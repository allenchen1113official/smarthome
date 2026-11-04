"""青鳥 Magpie Bot — LINE Messaging API + Telegram Bot 共用的遠端控制介面
- 成員白名單（config/bot/bot.yaml 由後台產生）
- 結構化指令（/燈 /冷氣 /窗簾 /情境 /狀態）直接呼叫 HA；自然語言交給 Hermes（政策、覆誦確認、回滾一致）
- 確認：LINE Quick Reply / Telegram Inline Keyboard 的「好 / 取消」→ 回 Hermes
- 推播：POST /v1/notify {to, message} 供 HA rest_command / Hermes 使用
"""
from __future__ import annotations
import asyncio, base64, hashlib, hmac, json, logging, os, re, time
from pathlib import Path
import httpx, yaml
from fastapi import FastAPI, Header, HTTPException, Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("magpie.bot")
app = FastAPI(title="青鳥 Magpie Bot", version="0.1")
CFG_PATH = Path(os.environ.get("MAGPIE_BOT_CONFIG", "/config/bot.yaml"))
AUDIT = Path(os.environ.get("MAGPIE_BOT_AUDIT", "/data/audit.log"))
CFG: dict = {}
PENDING: dict[str, dict] = {}        # member_key -> {"ts":..}
RATE: dict[str, list[float]] = {}


def load_cfg():
    global CFG
    CFG = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) if CFG_PATH.exists() else {}
    CFG.setdefault("members", []); CFG.setdefault("scenes", {}); CFG.setdefault("areas", {})
    return CFG


def audit(member: str, platform: str, text: str, result: str):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{platform}\t{member}\t{text!r}\t{result[:120]!r}\n")


def member_of(platform: str, uid: str) -> dict | None:
    for m in CFG["members"]:
        if m.get("platform") == platform and str(m.get("id")) == str(uid):
            return m
    return None


def rate_ok(key: str, limit: int = 20) -> bool:
    now = time.time(); RATE[key] = [t for t in RATE.get(key, []) if now - t < 60] + [now]
    return len(RATE[key]) <= limit


# ---------- Home Assistant / Hermes ----------
async def ha(domain: str, service: str, data: dict):
    async with httpx.AsyncClient(timeout=8, headers={"Authorization": f"Bearer {CFG['ha_token']}"}) as cl:
        r = await cl.post(f"{CFG['ha_url']}/api/services/{domain}/{service}", json=data); r.raise_for_status()


async def ha_state(entity: str) -> dict | None:
    async with httpx.AsyncClient(timeout=8, headers={"Authorization": f"Bearer {CFG['ha_token']}"}) as cl:
        r = await cl.get(f"{CFG['ha_url']}/api/states/{entity}")
        return r.json() if r.status_code == 200 else None


async def hermes(text: str, speaker: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=25) as cl:
            r = await cl.post(f"{CFG['hermes_url']}/v1/command", json={"text": text, "speaker": speaker, "source": "chat", "say": False})
            r.raise_for_status(); return r.json()["reply"]
    except Exception as e:
        log.warning("hermes: %s", e)
        return "管家暫時離線，請用指令格式（例：/燈 客廳 開）或稍後再試。"


# ---------- 指令文法 ----------
HELP = ("可用指令：\n"
        "/狀態 — 家裡現況\n"
        "/情境 睡眠|影音|訪客|離家 開|關\n"
        "/燈 客廳|主臥|次臥|玄關 開|關|亮度%\n"
        "/冷氣 客廳|主臥|次臥 開|關|溫度\n"
        "/窗簾 客廳|主臥 開|關|位置%\n"
        "/掃地 開始|回充\n"
        "或直接用自然語言，例如「客廳燈調到百分之五十」（管家會先覆誦確認）")
AREA = {"客廳": "living", "客餐廳": "living", "主臥": "master", "房間": "master", "次臥": "second", "玄關": "entry", "浴室": "bath"}
SCENE = {"睡眠": "input_boolean.sleep_mode", "影音": "input_boolean.movie_mode", "訪客": "input_boolean.guest_mode"}


async def structured(text: str, m: dict) -> str | None:
    t = text.strip().replace("／", "/")
    if t in ("/help", "/幫助", "幫助", "?"): return HELP
    if t.startswith("/狀態") or t == "狀態":
        return await status_text()
    mm = re.match(r"^/?情境\s+(\S+)\s*(開|關)?$", t)
    if mm:
        name, onoff = mm.group(1), mm.group(2) or "開"
        if name == "離家":
            await ha("light", "turn_off", {"entity_id": "light.all_lights"})
            for room in ("living", "master", "second"):
                await ha("script", "ac_set", {"room": room, "hvac_mode": "off"})
            return "🏠 已執行離家：全屋關燈、冷氣關。"
        ent = SCENE.get(name)
        if not ent: return f"沒有「{name}」這個情境。{HELP}"
        await ha("input_boolean", "turn_on" if onoff == "開" else "turn_off", {"entity_id": ent})
        return f"{'✅' if onoff == '開' else '⏹'} {name}模式已{onoff}。"
    mm = re.match(r"^/?燈\s+(\S+)\s+(開|關|(\d{1,3})%?)$", t)
    if mm:
        area = AREA.get(mm.group(1)); ent = CFG["areas"].get(area, {}).get("light") if area else None
        if not ent: return f"不認得區域「{mm.group(1)}」。"
        if mm.group(3): await ha("light", "turn_on", {"entity_id": ent, "brightness_pct": int(mm.group(3))}); return f"💡 {mm.group(1)}燈 {mm.group(3)}%。"
        await ha("light", "turn_on" if mm.group(2) == "開" else "turn_off", {"entity_id": ent}); return f"💡 {mm.group(1)}燈已{mm.group(2)}。"
    mm = re.match(r"^/?冷氣\s+(\S+)\s+(開|關|(\d{2}))$", t)
    if mm:
        area = AREA.get(mm.group(1))
        if area not in ("living", "master", "second"): return f"不認得「{mm.group(1)}」的冷氣。"
        if mm.group(3):
            temp = int(mm.group(3))
            if not 18 <= temp <= 30: return "溫度要在 18–30 之間。"
            await ha("script", "ac_set", {"room": area, "hvac_mode": "cool", "temperature": temp}); return f"❄️ {mm.group(1)}冷氣 {temp}°C。"
        await ha("script", "ac_set", {"room": area, "hvac_mode": "cool" if mm.group(2) == "開" else "off"}); return f"❄️ {mm.group(1)}冷氣已{mm.group(2)}。"
    mm = re.match(r"^/?窗簾\s+(\S+)\s+(開|關|(\d{1,3})%?)$", t)
    if mm:
        area = AREA.get(mm.group(1)); ent = CFG["areas"].get(area, {}).get("cover") if area else None
        if not ent: return f"「{mm.group(1)}」沒有窗簾。"
        if mm.group(3): await ha("cover", "set_cover_position", {"entity_id": ent, "position": int(mm.group(3))}); return f"🪟 {mm.group(1)}窗簾 {mm.group(3)}%。"
        await ha("cover", "open_cover" if mm.group(2) == "開" else "close_cover", {"entity_id": ent}); return f"🪟 {mm.group(1)}窗簾已{mm.group(2)}。"
    mm = re.match(r"^/?掃地\s*(開始|回充|暫停)?$", t)
    if mm:
        act = {"開始": "start", "回充": "return_to_base", "暫停": "pause", None: "start"}[mm.group(1)]
        await ha("vacuum", act, {"entity_id": "vacuum.qrevo"}); return f"🤖 掃地機：{mm.group(1) or '開始'}。"
    return None


async def status_text() -> str:
    parts = []
    for label, ent, fmt in [("Allen", "person.allen", lambda s: "在家" if s["state"] == "home" else "外出"),
                            ("Ann", "person.ann", lambda s: "在家" if s["state"] == "home" else "外出"),
                            ("客廳", "sensor.living_temperature", lambda s: f"{s['state']}°C"),
                            ("主臥", "sensor.master_temperature", lambda s: f"{s['state']}°C"),
                            ("客廳冷氣", "climate.living", lambda s: s["state"] if s["state"] == "off" else f"{s['state']} {s['attributes'].get('temperature')}°"),
                            ("主臥冷氣", "climate.master", lambda s: s["state"] if s["state"] == "off" else f"{s['state']} {s['attributes'].get('temperature')}°"),
                            ("睡眠模式", "input_boolean.sleep_mode", lambda s: s["state"]),
                            ("大門", "binary_sensor.front_door", lambda s: "開著" if s["state"] == "on" else "已關"),
                            ("掃地機", "vacuum.qrevo", lambda s: s["state"])]:
        try:
            s = await ha_state(ent); parts.append(f"{label}：{fmt(s) if s else '—'}")
        except Exception:
            parts.append(f"{label}：—")
    return "🏠 家裡現況\n" + "\n".join(parts)


async def handle(platform: str, uid: str, text: str) -> tuple[str, bool]:
    """回 (訊息, 是否需要確認按鈕)"""
    m = member_of(platform, uid)
    if not m:
        return f"你還不是家庭成員。請把這組 ID 交給管理員加入白名單：\n{platform}:{uid}", False
    key = f"{platform}:{uid}"
    if not rate_ok(key):
        return "指令太頻繁，請稍候一分鐘。", False
    if text.strip() in ("好", "取消", "yes", "no", "ok"):
        reply = await hermes(text, m["name"]); audit(m["name"], platform, text, reply); PENDING.pop(key, None); return reply, False
    try:
        r = await structured(text, m)
    except httpx.HTTPError as e:
        r = f"Home Assistant 回應錯誤：{e}"
    if r is not None:
        audit(m["name"], platform, text, r); return r, False
    if m.get("role") == "viewer":
        return "你的權限只能查詢（/狀態）。", False
    reply = await hermes(text, m["name"]); audit(m["name"], platform, text, reply)
    need = reply.startswith("要我") and reply.endswith("嗎？")
    if need: PENDING[key] = {"ts": time.time()}
    return reply, need


# ---------- LINE ----------
@app.post("/line/webhook")
async def line_webhook(req: Request, x_line_signature: str = Header(default="")):
    body = await req.body()
    mac = hmac.new(CFG["line"]["channel_secret"].encode(), body, hashlib.sha256).digest()
    if not hmac.compare_digest(base64.b64encode(mac).decode(), x_line_signature):
        raise HTTPException(403, "bad signature")
    for ev in json.loads(body).get("events", []):
        if ev.get("type") == "message" and ev["message"].get("type") == "text":
            uid = ev["source"].get("userId", ""); text = ev["message"]["text"]
            if text.startswith("CONFIRM:"): text = text.split(":", 1)[1]
            reply, need = await handle("line", uid, text)
            await line_reply(ev["replyToken"], reply, need)
        elif ev.get("type") == "follow":
            await line_reply(ev["replyToken"], f"歡迎使用青鳥智慧家庭。你的 LINE ID：\n{ev['source'].get('userId')}\n請交給管理員加入成員後即可使用。\n\n{HELP}", False)
    return {"ok": True}


async def line_reply(token: str, text: str, need_confirm: bool):
    msg: dict = {"type": "text", "text": text[:4900]}
    items = [{"type": "action", "action": {"type": "message", "label": "好", "text": "好"}}, {"type": "action", "action": {"type": "message", "label": "取消", "text": "取消"}}] if need_confirm else \
            [{"type": "action", "action": {"type": "message", "label": l, "text": t}} for l, t in CFG.get("quick", [])][:13]
    if items: msg["quickReply"] = {"items": items}
    async with httpx.AsyncClient(timeout=10, headers={"Authorization": f"Bearer {CFG['line']['access_token']}"}) as cl:
        r = await cl.post("https://api.line.me/v2/bot/message/reply", json={"replyToken": token, "messages": [msg]})
        if r.status_code >= 300: log.warning("line reply %s %s", r.status_code, r.text[:200])


async def line_push(uid: str, text: str):
    async with httpx.AsyncClient(timeout=10, headers={"Authorization": f"Bearer {CFG['line']['access_token']}"}) as cl:
        await cl.post("https://api.line.me/v2/bot/message/push", json={"to": uid, "messages": [{"type": "text", "text": text[:4900]}]})


# ---------- Telegram（long polling，不需要對外開埠）----------
TG = "https://api.telegram.org/bot{token}/{method}"


async def tg(method: str, **data):
    async with httpx.AsyncClient(timeout=35) as cl:
        r = await cl.post(TG.format(token=CFG["telegram"]["bot_token"], method=method), json=data)
        return r.json()


def tg_keyboard(need_confirm: bool) -> dict:
    if need_confirm:
        return {"inline_keyboard": [[{"text": "好 ✅", "callback_data": "好"}, {"text": "取消 ✖", "callback_data": "取消"}]]}
    rows, row = [], []
    for l, t in CFG.get("quick", []):
        row.append({"text": l, "callback_data": t})
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    return {"inline_keyboard": rows} if rows else {}


async def tg_loop():
    if not CFG.get("telegram", {}).get("bot_token"):
        log.info("Telegram 未設定 token，略過"); return
    offset = 0; announced = False
    while True:
        try:
            if not announced:
                await tg("setMyCommands", commands=[{"command": "status", "description": "家裡現況"}, {"command": "help", "description": "指令說明"}]); announced = True
            res = await tg("getUpdates", offset=offset, timeout=30, allowed_updates=["message", "callback_query"])
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                if "message" in u and "text" in u["message"]:
                    chat = u["message"]["chat"]["id"]; text = u["message"]["text"]
                    if text in ("/start", "/help"): text = "/help"
                    if text == "/status": text = "/狀態"
                    reply, need = await handle("telegram", str(chat), text)
                    await tg("sendMessage", chat_id=chat, text=reply, reply_markup=tg_keyboard(need))
                elif "callback_query" in u:
                    cq = u["callback_query"]; chat = cq["message"]["chat"]["id"]
                    await tg("answerCallbackQuery", callback_query_id=cq["id"])
                    reply, need = await handle("telegram", str(chat), cq["data"])
                    await tg("sendMessage", chat_id=chat, text=reply, reply_markup=tg_keyboard(need))
        except Exception as e:
            log.warning("tg loop: %s", e); await asyncio.sleep(5)


# ---------- 推播（給 HA / Hermes）----------
@app.post("/v1/notify")
async def notify(body: dict, req: Request):
    if not hmac.compare_digest(req.headers.get("X-Magpie-Secret", ""), CFG.get("shared_secret", "") or "__unset__"):
        raise HTTPException(403)
    to = body.get("to", "all"); text = body.get("message", "")
    sent = []
    for m in CFG["members"]:
        if to in ("all", m["name"], m.get("role")) or m["name"] in (to if isinstance(to, list) else [to]):
            try:
                if m["platform"] == "telegram": await tg("sendMessage", chat_id=m["id"], text=text)
                elif m["platform"] == "line": await line_push(m["id"], text)
                sent.append(f"{m['platform']}:{m['name']}")
            except Exception as e:
                log.warning("notify %s: %s", m["name"], e)
    return {"sent": sent}


@app.get("/v1/health")
async def health():
    return {"ok": True, "members": len(CFG["members"]), "line": bool(CFG.get("line", {}).get("access_token")), "telegram": bool(CFG.get("telegram", {}).get("bot_token")), "pending": len(PENDING)}


@app.post("/v1/reload")
async def reload(req: Request):
    if not hmac.compare_digest(req.headers.get("X-Magpie-Secret", ""), CFG.get("shared_secret", "") or "__unset__"):
        raise HTTPException(403)
    load_cfg(); return {"ok": True, "members": len(CFG["members"])}


@app.on_event("startup")
async def _startup():
    load_cfg()
    asyncio.create_task(tg_loop())
    log.info("Magpie Bot 就緒：成員 %d，LINE %s，Telegram %s", len(CFG["members"]), bool(CFG.get("line", {}).get("access_token")), bool(CFG.get("telegram", {}).get("bot_token")))
