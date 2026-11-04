"""權限 scope、確認策略、深夜時段、never 清單"""
from __future__ import annotations
from datetime import datetime, time as dtime
from .config import POLICY, TOOLS


def _parse(t: str) -> dtime:
    h, m = t.split(":"); return dtime(int(h), int(m))


def in_window(window: list[str], now: datetime | None = None) -> bool:
    now = (now or datetime.now()).time()
    a, b = _parse(window[0]), _parse(window[1])
    return (a <= now or now < b) if a > b else (a <= now < b)


def is_quiet_hours(now: datetime | None = None) -> bool:
    return in_window(POLICY["confirm"]["quiet_hours"]["window"], now)


def is_never(tool: str) -> bool:
    return tool in POLICY.get("never", [])


def tool_scope(tool: str) -> str:
    return TOOLS.get(tool, {}).get("scope", "read")


def needs_confirm(tool: str, source: str = "voice") -> bool:
    t = TOOLS.get(tool)
    if not t:
        return True
    if t.get("confirm") is False:
        return False
    for ex in POLICY.get("exempt", []):
        if ex.get("tool") == tool or ex.get("source") == source or ex.get("scope") == t.get("scope"):
            return False
    return POLICY["scopes"].get(t.get("scope"), {}).get("confirm", True)


def is_accept(text: str) -> bool:
    t = text.strip().lower().rstrip("。！!")
    return any(t == a or t.startswith(a) for a in POLICY["confirm"]["accept"])


def is_reject(text: str) -> bool:
    t = text.strip().lower().rstrip("。！!")
    return any(t == a or t.startswith(a) for a in POLICY["confirm"]["reject"])


def appliance_denied(sleep_mode: bool) -> str | None:
    sc = POLICY["scopes"]["write.appliance"]
    if sleep_mode and sc.get("deny_when_sleep_mode"):
        return "睡眠模式中，不啟動家電"
    if in_window(sc.get("deny_window", ["23:00", "07:00"])):
        return "深夜時段不啟動家電"
    return None


def clamp_night(tool: str, args: dict) -> dict:
    """23:00–07:00 主臥亮度 / 音量上限 20%"""
    if not is_quiet_hours():
        return args
    sc = POLICY["scopes"]["write.comfort"]
    a = dict(args)
    if tool == "light.set" and a.get("area") == "master" and a.get("brightness", 0) > sc["night_master_brightness_max"]:
        a["brightness"] = sc["night_master_brightness_max"]
    if tool == "media.say" and a.get("target") in ("master_mini", "all") and a.get("volume", 0) > sc["night_master_volume_max"]:
        a["volume"] = sc["night_master_volume_max"]
    return a
