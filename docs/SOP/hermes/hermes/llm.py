"""Ollama（Llama 3 8B）：自然語言 → JSON Plan。注入精簡工具 schema 與 ~600 tokens 的上下文。"""
from __future__ import annotations
import json, logging, os, re
from datetime import datetime
import httpx
from .config import CFG, compact_tool_schema
from .ha import ha
from .memory import mem

log = logging.getLogger("hermes.llm")

SYSTEM = """你是 Hermes，Allen 與 Ann 家中的智慧家庭管家。你只能呼叫下面列出的工具；不在清單內的工具一律不要用，改回覆「這個我還不會」。
輸出必須是單一 JSON 物件，不要有其他文字：
{"intent": "<短英文代號>", "reply": "<給使用者的一句繁體中文回覆>", "steps": [{"tool": "<工具名>", "args": {...}}]}
規則：
- 使用者只是在聊天或提問且不需要設備動作時，steps 給空陣列。
- 「再暗一點」「那間房」這類指代，依 recent 與 last_plan 推斷。
- 溫度 18–30，亮度 1–100。地點用 living/master/second/entry/bath。
- 不要自己編造場景名稱或實體 ID。
- 節能是最高目標：冷氣預設 27 度、優先除濕與風扇、白天少開燈、離家或睡前用 energy.idle_sweep；使用者說「這次不要省」「宴客」才用 energy.pause_guard 或 energy.set_mode comfort。
- 問用電、電費、碳排、「今天省了多少」→ energy.report。
可用工具：
""" + compact_tool_schema()


async def build_context() -> str:
    p = CFG["presence"]
    allen = await ha.get_state(p["allen"]); ann = await ha.get_state(p["ann"])
    shift = await ha.get_state(p["ann_shift"]); sleep = await ha.get_state(p["sleep_mode"])
    lt = await ha.get_state("sensor.living_temperature"); mt = await ha.get_state("sensor.master_temperature")
    offline = [e for e in ("light.living_all", "climate.living", "climate.master", "cover.living_curtain", "cover.bedroom_curtain", "vacuum.qrevo") if not await ha.is_online(e)]
    ctx = {
        "now": datetime.now().strftime("%Y-%m-%d %H:%M (%a)"),
        "presence": {"allen": allen and allen["state"], "ann": ann and ann["state"]},
        "ann_shift": shift and shift["state"], "sleep_mode": sleep and sleep["state"] == "on",
        "env": {"living": lt and lt["state"], "master": mt and mt["state"]},
        "devices_offline": offline,
        "recent": mem.session["turns"][-4:],
        "last_plan": mem.session.get("last_plan"),
        "prefs": [f"{k}: {v} (n={n}, conf {c:.2f})" for k, v, n, c in mem.prefs()],
    }
    return "# context\n" + json.dumps(ctx, ensure_ascii=False)


def _strip_think(t: str) -> str:
    """舊版 Ollama 不吃 think 參數時，把 <think>…</think> 砍掉再解析 JSON"""
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


async def _ollama(messages: list[dict]) -> str:
    o = CFG["ollama"]
    body = {"model": o["model"], "messages": messages, "stream": False, "format": "json",
            "options": {"temperature": o.get("temperature", 0.1), "num_ctx": o.get("num_ctx", 4096)}, "keep_alive": -1}
    if o.get("think") is not None:        # Qwen3 等推理模型：關閉 thinking，回覆才不會夾 <think>
        body["think"] = bool(o["think"])
    async with httpx.AsyncClient(timeout=o.get("timeout_s", 8)) as cl:
        r = await cl.post(o["url"].rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        return _strip_think(r.json()["message"]["content"])


async def _grok(messages: list[dict]) -> str:
    """xAI Grok（OpenAI 相容 chat/completions）。只送文字上下文，不送語音；金鑰由環境變數提供。"""
    g = CFG.get("grok") or {}
    key = os.environ.get(g.get("api_key_env", "HERMES_GROK_API_KEY"), "")
    if not key:
        raise RuntimeError("HERMES_GROK_API_KEY 未設定")
    body = {"model": g.get("model", "grok-4-fast"), "messages": messages, "temperature": g.get("temperature", 0.1),
            "response_format": {"type": "json_object"}, "max_tokens": g.get("max_tokens", 600)}
    async with httpx.AsyncClient(timeout=g.get("timeout_s", 15), headers={"Authorization": f"Bearer {key}"}) as cl:
        r = await cl.post(g.get("base_url", "https://api.x.ai/v1").rstrip("/") + "/chat/completions", json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


PROVIDERS = {"ollama": _ollama, "grok": _grok}


async def plan(user_text: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM + "\n" + await build_context()}, {"role": "user", "content": user_text}]
    llm = CFG.get("llm") or {}
    primary = llm.get("provider", "ollama"); fallback = llm.get("fallback", "ollama" if primary != "ollama" else None)
    try:
        content = await PROVIDERS[primary](messages)
    except Exception as e:
        log.warning("LLM provider %s failed: %s", primary, e)
        if fallback and fallback != primary:
            log.warning("fallback → %s", fallback)
            content = await PROVIDERS[fallback](messages)
        else:
            raise
    try:
        j = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        j = json.loads(m.group(0)) if m else {"intent": "chat", "reply": content.strip(), "steps": []}
    j.setdefault("steps", []); j.setdefault("reply", ""); j.setdefault("intent", "unknown")
    return j
