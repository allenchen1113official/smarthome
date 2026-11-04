"""Hermes HTTP 介面
- /api/tags, /api/show, /api/chat   Ollama 相容 → HA 的「Ollama」整合可直接把 Hermes 當對話代理
- /v1/command                       Siri 捷徑 / HA webhook 自動化 直接丟文字
- /v1/jobs/screen                   13:30 盤後掃描（情境 32）
- /v1/alerts/check                  盤中告警輪詢（情境 33）
- /v1/health
"""
from __future__ import annotations
import asyncio, json, logging, time
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from .config import CFG
from .ha import ha
from . import orchestrator, market, tools
from .textnorm import for_tts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hermes.app")
app = FastAPI(title="Hermes Agent", version="0.1")
MODEL = CFG["server"]["model_name"]
_llm_sem = asyncio.Semaphore(CFG["lanes"]["llm_workers"])
_queue_len = 0


@app.on_event("startup")
async def _startup():
    ha.start_ws()
    log.info("Hermes v0.1 ready on %s:%s", CFG["server"]["host"], CFG["server"]["port"])


# ---------- Ollama 相容 ----------
@app.get("/api/tags")
async def tags():
    return {"models": [{"name": MODEL, "model": MODEL, "modified_at": datetime.now(timezone.utc).isoformat(), "size": 0,
                        "details": {"family": "hermes", "parameter_size": "8B", "quantization_level": "Q4_0"}}]}


@app.post("/api/show")
async def show():
    return {"modelfile": "", "parameters": "", "template": "", "details": {"family": "hermes"}, "capabilities": ["completion"]}


@app.get("/api/version")
async def version():
    return {"version": "0.1.0-hermes"}


@app.post("/api/chat")
async def chat(req: Request):
    global _queue_len
    body = await req.json()
    msgs = body.get("messages", [])
    user = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
    if _queue_len >= CFG["lanes"]["llm_queue_max"]:
        reply = "等我一下，前面還有指令在處理。"
    else:
        _queue_len += 1
        try:
            async with _llm_sem:
                reply = await orchestrator.handle(user, speaker=None, source="assist")
        finally:
            _queue_len -= 1
    reply = for_tts(reply) if body.get("options", {}).get("hermes_tts", True) else reply
    now = datetime.now(timezone.utc).isoformat()
    if body.get("stream", True):
        async def gen():
            yield json.dumps({"model": MODEL, "created_at": now, "message": {"role": "assistant", "content": reply}, "done": False}, ensure_ascii=False) + "\n"
            yield json.dumps({"model": MODEL, "created_at": now, "message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop",
                              "total_duration": 0, "eval_count": 0, "prompt_eval_count": 0}, ensure_ascii=False) + "\n"
        return StreamingResponse(gen(), media_type="application/x-ndjson")
    return {"model": MODEL, "created_at": now, "message": {"role": "assistant", "content": reply}, "done": True, "done_reason": "stop"}


# ---------- 直接指令（Siri 捷徑 / HA 自動化）----------
@app.post("/v1/command")
async def command(req: Request):
    b = await req.json()
    text = b.get("text", ""); speaker = b.get("speaker"); source = b.get("source", "voice")
    reply = await orchestrator.handle(text, speaker=speaker, source=source)
    if b.get("say", True):
        try:
            await tools.execute("media.say", {"text": reply, "target": b.get("output", "living_homepod")})
        except Exception as e:
            log.warning("say failed: %s", e)
    return {"reply": reply, "reply_tts": for_tts(reply)}


# ---------- 批次與告警 ----------
@app.post("/v1/jobs/screen")
async def job_screen(req: Request):
    b = await req.json() if await req.body() else {}
    res = await market.screen(b.get("top_n"), b.get("min_score"))
    if res["results"]:
        text = "今天盤後掃描前幾名：" + "；".join(f"{r['symbol']} {r['name']} {r['score']} 分，{r['why']}" for r in res["results"]) + "。" + market.MARKET["disclaimer"]
    else:
        text = "今天沒有符合條件的。"
    res["speech"] = for_tts(text)
    try:
        await tools.execute("notify.push", {"to": "allen", "message": text, "image": res.get("card_path")})
    except Exception as e:
        log.warning("push failed: %s", e)
    return res


@app.post("/v1/alerts/check")
async def alerts_check():
    fired = await market.check_alerts()
    for a in fired:
        try:
            await ha.call_service("script", "hermes_alert", {"message": a["message"], "light": a.get("light") or "none", "tts": a.get("tts", False), "priority": a.get("priority", "normal")})
        except Exception as e:
            log.warning("hermes_alert failed: %s", e)
    return {"fired": fired, "checked_at": datetime.now().isoformat(timespec="seconds")}


@app.get("/v1/health")
async def health():
    return {"ok": True, "world_entities": len(ha.world), "pending": bool(orchestrator.mem.session.get("pending")), "ts": time.time()}


@app.get("/v1/holdings")
async def holdings():
    return orchestrator.mem.holdings()
