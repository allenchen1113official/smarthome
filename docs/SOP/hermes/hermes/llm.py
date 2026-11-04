"""Ollama（Llama 3 8B）：自然語言 → JSON Plan。注入精簡工具 schema 與 ~600 tokens 的上下文。"""
from __future__ import annotations
import json, logging, re
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


async def plan(user_text: str) -> dict:
    o = CFG["ollama"]
    messages = [{"role": "system", "content": SYSTEM + "\n" + await build_context()}, {"role": "user", "content": user_text}]
    body = {"model": o["model"], "messages": messages, "stream": False, "format": "json",
            "options": {"temperature": o.get("temperature", 0.1), "num_ctx": o.get("num_ctx", 4096)}, "keep_alive": -1}
    async with httpx.AsyncClient(timeout=o.get("timeout_s", 8)) as cl:
        r = await cl.post(o["url"].rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        content = r.json()["message"]["content"]
    try:
        j = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        j = json.loads(m.group(0)) if m else {"intent": "chat", "reply": content.strip(), "steps": []}
    j.setdefault("steps", []); j.setdefault("reply", ""); j.setdefault("intent", "unknown")
    return j
