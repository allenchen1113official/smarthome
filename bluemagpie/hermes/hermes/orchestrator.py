"""編排：PARSE → GUARD → CONFIRM → DISPATCH → RETRY → SETTLE（含反向補償回滾）與 fast lane"""
from __future__ import annotations
import asyncio, logging, os, re, time, uuid
from datetime import datetime
from .config import CFG, POLICY, TOOLS
from .ha import ha
from .memory import mem
from . import tools, market, policy, llm, energy
from .textnorm import to_traditional

log = logging.getLogger("hermes.orch")
_tx = None


def tx(line: str):
    global _tx
    if _tx is None:
        p = CFG["paths"]["tx_log"]; os.makedirs(os.path.dirname(p), exist_ok=True); _tx = open(p, "a", encoding="utf-8")
    _tx.write(f"{datetime.now():%H:%M:%S.%f}"[:-3] + " " + line + "\n"); _tx.flush()


# ---------------- 驗證 ----------------
def validate_steps(steps: list[dict]) -> tuple[list[dict], str | None]:
    ok = []
    for s in steps:
        name, args = s.get("tool"), s.get("args") or {}
        if policy.is_never(name):
            return [], f"{name} 是永久封鎖的動作"
        t = TOOLS.get(name)
        if not t or t.get("internal"):
            return [], "這個我還不會"
        for req in t.get("required", []):
            if req not in args:
                return [], f"{name} 少了 {req}"
        for k, v in list(args.items()):
            spec = (t.get("params") or {}).get(k)
            if not spec:
                args.pop(k); continue
            if "enum" in spec and v not in spec["enum"]:
                return [], f"{k} 只能是 {'/'.join(map(str, spec['enum']))}"
            if isinstance(v, (int, float)) and (("min" in spec and v < spec["min"]) or ("max" in spec and v > spec["max"])):
                return [], f"{k} 要在 {spec.get('min')}–{spec.get('max')} 之間"
        ok.append({"id": f"s{len(ok)+1}", "tool": name, "args": policy.clamp_night(name, args)})
    return ok, None


def summarize(steps: list[dict]) -> str:
    AREA = {"living": "客廳", "master": "主臥", "second": "次臥", "entry": "玄關", "bath": "浴室", "living_curtain": "客廳窗簾", "bedroom_curtain": "主臥窗簾"}
    out = []
    for s in steps:
        a = s["args"]; t = s["tool"]
        if t == "light.set":
            out.append(f"把{AREA.get(a.get('area'), a.get('entity',''))}燈調到" + (f"{a['brightness']}%" if "brightness" in a else "") + (f" {a['kelvin']}K" if "kelvin" in a else ""))
        elif t == "light.activate_scene": out.append(f"開{AREA.get(a.get('area'),'客廳')}的 {a['scene']} 場景")
        elif t == "climate.set": out.append(f"把{AREA[a['entity']]}冷氣設 " + (f"{a['temp']} 度" if "temp" in a else "") + (f" {a['mode']}" if "mode" in a else ""))
        elif t == "cover.set_position": out.append(f"把{AREA[a['entity']]}開到 {a['position']}%")
        elif t == "vacuum.control": out.append({"start": "啟動掃地機", "pause": "暫停掃地機", "dock": "掃地機回充", "spot": "清掃指定房間"}[a["action"]])
        elif t == "market.paper_order": out.append(f"模擬{'買進' if a['side']=='buy' else '賣出'} {a['symbol']} {a['shares']} 股" + (f"，以 {a['price']} 記錄" if a.get("price") else "，以現價記錄"))
        elif t == "emergency.sos": out.append("發送 SOS 簡訊並全屋紅光")
        else: out.append(t)
    return "並".join(out)


# ---------------- fast lane（免 LLM）----------------
async def fast_lane(text: str) -> str | None:
    t = text.replace("？", "?").strip()
    m = re.search(r"(\d{4})\s*(現在|怎樣|怎麼樣|多少|股價)", t)
    if m:
        try:
            q = await market.quote(m.group(1))
            try: ind = market.indicators(m.group(1), ["ma20", "vol_ratio", "rsi14"])
            except Exception: ind = None
            return market.speak_quote(q, ind)
        except Exception as e:
            log.info("quote fail: %s", e)
            return "現在拿不到報價，網路或交易所那邊有狀況，要我五分鐘後再試一次嗎？"
    if re.search(r"(還在睡|睡了嗎|在睡嗎)", t):
        st = await tools.read_state({"area": "master"})
        cur = st.get("cover", {}).get("current_position"); mo = st.get("motion", {}).get("state")
        if cur is not None and cur <= 5:
            return "主臥窗簾全閉" + ("、沒有動靜" if mo == "off" else "") + "，看起來還在補眠喔。"
        return "主臥窗簾是開的，應該起來了。"
    m = re.search(r"(客廳|主臥|房間|次臥|小房間)\s*(冷氣)?\s*(幾度|溫度)", t)
    if m:
        area = mem.resolve_alias(m.group(1)) or "living"
        st = await tools.read_state({"area": area})
        c = st.get("climate", {}); tp = st.get("temp", {}).get("state")
        if c:
            return f"{m.group(1)}冷氣{'關著' if c['state']=='off' else '設 '+str(c.get('temperature'))+' 度'}" + (f"，室溫 {tp} 度。" if tp else "。")
    return None


# ---------------- 主入口 ----------------
async def handle(text: str, speaker: str | None = None, source: str = "voice") -> str:
    text = to_traditional(text.strip())
    mem.touch(speaker); mem.add_turn("user", text)
    pend = mem.session.get("pending")

    # 1) 待確認的 plan
    if pend:
        if time.time() > pend["expires_at"]:
            mem.session["pending"] = None; tx(f"plan {pend['id']} CONFIRM_TIMEOUT")
        elif policy.is_accept(text):
            mem.session["pending"] = None; tx(f"confirm ← '{text}'")
            return await execute_plan(pend)
        elif policy.is_reject(text):
            mem.session["pending"] = None; tx(f"plan {pend['id']} REJECTED")
            return "好，取消了。"

    # 2) fast lane
    fast = await fast_lane(text)
    if fast:
        mem.add_turn("assistant", fast); return fast

    # 3) LLM
    try:
        p = await llm.plan(text)
    except Exception as e:
        log.warning("LLM fail: %s", e)
        return "等我一下，我現在有點忙，請再說一次。"
    steps, err = validate_steps(p.get("steps", []))
    if err:
        return err
    if not steps:
        reply = p.get("reply") or "我在。"
        mem.add_turn("assistant", reply); return reply

    plan = {"id": "pln_" + uuid.uuid4().hex[:4], "intent": p.get("intent"), "steps": steps, "reply": p.get("reply", ""), "speaker": speaker, "source": source, "created": time.time()}
    tx(f"plan {plan['id']} PARSED intent={plan['intent']} steps={[s['tool'] for s in steps]}")

    # 4) 確認
    if POLICY.get("autonomy") == "confirm_all" and any(policy.needs_confirm(s["tool"], source) for s in steps):
        summary = summarize(steps)
        plan["expires_at"] = time.time() + POLICY["confirm"]["timeout_s"]
        mem.session["pending"] = plan
        phrase = POLICY["confirm"]["phrase"].format(summary=summary)
        tx(f"confirm → '{phrase}'")
        if policy.is_quiet_hours():
            await tools.execute("notify.push", {"to": speaker or "both", "message": f"Hermes：{phrase}（回覆 App 或再說一次「好」）"})
            return "深夜時段，我把確認改用推播送到手機了。"
        mem.add_turn("assistant", phrase)
        return phrase
    return await execute_plan(plan)


async def execute_plan(plan: dict) -> str:
    """GUARD → snapshot → DISPATCH(+RETRY) → SETTLE / 反向補償"""
    t0 = time.time(); done: list[tuple[dict, dict]] = []; energy_notes: list[str] = []
    sleep = await ha.get_state(CFG["presence"]["sleep_mode"]); sleep_on = bool(sleep and sleep["state"] == "on")
    tx(f"plan {plan['id']} START intent={plan['intent']}")
    for s in plan["steps"]:
        tool, args = s["tool"], s["args"]
        # GUARD
        ents = tools.affected_entities(tool, args)
        for e in ents:
            if not await ha.is_online(e):
                tx(f"guard {s['id']} {e} OFFLINE → ABORT")
                await _rollback(done)
                return f"{e.split('.')[1].replace('_all','').replace('_',' ')} 現在沒回應，" + ("已把前面的動作還原。" if done else "先不動。")
        if TOOLS[tool].get("scope") == "write.appliance":
            why = policy.appliance_denied(sleep_on)
            if why:
                tx(f"guard {s['id']} DENY {why}"); await _rollback(done); return why + "。"
        if tool == "light.set" and sleep_on and args.get("area") == "master":
            tx(f"guard {s['id']} sleep_mode → skip"); continue
        if (time.time() - t0) * 1000 > POLICY["plan"]["max_total_ms"]:
            tx(f"plan {plan['id']} TIMEOUT"); await _rollback(done); return "動作太久了，已還原。"
        # ENERGY GUARD（憲章 VI）：只收緊不放寬；comfort 模式 / 暫停守門時原樣通過
        args, enotes = await energy.clamp(tool, args)
        if enotes:
            s["args"] = args; energy_notes.extend(enotes); tx(f"energy {s['id']} {' / '.join(enotes)}")
        # snapshot
        snap = await tools.snapshot(ents) if ents else {}
        if snap:
            sid = f"{plan['id']}:{s['id']}"; mem.save_snapshot(sid, snap); tx(f"snap {s['id']} {list(snap)}")
        # DISPATCH + RETRY
        ok = False; retries = TOOLS[tool].get("retry", 1)
        for attempt in range(retries + 1):
            try:
                ts = time.time(); res = await tools.execute(tool, args)
                tx(f"exec {s['id']} {tool} OK {int((time.time()-ts)*1000)}ms"); ok = True; break
            except Exception as e:
                tx(f"exec {s['id']} {tool} FAIL attempt {attempt+1}/{retries+1}: {e}")
                if attempt < retries:
                    await asyncio.sleep(POLICY["plan"]["retry_backoff_s"][min(attempt, 2)])
        if ok:
            done.append((s, snap))
            if tool == "climate.set" and "temp" in args and plan.get("speaker"):
                mem.learn_pref(f"{plan['speaker']}.climate.{args['entity']}.temp", args["temp"])
        elif TOOLS[tool].get("on_fail") == "skip":
            tx(f"skip {s['id']} (non-critical)")
        else:
            tx(f"ABORT {s['id']} reason=device_unreachable")
            await _rollback(done)
            tx(f"plan {plan['id']} ROLLED_BACK total {time.time()-t0:.1f}s")
            return f"{summarize([s])}沒成功，設備沒回應，已把前面的動作還原。"
    mem.session["last_plan"] = {"intent": plan["intent"], "steps": [x["tool"] for x in plan["steps"]], "args": [x["args"] for x in plan["steps"]]}
    tx(f"plan {plan['id']} DONE total {time.time()-t0:.1f}s")
    reply = plan.get("reply") or "好了。"
    if energy_notes:
        reply = reply.rstrip("。") + "。" + "；".join(dict.fromkeys(energy_notes)) + "。"
    mem.add_turn("assistant", reply)
    return reply


async def _rollback(done: list[tuple[dict, dict]]):
    for s, snap in reversed(done):
        if snap:
            tx(f"compensate {s['id']} → restore {list(snap)}")
            await tools.restore(snap)
