"""青鳥 · 台灣藍鵲 Magpie Admin — 後台 API 與網頁"""
from __future__ import annotations
import asyncio, logging, os, secrets
from pathlib import Path
import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from . import settings as S, docker_ctl as D, backup as B, openclaw as OC

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("magpie")
app = FastAPI(title="青鳥 Magpie Admin", version="0.1")
STATIC = Path(__file__).parent / "static"
basic = HTTPBasic()


def _password() -> str:
    return S.load()["site"].get("admin_password") or os.environ.get("MAGPIE_ADMIN_PASSWORD", "bluemagpie")


def auth(c: HTTPBasicCredentials = Depends(basic)):
    if not secrets.compare_digest(c.password, _password()):
        raise HTTPException(401, "密碼錯誤", headers={"WWW-Authenticate": "Basic"})
    return True


def peer_auth(req: Request):
    if not secrets.compare_digest(req.headers.get("X-Magpie-Secret", ""), S.load()["cluster"]["shared_secret"] or "__unset__"):
        raise HTTPException(403, "shared secret 不符")
    return True


@app.on_event("startup")
async def _startup():
    S.DATA.mkdir(parents=True, exist_ok=True)
    d = S.load()
    if d["site"]["role"] == "standby" and not B.STATE["promoted"]:
        await asyncio.to_thread(D.stop, ["homeassistant", "zigbee2mqtt", "hermes", "bot"])   # 副節點平時不跑這三個
    asyncio.create_task(B.scheduler())
    log.info("青鳥 Magpie Admin 就緒，專案目錄 %s", S.PROJECT)


# ---------- 網頁 ----------
@app.get("/")
async def index(_=Depends(auth)):
    return FileResponse(STATIC / "index.html")


# ---------- 設定 ----------
@app.get("/api/schema")
async def schema(_=Depends(auth)):
    return S.SCHEMA


@app.get("/api/settings")
async def get_settings(_=Depends(auth)):
    d = S.load()
    applied = (S.DATA / "applied_at").read_text() if (S.DATA / "applied_at").exists() else None
    return {"settings": S.masked(d), "applied_at": applied, "role": d["site"]["role"]}


@app.put("/api/settings")
async def put_settings(body: dict, _=Depends(auth)):
    d = S.merge_from_client(S.load(), body)
    S.save(d)
    return {"ok": True}


@app.post("/api/apply")
async def apply(body: dict | None = None, _=Depends(auth)):
    d = S.merge_from_client(S.load(), body or {})
    res = await asyncio.to_thread(S.apply, d)
    restart = (body or {}).get("restart", True)
    if restart:
        keys = ["mosquitto"] + (["zigbee2mqtt", "hermes", "bot", "homeassistant"] if d["site"]["role"] == "primary" else [])
        res["restart"] = await asyncio.to_thread(D.restart, keys)
    res["note"] = "埠號 / 模型 / profile 變更需在主機執行：docker compose up -d（後台無法自行重建容器）"
    return res


# ---------- 健康 ----------
@app.get("/api/health/self")
async def health_self():
    return {"ok": True, "role": S.load()["site"]["role"], "promoted": B.STATE["promoted"]}


async def _probe(url: str, headers: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=3) as cl:
            r = await cl.get(url, headers=headers)
            return {"ok": r.status_code < 500, "code": r.status_code}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


@app.get("/api/health")
async def health(_=Depends(auth)):
    d = S.load()
    host = "host.docker.internal" if d["site"]["network_mode"] == "host" else None
    tok = d["ha"]["token"]
    checks = {
        "homeassistant": await _probe(f"http://{host or 'homeassistant'}:8123/api/", {"Authorization": f"Bearer {tok}"} if tok else None),
        "hermes": await _probe(f"http://{host or 'hermes'}:8800/v1/health"),
        "zigbee2mqtt": await _probe(f"http://{host or 'zigbee2mqtt'}:8080/"),
        "bot": await _probe(f"http://{host or 'bot'}:8900/v1/health"),
        "ollama": await _probe((d["voice"]["ollama_url"] if d["voice"]["ollama_source"] == "host" else "http://ollama:11434") + "/api/tags"),
    }
    if d["cluster"]["peer_url"]:
        checks["peer"] = await _probe(d["cluster"]["peer_url"].rstrip("/") + "/api/health/self")
    return {"containers": D.status(), "services": checks, "backup": {k: B.STATE[k] for k in ("last_backup", "last_push", "peer_ok", "promoted")}, "events": B.STATE["events"][:20]}


@app.get("/api/logs/{key}", response_class=PlainTextResponse)
async def logs(key: str, tail: int = 200, _=Depends(auth)):
    if key not in D.NAMES:
        raise HTTPException(404)
    return D.logs(key, tail)


@app.post("/api/containers/{action}")
async def containers(action: str, body: dict, _=Depends(auth)):
    keys = [k for k in body.get("keys", []) if k in D.NAMES]
    fn = {"restart": D.restart, "start": D.start, "stop": D.stop}.get(action)
    if not fn:
        raise HTTPException(400)
    return await asyncio.to_thread(fn, keys)


# ---------- 備份 / 熱備 ----------
@app.get("/api/backup")
async def backups(_=Depends(auth)):
    return {"files": B.list_backups(), "state": B.STATE}


@app.post("/api/backup/run")
async def backup_run(req: Request):
    """後台按鈕（Basic auth）或 HA rest_command（X-Magpie-Secret）皆可呼叫"""
    sec = req.headers.get("X-Magpie-Secret")
    if sec is not None:
        peer_auth(req)
    else:
        try:
            c = await basic(req); auth(c)
        except HTTPException:
            raise
    p = await asyncio.to_thread(B.create, None)
    pushed = await B.push(p)
    return {"name": p.name, "pushed": pushed}


@app.post("/api/backup/receive")
async def backup_receive(file: UploadFile = File(...), _=Depends(peer_auth)):
    data = await file.read()
    return {"saved": B.receive(file.filename, data)}


@app.post("/api/backup/restore")
async def backup_restore(body: dict, _=Depends(auth)):
    return await asyncio.to_thread(B.restore, body["name"], body.get("restart", True))


@app.post("/api/cluster/promote")
async def promote(_=Depends(auth)):
    await B._promote()
    return {"promoted": B.STATE["promoted"], "events": B.STATE["events"][:5]}


@app.post("/api/cluster/demote")
async def demote(_=Depends(auth)):
    """回切：本節點退回副節點（先確認主節點已還原最新備份並正常）"""
    d = S.load(); d["site"]["role"] = "standby"; S.apply(d)
    res = D.stop(["homeassistant", "zigbee2mqtt", "hermes", "bot"])
    B.STATE["promoted"] = False; B.STATE["peer_down_since"] = None
    B.event("已回切為副節點")
    return {"ok": True, "containers": res}


# ---------- OpenClaw 本地語音 ----------
@app.get("/api/openclaw/status")
async def openclaw_status(_=Depends(auth)):
    return await OC.status()


@app.post("/api/openclaw/pull")
async def openclaw_pull(_=Depends(auth)):
    return await OC.pull_model()


@app.post("/api/openclaw/setup")
async def openclaw_setup(_=Depends(auth)):
    return await OC.setup_ha()


@app.get("/api/brand")
async def brand():
    return {"name": "青鳥 · 台灣藍鵲", "en": "BlueMagpie", "version": "0.1.0"}
