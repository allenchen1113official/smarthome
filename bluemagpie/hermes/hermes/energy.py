"""節能管家：AI 節能守門（每個計畫執行前修正參數）+ 用電/碳排報告。

憲章 VI：節能省碳是情境設計的最高目標。Hermes 是唯一的節能決策點——
HA 自動化只做量測與簡單反射（s00_energy.yaml），所有「要不要省、省多少」由這裡決定，
這樣住戶只要對一個管家說「這次不要省」就能全域放寬，不必逐個情境改。
"""
from __future__ import annotations
import logging, os, time
from datetime import datetime
import yaml
from .config import ROOT, CFG
from .ha import ha

log = logging.getLogger("hermes.energy")

try:
    with open(ROOT / "energy.yaml", encoding="utf-8") as f:
        ECFG: dict = yaml.safe_load(f) or {}
except FileNotFoundError:
    ECFG = {"enabled": False}

_pause_until: float = 0.0          # pause_guard 到期時間（epoch）
_cache: dict = {"mode": "eco", "lux": None, "ts": 0.0}


# ---------------- 狀態 ----------------
def _hm(t: str) -> int:
    h, m = t.split(":"); return int(h) * 60 + int(m)


def is_peak(now: datetime | None = None) -> bool:
    """台電二段式時間電價尖峰判斷（週末全離峰）"""
    t = ECFG.get("tariff") or {}
    now = now or datetime.now()
    if t.get("weekend_all_offpeak", True) and now.weekday() >= 5:
        return False
    windows = t.get("peak_summer") if now.month in (t.get("summer_months") or []) else t.get("peak_other")
    cur = now.hour * 60 + now.minute
    return any(_hm(a) <= cur < _hm(b) for a, b in (windows or []))


async def refresh(force: bool = False) -> dict:
    """讀 HA 的模式 / 守門 / 照度（快取 30 秒）"""
    if not force and time.time() - _cache["ts"] < 30:
        return _cache
    m = await ha.get_state(ECFG.get("mode_entity", "input_select.energy_mode"))
    g = await ha.get_state(ECFG.get("guard_entity", "input_boolean.energy_guard"))
    lx = await ha.get_state((ECFG.get("daylight") or {}).get("illuminance_entity", ""))
    _cache.update({
        "mode": (m or {}).get("state") if m and m["state"] in ECFG.get("modes", {}) else "eco",
        "guard": not g or g["state"] == "on",
        "lux": float(lx["state"]) if lx and lx["state"] not in ("unknown", "unavailable") else None,
        "ts": time.time(),
    })
    return _cache


def guard_active(st: dict) -> bool:
    return bool(ECFG.get("enabled", True)) and st.get("guard", True) and time.time() > _pause_until


# ---------------- 守門：修正每一步的參數 ----------------
async def clamp(tool: str, args: dict) -> tuple[dict, list[str]]:
    """回傳 (修正後 args, 說明清單)。只收緊、不放寬；comfort 模式或守門暫停時原樣回傳。"""
    st = await refresh()
    if not guard_active(st) or st["mode"] == "comfort":
        return args, []
    p = ECFG["modes"][st["mode"]]
    a, notes = dict(args), []

    if tool == "climate.set":
        mode = a.get("mode")
        if mode in (None, "cool", "auto") and "temp" in a:
            floor = p.get("peak_ac_min_cool", p["ac_min_cool"]) if is_peak() else p["ac_min_cool"]
            if a["temp"] < floor:
                notes.append(f"節能：冷氣最低 {floor} 度" + ("（尖峰時段）" if is_peak() else ""))
                a["temp"] = floor
        if mode == "heat" and "temp" in a and a["temp"] > p["ac_max_heat"]:
            notes.append(f"節能：暖氣最高 {p['ac_max_heat']} 度"); a["temp"] = p["ac_max_heat"]
        if mode == "cool" and p.get("ac_prefer_dry_rh_below"):
            room = CFG["areas"].get(a.get("entity", ""), {})
            rh = await ha.get_state(room.get("humidity", "")) if room.get("humidity") else None
            tmp = await ha.get_state(room.get("temperature", "")) if room.get("temperature") else None
            try:
                if rh and tmp and float(rh["state"]) < p["ac_prefer_dry_rh_below"] and float(tmp["state"]) <= 28:
                    notes.append("節能：室溫不高，改用除濕"); a["mode"] = "dry"
            except (TypeError, ValueError):
                pass
        if "fan" not in a and p.get("ac_fan_default"):
            a["fan"] = p["ac_fan_default"]

    elif tool == "light.set" and "brightness" in a:
        cap = p["light_max_pct"]
        lux_th = (ECFG.get("daylight") or {}).get("lux_threshold", 300)
        if st["lux"] is not None and st["lux"] >= lux_th and a.get("area") in ("living", "second"):
            cap = min(cap, p["daylight_light_max_pct"])
        if a["brightness"] > cap:
            notes.append(f"節能：亮度上限 {cap}%" + ("（白天自然光夠）" if cap == p["daylight_light_max_pct"] else ""))
            a["brightness"] = cap

    elif tool == "light.activate_scene" and st["mode"] == "eco" and a.get("scene") == "Focus":
        # Focus 5000K 100% 最耗電；eco 下改 Welcome 再由 light.set 守門
        notes.append("節能：Focus 改 Welcome"); a["scene"] = "Welcome"

    return a, notes


# ---------------- 工具 ----------------
async def _num(entity: str) -> float | None:
    if not entity:
        return None
    s = await ha.get_state(entity)
    try:
        return float(s["state"]) if s else None
    except (TypeError, ValueError):
        return None


async def report(period: str = "today") -> dict:
    sn = ECFG.get("sensors") or {}
    kwh = await _num(sn.get("month_kwh") if period == "month" else sn.get("today_kwh"))
    base = await _num(sn.get("baseline_entity"))
    power = await _num(sn.get("power_w"))
    factor = float(ECFG.get("carbon_kg_per_kwh", 0.474))
    days = datetime.now().day if period == "month" else 1
    out = {"period": period, "kwh": kwh, "power_w": power, "co2_kg": round(kwh * factor, 2) if kwh is not None else None,
           "mode": (await refresh())["mode"], "peak_now": is_peak()}
    if kwh is not None and base:
        out["saving_pct"] = round((1 - kwh / (base * days)) * 100, 1)
    top = []
    for name, ent in (sn.get("devices") or {}).items():
        v = await _num(ent)
        if v is not None:
            top.append((name, v))
    top.sort(key=lambda x: -x[1])
    out["top"] = top[:3]
    # 一句建議
    tips = []
    if top and top[0][0].startswith("冷氣") and kwh and top[0][1] / kwh > 0.5:
        tips.append("冷氣佔一半以上，設定溫度每高一度約省百分之六")
    if out.get("saving_pct", 0) < 0:
        tips.append("今天比基準高，晚上睡前讓我做一次巡檢")
    if is_peak():
        tips.append("現在是尖峰時段，洗衣烘衣建議等到晚上十二點後")
    out["tip"] = tips[0] if tips else "維持得不錯"
    return out


def report_text(r: dict) -> str:
    if r.get("kwh") is None:
        return "還沒有用電資料，請先確認 Shelly EM 或計量插座已接上。"
    label = {"today": "今天", "month": "這個月", "week": "這週"}[r["period"]]
    s = f"{label}用電 {r['kwh']:.1f} 度，約 {r['co2_kg']:.1f} 公斤碳排"
    if "saving_pct" in r:
        s += f"，比基準{'省' if r['saving_pct'] >= 0 else '多'}了 {abs(r['saving_pct']):.0f}%"
    if r.get("top"):
        s += "；最耗電是 " + "、".join(f"{n} {v:.1f} 度" for n, v in r["top"][:2])
    return s + f"。{r['tip']}。"


async def set_mode(mode: str, minutes: int | None = None) -> dict:
    await ha.call_service("input_select", "select_option", {"entity_id": ECFG["mode_entity"], "option": mode})
    if mode != "eco" and minutes:
        # HA 端 timer（s00_energy.yaml）到期自動切回 eco
        await ha.call_service("timer", "start", {"entity_id": "timer.energy_mode_revert", "duration": f"{minutes*60}"})
    await refresh(force=True)
    return {"mode": mode, "minutes": minutes}


def pause_guard(minutes: int) -> dict:
    global _pause_until
    _pause_until = time.time() + minutes * 60
    return {"paused_min": minutes}


async def idle_sweep(keep: str = "fridge") -> dict:
    """關無人房間燈/空調、切待機插座；交給 HA script.energy_idle_sweep（可還原）"""
    await ha.call_service("script", "energy_idle_sweep", {"keep": keep})
    return {"ok": True, "keep": keep}
