"""工具實作：每個工具 = (受影響實體, 執行, 快照/還原)。Hermes 只透過 HA 服務碰設備。"""
from __future__ import annotations
import logging
from .config import CFG
from .ha import ha
from .textnorm import for_tts

log = logging.getLogger("hermes.tools")
AREAS = CFG["areas"]
MEDIA = CFG["media"]
NOTIFY = CFG["notify"]


def _light_target(args: dict) -> str:
    if args.get("entity"):
        return args["entity"]
    return AREAS[args["area"]]["light"]


def affected_entities(tool: str, args: dict) -> list[str]:
    if tool in ("light.set", "light.activate_scene"):
        return [_light_target(args)] if (args.get("entity") or args.get("area")) else ["light.living_all"]
    if tool == "climate.set":
        return [AREAS[args["entity"]]["climate"]]
    if tool == "cover.set_position":
        return [f"cover.{args['entity']}"]
    if tool == "vacuum.control":
        return ["vacuum.qrevo"]
    return []


async def snapshot(entities: list[str]) -> dict:
    snap = {}
    for e in entities:
        s = await ha.get_state(e)
        if s:
            snap[e] = {"state": s["state"], "attrs": {k: s["attrs"].get(k) for k in ("brightness", "color_temp_kelvin", "temperature", "hvac_mode", "fan_mode", "current_position")}}
    return snap


async def restore(snap: dict):
    for e, s in snap.items():
        dom = e.split(".")[0]
        a = s["attrs"]
        try:
            if dom == "light":
                if s["state"] == "on":
                    data = {"entity_id": e}
                    if a.get("brightness") is not None: data["brightness"] = a["brightness"]
                    if a.get("color_temp_kelvin"): data["color_temp_kelvin"] = a["color_temp_kelvin"]
                    await ha.call_service("light", "turn_on", data)
                else:
                    await ha.call_service("light", "turn_off", {"entity_id": e})
            elif dom == "climate":
                await ha.call_service("climate", "set_hvac_mode", {"entity_id": e, "hvac_mode": s["state"]})
                if a.get("temperature"):
                    await ha.call_service("climate", "set_temperature", {"entity_id": e, "temperature": a["temperature"]})
            elif dom == "cover" and a.get("current_position") is not None:
                await ha.call_service("cover", "set_cover_position", {"entity_id": e, "position": a["current_position"]})
            elif dom == "vacuum":
                await ha.call_service("vacuum", "return_to_base", {"entity_id": e})
        except Exception as ex:
            log.warning("restore %s failed: %s", e, ex)


async def execute(tool: str, args: dict) -> dict:
    """回傳 {ok, applied}。丟出例外代表失敗（由 orchestrator 重試）。"""
    if tool == "light.set":
        data = {"entity_id": _light_target(args), "transition": args.get("transition", 1.0)}
        if "brightness" in args: data["brightness_pct"] = args["brightness"]
        if "kelvin" in args: data["color_temp_kelvin"] = args["kelvin"]
        await ha.call_service("light", "turn_on", data)
        return {"ok": True, "applied": data}

    if tool == "light.activate_scene":
        # HA 內 Hue 場景 entity 命名：scene.<area>_<scene>（03 章），找不到就退回 hue.activate_scene
        area = args.get("area", "living")
        ent = f"scene.{area}_{args['scene'].lower()}"
        if await ha.get_state(ent):
            await ha.call_service("scene", "turn_on", {"entity_id": ent})
        else:
            await ha.call_service("hue", "activate_scene", {"group_name": area, "scene_name": args["scene"]})
        return {"ok": True, "applied": {"scene": ent}}

    if tool == "climate.set":
        # 走 script.ac_set：雲端 unavailable 時自動改走 IR（03 章）
        data = {"room": args["entity"]}
        if "temp" in args: data["temperature"] = args["temp"]
        if "mode" in args: data["hvac_mode"] = args["mode"]
        if "fan" in args: data["fan_mode"] = args["fan"]
        await ha.call_service("script", "ac_set", data)
        return {"ok": True, "applied": data}

    if tool == "cover.set_position":
        await ha.call_service("cover", "set_cover_position", {"entity_id": f"cover.{args['entity']}", "position": args["position"]})
        return {"ok": True, "applied": args}

    if tool == "media.say":
        target = args.get("target", "living_homepod")
        data = {"message": for_tts(args["text"]), "target": target}
        if "volume" in args: data["volume"] = args["volume"]
        await ha.call_service("script", "say", data)
        return {"ok": True, "applied": data}

    if tool == "vacuum.control":
        act = args["action"]
        if act == "start": await ha.call_service("vacuum", "start", {"entity_id": "vacuum.qrevo"})
        elif act == "pause": await ha.call_service("vacuum", "pause", {"entity_id": "vacuum.qrevo"})
        elif act == "dock": await ha.call_service("vacuum", "return_to_base", {"entity_id": "vacuum.qrevo"})
        elif act == "spot":
            await ha.call_service("script", "vacuum_rooms", {"rooms": args.get("rooms", ["living"])})
        return {"ok": True, "applied": args}

    if tool == "notify.push":
        svc = NOTIFY[args.get("to", "both")].split(".", 1)[1]
        data = {"message": args["message"], "data": {}}
        if args.get("priority") == "time_sensitive":
            data["data"]["push"] = {"interruption-level": "time-sensitive"}
        if args.get("image"):
            data["data"]["image"] = args["image"]
        if args["message"].startswith("Hermes："):   # 深夜確認：推播附「好 / 取消」按鈕（情境 35）
            data["data"]["actions"] = [{"action": "HERMES_YES", "title": "好"}, {"action": "HERMES_NO", "title": "取消"}]
            data["data"]["tag"] = "hermes_confirm"
        await ha.call_service("notify", svc, data)
        return {"ok": True, "applied": {"to": args.get("to")}}

    if tool == "emergency.sos":
        await ha.call_service("script", "emergency_sos", {"reason": args.get("reason", "voice"), "silent": args.get("silent", False)})
        return {"ok": True, "applied": args}

    if tool == "home.get_state":
        return {"ok": True, "states": await read_state(args)}

    if tool.startswith("market."):
        from . import market
        from .memory import mem
        if tool == "market.quote":
            return {"ok": True, **await market.quote(args["symbol"])}
        if tool == "market.indicators":
            return {"ok": True, **market.indicators(args["symbol"], args.get("set"))}
        if tool == "market.screen":
            return {"ok": True, **await market.screen(args.get("top_n"), args.get("min_score"))}
        if tool == "market.paper_order":
            price = args.get("price") or (await market.quote(args["symbol"]))["price"]
            oid = mem.paper_order(args["symbol"], args["side"], int(args["shares"]), float(price))
            return {"ok": True, "order_id": f"po_{oid}", "price": price}

    raise ValueError(f"unknown tool {tool}")


async def read_state(args: dict) -> dict:
    out = {}
    if args.get("entity"):
        s = await ha.get_state(args["entity"]); out[args["entity"]] = s and {"state": s["state"], **{k: v for k, v in s["attrs"].items() if k in ("brightness", "temperature", "current_temperature", "current_position", "humidity")}}
        return out
    area = args.get("area", "living")
    for role, ent in AREAS.get(area, {}).items():
        if not ent: continue
        s = await ha.get_state(ent)
        if s:
            out[role] = {"state": s["state"], **{k: v for k, v in s["attrs"].items() if k in ("brightness", "temperature", "current_temperature", "current_position")}}
    return out
