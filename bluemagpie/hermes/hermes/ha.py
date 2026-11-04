"""Home Assistant REST / WebSocket 用戶端（Hermes 唯一碰設備的通道）— 支援主/副節點自動切換"""
from __future__ import annotations
import asyncio, json, logging, time
import httpx
from .config import CFG, ha_token

log = logging.getLogger("hermes.ha")


class HA:
    def __init__(self):
        cfg = CFG["ha"]
        self.urls: list[str] = [u.rstrip("/") for u in (cfg.get("urls") or [cfg.get("url")])]
        self.idx = 0
        self.timeout = cfg.get("timeout_s", 1.1)
        self.health_interval = cfg.get("health_interval_s", 60)
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {ha_token()}", "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        self.world: dict[str, dict] = {}       # entity_id -> {state, attrs, updated_at}
        self._ws_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None
        self._ws_generation = 0

    @property
    def base(self) -> str:
        return self.urls[self.idx]

    # ---------- 節點切換 ----------
    async def _alive(self, url: str) -> bool:
        try:
            r = await self._client.get(url + "/api/", timeout=2)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def _switch(self, reason: str):
        for i, u in enumerate(self.urls):
            if i != self.idx and await self._alive(u):
                log.warning("ha_switch %s → %s (%s)", self.base, u, reason)
                self.idx = i
                self._ws_generation += 1       # 讓 WS 迴圈重連到新節點
                return True
        return False

    async def _request(self, method: str, path: str, **kw):
        try:
            r = await self._client.request(method, self.base + path, **kw)
            return r
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if await self._switch(f"{type(e).__name__}"):
                return await self._client.request(method, self.base + path, **kw)
            raise

    async def _health_loop(self):
        while True:
            await asyncio.sleep(self.health_interval)
            if not await self._alive(self.base):
                await self._switch("health check failed")
            elif self.idx != 0 and await self._alive(self.urls[0]):
                log.info("主節點已恢復，但維持使用 %s（回切由人工執行後重啟 Hermes）", self.base)

    # ---------- REST ----------
    async def call_service(self, domain: str, service: str, data: dict) -> list:
        r = await self._request("POST", f"/api/services/{domain}/{service}", json=data)
        r.raise_for_status()
        return r.json()

    async def get_state(self, entity_id: str) -> dict | None:
        w = self.world.get(entity_id)
        if w and time.time() - w["updated_at"] < 60:
            return w
        try:
            r = await self._request("GET", f"/api/states/{entity_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            j = r.json()
            w = {"state": j["state"], "attrs": j.get("attributes", {}), "updated_at": time.time()}
            self.world[entity_id] = w
            return w
        except httpx.HTTPError as e:
            log.warning("get_state %s failed: %s", entity_id, e)
            return w

    async def is_online(self, entity_id: str) -> bool:
        s = await self.get_state(entity_id)
        return bool(s) and s["state"] not in ("unavailable", "unknown")

    async def all_states(self) -> list[dict]:
        r = await self._request("GET", "/api/states", timeout=5)
        r.raise_for_status()
        return r.json()

    # ---------- WebSocket：state_changed → world model ----------
    def start_ws(self):
        if not self._health_task:
            self._health_task = asyncio.create_task(self._health_loop())
        if CFG["ha"].get("ws_enabled", True) and not self._ws_task:
            self._ws_task = asyncio.create_task(self._ws_loop())

    async def _ws_loop(self):
        try:
            import websockets
        except ImportError:
            log.warning("websockets 未安裝，world model 改用 REST 輪詢")
            return
        while True:
            gen = self._ws_generation
            url = self.base.replace("http", "ws", 1) + "/api/websocket"
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    await ws.recv()  # auth_required
                    await ws.send(json.dumps({"type": "auth", "access_token": ha_token()}))
                    await ws.recv()  # auth_ok
                    await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
                    for s in await self.all_states():
                        self.world[s["entity_id"]] = {"state": s["state"], "attrs": s.get("attributes", {}), "updated_at": time.time()}
                    log.info("WS 已連線 %s，world model %d entities", self.base, len(self.world))
                    async for raw in ws:
                        if gen != self._ws_generation:
                            break                      # 節點已切換，重連
                        msg = json.loads(raw)
                        if msg.get("type") == "event":
                            ns = msg["event"]["data"].get("new_state")
                            if ns:
                                self.world[ns["entity_id"]] = {"state": ns["state"], "attrs": ns.get("attributes", {}), "updated_at": time.time()}
            except Exception as e:
                log.warning("WS 斷線：%s，5 秒後重連", e)
                await self._switch("ws disconnected")
                await asyncio.sleep(5)


ha = HA()
