"""容器控制：透過 docker.sock 查狀態、重啟、啟停（熱備接手時啟動主節點 profile 的容器）"""
from __future__ import annotations
import logging
import docker

log = logging.getLogger("magpie.docker")
NAMES = {
    "admin": "magpie-admin", "homeassistant": "magpie-homeassistant", "mosquitto": "magpie-mosquitto",
    "zigbee2mqtt": "magpie-zigbee2mqtt", "whisper": "magpie-whisper", "piper": "magpie-piper",
    "ollama": "magpie-ollama", "hermes": "magpie-hermes",
}
PRIMARY_ONLY = ["homeassistant", "zigbee2mqtt", "hermes"]

_client = None


def client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def status() -> dict:
    out = {}
    try:
        cs = {c.name: c for c in client().containers.list(all=True)}
    except Exception as e:
        return {k: {"state": f"docker 無法連線：{e}"} for k in NAMES}
    for key, name in NAMES.items():
        c = cs.get(name)
        if not c:
            out[key] = {"state": "absent"}
        else:
            h = c.attrs.get("State", {}).get("Health", {}).get("Status")
            out[key] = {"state": c.status, "health": h, "image": (c.image.tags or [""])[0], "started": c.attrs["State"].get("StartedAt", "")[:19]}
    return out


def restart(keys: list[str]) -> dict:
    res = {}
    for k in keys:
        try:
            c = client().containers.get(NAMES[k]); c.restart(timeout=20); res[k] = "restarted"
        except docker.errors.NotFound:
            res[k] = "absent"
        except Exception as e:
            res[k] = f"error: {e}"
    return res


def start(keys: list[str]) -> dict:
    res = {}
    for k in keys:
        try:
            c = client().containers.get(NAMES[k]); c.start(); res[k] = "started"
        except docker.errors.NotFound:
            res[k] = "absent（請在主機執行 docker compose --profile primary up -d 建立容器）"
        except Exception as e:
            res[k] = f"error: {e}"
    return res


def stop(keys: list[str]) -> dict:
    res = {}
    for k in keys:
        try:
            c = client().containers.get(NAMES[k]); c.stop(timeout=20); res[k] = "stopped"
        except docker.errors.NotFound:
            res[k] = "absent"
        except Exception as e:
            res[k] = f"error: {e}"
    return res


def logs(key: str, tail: int = 200) -> str:
    try:
        return client().containers.get(NAMES[key]).logs(tail=tail).decode("utf-8", "replace")
    except Exception as e:
        return f"無法取得記錄：{e}"
