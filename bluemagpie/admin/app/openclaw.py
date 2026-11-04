"""OpenClaw 本地語音管線：狀態檢查、拉模型、把 Whisper/Piper/Hermes 一鍵串進 Home Assistant（Wyoming、Ollama 整合、Assist 管線）"""
from __future__ import annotations
import asyncio, json, logging, socket
import httpx
from . import settings as S

log = logging.getLogger("magpie.openclaw")


def _hosts(d: dict) -> dict:
    """從 HA 容器看出去的位址（host 模式 HA 在主機網路，其他容器經 host.docker.internal 對映埠）"""
    hostnet = d["site"]["network_mode"] == "host"
    h = "host.docker.internal" if hostnet else None
    env = {}
    envp = S.PROJECT / ".env"
    if envp.exists():
        for line in envp.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("="); env[k.strip()] = v.split("#")[0].strip()
    vip = d["cluster"].get("lb_vip")
    return {
        "whisper": (vip, 10300) if vip else (h or "whisper", int(env.get("WHISPER_PORT", 10300)) if h else 10300),
        "piper": (vip, 10200) if vip else (h or "piper", int(env.get("PIPER_PORT", 10200)) if h else 10200),
        "hermes_url": f"http://{h or 'hermes'}:{env.get('HERMES_PORT', 8800) if h else 8800}",
        "ollama_url": d["voice"]["ollama_url"] if d["voice"]["ollama_source"] == "host" else "http://ollama:11434",
        "ha_url": f"http://{'host.docker.internal' if hostnet else 'homeassistant'}:8123",
    }


def _tcp(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


async def status() -> dict:
    d = S.load(); H = _hosts(d)
    out = {"whisper": _tcp("whisper", 10300), "piper": _tcp("piper", 10200)}
    try:
        async with httpx.AsyncClient(timeout=4) as cl:
            r = await cl.get(H["ollama_url"] + "/api/tags"); models = [m["name"] for m in r.json().get("models", [])]
            out["ollama"] = {"ok": True, "models": models, "has_model": any(m.startswith(d["voice"]["ollama_model"].split(":")[0]) for m in models)}
    except Exception as e:
        out["ollama"] = {"ok": False, "error": type(e).__name__, "models": [], "has_model": False}
    try:
        async with httpx.AsyncClient(timeout=4) as cl:
            r = await cl.get("http://hermes:8800/v1/health"); out["hermes"] = r.json()
    except Exception as e:
        out["hermes"] = {"ok": False, "error": type(e).__name__}
    out["llm_provider"] = d["voice"].get("llm_provider", "ollama")
    if d["voice"].get("grok_api_key"):
        try:
            async with httpx.AsyncClient(timeout=8, headers={"Authorization": f"Bearer {d['voice']['grok_api_key']}"}) as cl:
                r = await cl.get("https://api.x.ai/v1/models"); out["grok"] = {"ok": r.status_code == 200, "code": r.status_code}
        except Exception as e:
            out["grok"] = {"ok": False, "error": type(e).__name__}
    else:
        out["grok"] = {"ok": False, "error": "未設定 API key"}
    out["ha"] = await _ha_entities(d, H)
    return out


async def _ha_entities(d: dict, H: dict) -> dict:
    tok = d["ha"]["token"]
    if not tok:
        return {"ok": False, "error": "尚未填 HA 權杖"}
    try:
        async with httpx.AsyncClient(timeout=6, headers={"Authorization": f"Bearer {tok}"}) as cl:
            r = await cl.get(H["ha_url"] + "/api/states"); r.raise_for_status()
            ids = [s["entity_id"] for s in r.json()]
            return {"ok": True,
                    "stt": [e for e in ids if e.startswith("stt.")], "tts": [e for e in ids if e.startswith("tts.")],
                    "conversation": [e for e in ids if e.startswith("conversation.")]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def pull_model() -> dict:
    d = S.load(); H = _hosts(d); model = d["voice"]["ollama_model"]
    try:
        async with httpx.AsyncClient(timeout=1800) as cl:
            async with cl.stream("POST", H["ollama_url"] + "/api/pull", json={"name": model, "stream": True}) as r:
                last = ""
                async for line in r.aiter_lines():
                    if line:
                        try: last = json.loads(line).get("status", last)
                        except json.JSONDecodeError: pass
        return {"ok": True, "model": model, "status": last}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------- HA 設定流程（config flow）----------
async def _flow(cl: httpx.AsyncClient, base: str, handler: str, steps: list[dict]) -> dict:
    try:
        return await _flow_inner(cl, base, handler, steps)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def _flow_inner(cl: httpx.AsyncClient, base: str, handler: str, steps: list[dict]) -> dict:
    r = await cl.post(base + "/api/config/config_entries/flow", json={"handler": handler, "show_advanced_options": True}); r.raise_for_status()
    res = r.json(); fid = res["flow_id"]
    for data in steps:
        if res.get("type") != "form":
            break
        r = await cl.post(f"{base}/api/config/config_entries/flow/{fid}", json=data); r.raise_for_status(); res = r.json()
    if res.get("type") == "form":  # 還有表單沒填完：回報欄位讓使用者在 HA 完成
        return {"ok": False, "step": res.get("step_id"), "fields": [f.get("name") for f in res.get("data_schema", [])], "errors": res.get("errors")}
    if res.get("type") == "abort":
        return {"ok": res.get("reason") in ("already_configured", "single_instance_allowed"), "abort": res.get("reason")}
    return {"ok": res.get("type") == "create_entry", "title": res.get("title"), "entry_id": (res.get("result") or {}).get("entry_id")}


async def setup_ha() -> dict:
    """一鍵：Wyoming(whisper) + Wyoming(piper) + Ollama 整合（指向 Hermes）+ Assist 管線「OpenClaw」設為預設"""
    d = S.load(); H = _hosts(d); tok = d["ha"]["token"]
    if not tok:
        return {"ok": False, "error": "請先在「Home Assistant」頁填入長效權杖並套用"}
    base = H["ha_url"]; report = {}
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {tok}"}) as cl:
        report["whisper"] = await _flow(cl, base, "wyoming", [{"host": H["whisper"][0], "port": H["whisper"][1]}])
        report["piper"] = await _flow(cl, base, "wyoming", [{"host": H["piper"][0], "port": H["piper"][1]}])
        # Ollama 整合指向 Hermes（Hermes 提供 /api/tags、/api/chat）；不同 HA 版本的流程步驟略有差異，逐步餵
        report["hermes"] = await _flow(cl, base, "ollama", [{"url": H["hermes_url"], "model": "hermes:latest"}, {"model": "hermes:latest"}, {"download": False}])
    await asyncio.sleep(3)
    ents = await _ha_entities(d, H)
    report["entities"] = ents
    if ents.get("ok"):
        report["pipeline"] = await _create_pipeline(d, H, ents)
    report["ok"] = all(report[k].get("ok") for k in ("whisper", "piper", "hermes")) and report.get("pipeline", {}).get("ok", False)
    if not ents.get("ok"):
        report["error"] = "連不到 Home Assistant：" + str(ents.get("error"))
    report["next"] = ("完成。到 HA → 設定 → 語音助理 確認「OpenClaw」為預設；Ollama 整合的對話代理請改名 Hermes 並把「控制 Home Assistant」設為不控制。"
                      if report["ok"] else "部分步驟需到 HA → 設定 → 整合 手動完成（見各項回報）。")
    return report


async def _create_pipeline(d: dict, H: dict, ents: dict) -> dict:
    """用 WebSocket 建立/更新 Assist 管線並設為預設"""
    try:
        import websockets
    except ImportError:
        return {"ok": False, "error": "websockets 未安裝"}
    stt = next((e for e in ents["stt"] if "whisper" in e), ents["stt"][0] if ents["stt"] else None)
    tts = next((e for e in ents["tts"] if "piper" in e), ents["tts"][0] if ents["tts"] else None)
    conv = next((e for e in ents["conversation"] if "hermes" in e or "ollama" in e), None)
    if not (stt and tts and conv):
        return {"ok": False, "error": f"實體不足 stt={stt} tts={tts} conversation={conv}"}
    url = H["ha_url"].replace("http", "ws", 1) + "/api/websocket"
    try:
        async with websockets.connect(url) as ws:
            await ws.recv(); await ws.send(json.dumps({"type": "auth", "access_token": d["ha"]["token"]})); await ws.recv()
            await ws.send(json.dumps({"id": 1, "type": "assist_pipeline/pipeline/list"})); lst = json.loads(await ws.recv())
            existing = next((p for p in lst.get("result", {}).get("pipelines", []) if p["name"] == "OpenClaw"), None)
            body = {"name": "OpenClaw", "language": "zh-TW", "conversation_engine": conv, "conversation_language": "zh-TW",
                    "stt_engine": stt, "stt_language": "zh", "tts_engine": tts, "tts_language": "zh_CN", "tts_voice": d["voice"]["piper_voice"],
                    "wake_word_entity": None, "wake_word_id": None}
            if existing:
                await ws.send(json.dumps({"id": 2, "type": "assist_pipeline/pipeline/update", "pipeline_id": existing["id"], **body})); res = json.loads(await ws.recv()); pid = existing["id"]
            else:
                await ws.send(json.dumps({"id": 2, "type": "assist_pipeline/pipeline/create", **body})); res = json.loads(await ws.recv()); pid = (res.get("result") or {}).get("id")
            if not res.get("success"):
                return {"ok": False, "error": res.get("error")}
            await ws.send(json.dumps({"id": 3, "type": "assist_pipeline/pipeline/set_preferred", "pipeline_id": pid})); pref = json.loads(await ws.recv())
            return {"ok": bool(pref.get("success")), "pipeline_id": pid, "stt": stt, "tts": tts, "conversation": conv}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
