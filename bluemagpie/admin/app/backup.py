"""備份 / 推送到副節點 / 接收 / 還原 / 副節點監看與自動接手（取代 HAOS 的 hassio.* 與 standby_node.yaml）"""
from __future__ import annotations
import asyncio, io, logging, tarfile, time
from datetime import datetime
from pathlib import Path
import httpx
from . import settings as S, docker_ctl as D

log = logging.getLogger("magpie.backup")
BACKUPS = S.PROJECT / "backups"
STATE = {"last_backup": None, "last_push": None, "peer_ok": None, "peer_down_since": None, "promoted": False, "events": []}
INCLUDE = ["config/homeassistant", "config/zigbee2mqtt", "config/hermes", "config/mosquitto", "data/hermes", "data/admin"]
EXCLUDE_PARTS = ("home-assistant_v2.db-wal", "home-assistant_v2.db-shm", "__pycache__", "/www/hermes/", "/logs/")


def event(msg: str):
    STATE["events"] = ([f"{datetime.now():%m-%d %H:%M:%S} {msg}"] + STATE["events"])[:50]
    log.info(msg)


def _filter(ti: tarfile.TarInfo):
    return None if any(p in ti.name for p in EXCLUDE_PARTS) else ti


def create(name: str | None = None) -> Path:
    BACKUPS.mkdir(exist_ok=True)
    name = name or f"magpie_{datetime.now():%Y%m%d_%H%M}.tar.gz"
    path = BACKUPS / name
    with tarfile.open(path, "w:gz") as tf:
        for rel in INCLUDE:
            p = S.PROJECT / rel
            if p.exists():
                tf.add(p, arcname=rel, filter=_filter)
    STATE["last_backup"] = name
    _prune()
    event(f"備份完成 {name}（{path.stat().st_size // 1024} KB）")
    return path


def _prune():
    keep = S.load()["cluster"].get("keep", 30)
    files = sorted(BACKUPS.glob("magpie_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        p.unlink(missing_ok=True)


def list_backups() -> list[dict]:
    return [{"name": p.name, "size_kb": p.stat().st_size // 1024, "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"), "received": p.name.startswith("recv_")}
            for p in sorted(BACKUPS.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)]


async def push(path: Path) -> str:
    d = S.load()["cluster"]
    if not d["peer_url"]:
        return "未設定副節點"
    try:
        async with httpx.AsyncClient(timeout=120) as cl:
            r = await cl.post(d["peer_url"].rstrip("/") + "/api/backup/receive", headers={"X-Magpie-Secret": d["shared_secret"]},
                              files={"file": (path.name, path.read_bytes(), "application/gzip")})
            r.raise_for_status()
        STATE["last_push"] = f"{path.name} @ {datetime.now():%H:%M}"
        event(f"已推送到副節點 {d['peer_url']}")
        return "ok"
    except Exception as e:
        event(f"推送失敗：{e}")
        return f"失敗：{e}"


def receive(name: str, data: bytes) -> str:
    BACKUPS.mkdir(exist_ok=True)
    safe = "recv_" + Path(name).name.replace("recv_", "")
    (BACKUPS / safe).write_bytes(data)
    _prune_recv()
    event(f"收到主節點備份 {safe}")
    return safe


def _prune_recv():
    keep = S.load()["cluster"].get("keep", 30)
    files = sorted(BACKUPS.glob("recv_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        p.unlink(missing_ok=True)


def latest_received() -> Path | None:
    files = sorted(BACKUPS.glob("recv_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def restore(name: str, restart: bool = True) -> dict:
    path = BACKUPS / Path(name).name
    if not path.exists():
        raise FileNotFoundError(name)
    D.stop(["homeassistant", "zigbee2mqtt", "hermes", "bot"])
    with tarfile.open(path, "r:gz") as tf:
        for m in tf.getmembers():
            if m.name.startswith("/") or ".." in m.name:
                raise ValueError("不安全的備份內容")
        tf.extractall(S.PROJECT)
    event(f"已還原 {name}")
    res = D.start(["homeassistant", "zigbee2mqtt", "hermes", "bot"]) if restart else {}
    return {"restored": name, "containers": res}


# ---------- 副節點：監看主節點，失聯 5 分鐘自動接手 ----------
async def _promote():
    latest = latest_received()
    if not latest:
        event("要接手但沒有收到任何備份，放棄"); return
    d = S.load()
    d["site"]["role"] = "primary"
    S.apply(d)
    # 還原主節點設定（含 HA .storage → token 相同）；role 已改 primary，再把 input_text 由 HA 自動化讀 is_primary
    restore(latest.name, restart=False)
    # 讓 HA 知道自己是接手節點
    try:
        p = S.CONFIG / "homeassistant" / "packages" / "s00_node.yaml"
        if p.exists():
            p.write_text(p.read_text(encoding="utf-8").replace("initial: primary", "initial: standby_promoted"), encoding="utf-8")
    except Exception:
        pass
    res = D.start(["homeassistant", "zigbee2mqtt", "hermes", "bot"])
    STATE["promoted"] = True
    event(f"🛟 已自動接手為主節點：{res}")
    await _notify_both("🛟 青鳥副節點已自動接手：Home Assistant、Zigbee、Hermes 已在副節點啟動。主節點修好後請在後台按「回切」。")


async def _notify_both(msg: str):
    """透過本節點 HA REST 推播（接手後 HA 在本機；接手前用主節點的也行）"""
    d = S.load()
    tok = d["ha"]["token"]
    if not tok: return
    host = "host.docker.internal" if d["site"]["network_mode"] == "host" else "homeassistant"
    try:
        async with httpx.AsyncClient(timeout=10) as cl:
            await cl.post(f"http://{host}:8123/api/services/notify/both", headers={"Authorization": f"Bearer {tok}"}, json={"message": msg})
    except Exception as e:
        log.warning("notify failed: %s", e)


async def scheduler():
    """主節點：每小時 :05 備份並推送。副節點：每 30 秒監看主節點。"""
    last_hour = None
    while True:
        try:
            d = S.load()
            role = d["site"]["role"]; c = d["cluster"]
            now = datetime.now()
            if role == "primary":
                if c.get("hourly_backup") and now.minute >= 5 and last_hour != now.hour:
                    last_hour = now.hour
                    p = await asyncio.to_thread(create, None)
                    await push(p)
            elif role == "standby" and c.get("peer_url") and not STATE["promoted"]:
                ok = False
                try:
                    async with httpx.AsyncClient(timeout=5) as cl:
                        r = await cl.get(c["peer_url"].rstrip("/") + "/api/health/self"); ok = r.status_code == 200
                except Exception:
                    ok = False
                STATE["peer_ok"] = ok
                if ok:
                    STATE["peer_down_since"] = None
                else:
                    STATE["peer_down_since"] = STATE["peer_down_since"] or time.time()
                    down = time.time() - STATE["peer_down_since"]
                    if down > 300 and c.get("auto_promote"):
                        event("主節點失聯超過 5 分鐘，開始自動接手")
                        await _promote()
                    elif 290 < down <= 300:
                        await _notify_both("⚠️ 主節點失聯將滿 5 分鐘，副節點即將自動接手（後台可取消）。")
        except Exception as e:
            log.exception("scheduler: %s", e)
        await asyncio.sleep(30)
