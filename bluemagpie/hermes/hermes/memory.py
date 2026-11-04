"""三層記憶：session（10 min）/ world（由 ha.world 提供）/ pref、alias、holding、paper_orders（SQLite WAL）"""
from __future__ import annotations
import json, os, sqlite3, time
from .config import CFG

SCHEMA = """
CREATE TABLE IF NOT EXISTS session (id TEXT PRIMARY KEY, started_at INT, speaker TEXT, turns TEXT, last_plan_id TEXT, expires_at INT);
CREATE TABLE IF NOT EXISTS pref (key TEXT PRIMARY KEY, value TEXT, n INT, confidence REAL, updated_at INT);
CREATE TABLE IF NOT EXISTS alias (phrase TEXT PRIMARY KEY, entity TEXT, learned_from TEXT);
CREATE TABLE IF NOT EXISTS holding (symbol TEXT PRIMARY KEY, shares INT, cost REAL, note TEXT, updated_at INT);
CREATE TABLE IF NOT EXISTS paper_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INT, symbol TEXT, side TEXT, shares INT, price REAL);
CREATE TABLE IF NOT EXISTS snapshot (id TEXT PRIMARY KEY, created_at INT, data TEXT);
CREATE TABLE IF NOT EXISTS alert_log (day TEXT, symbol TEXT, name TEXT, ts INT);
CREATE TABLE IF NOT EXISTS daily (symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INT, PRIMARY KEY(symbol,date));
"""


class Memory:
    def __init__(self):
        path = CFG["paths"]["db"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        for phrase, ent in (CFG.get("aliases") or {}).items():
            self.db.execute("INSERT OR IGNORE INTO alias VALUES (?,?,?)", (phrase, ent, "config"))
        self.db.commit()
        self.session: dict = {"turns": [], "last_plan": None, "pending": None, "speaker": None, "expires_at": 0}

    # ----- session（單一家庭，記憶體內即可；10 分鐘 TTL）-----
    def touch(self, speaker: str | None):
        now = time.time()
        if now > self.session["expires_at"]:
            self.session = {"turns": [], "last_plan": None, "pending": None, "speaker": speaker, "expires_at": 0}
        self.session["expires_at"] = now + 600
        if speaker:
            self.session["speaker"] = speaker

    def add_turn(self, role: str, text: str):
        self.session["turns"] = (self.session["turns"] + [{"role": role, "text": text}])[-6:]

    # ----- 偏好 -----
    def learn_pref(self, key: str, value):
        row = self.db.execute("SELECT value,n FROM pref WHERE key=?", (key,)).fetchone()
        n = (row[1] if row else 0) + 1
        conf = min(0.95, 0.3 + 0.05 * n)
        self.db.execute("INSERT OR REPLACE INTO pref VALUES (?,?,?,?,?)", (key, json.dumps(value), n, conf, int(time.time())))
        self.db.commit()

    def prefs(self, prefix: str = "") -> list[tuple]:
        return self.db.execute("SELECT key,value,n,confidence FROM pref WHERE key LIKE ? AND confidence>=0.6", (prefix + "%",)).fetchall()

    def forget_pref(self, key: str):
        self.db.execute("DELETE FROM pref WHERE key=?", (key,)); self.db.commit()

    # ----- alias -----
    def resolve_alias(self, phrase: str) -> str | None:
        r = self.db.execute("SELECT entity FROM alias WHERE phrase=?", (phrase,)).fetchone()
        return r[0] if r else None

    # ----- snapshot -----
    def save_snapshot(self, sid: str, data: dict):
        self.db.execute("INSERT OR REPLACE INTO snapshot VALUES (?,?,?)", (sid, int(time.time()), json.dumps(data)))
        self.db.execute("DELETE FROM snapshot WHERE created_at < ?", (int(time.time()) - 600,))
        self.db.commit()

    def load_snapshot(self, sid: str) -> dict | None:
        r = self.db.execute("SELECT data FROM snapshot WHERE id=?", (sid,)).fetchone()
        return json.loads(r[0]) if r else None

    # ----- 股票 -----
    def holdings(self) -> dict[str, dict]:
        return {s: {"shares": sh, "cost": c} for s, sh, c in self.db.execute("SELECT symbol,shares,cost FROM holding")}

    def paper_order(self, symbol: str, side: str, shares: int, price: float) -> int:
        cur = self.db.execute("INSERT INTO paper_orders (ts,symbol,side,shares,price) VALUES (?,?,?,?,?)", (int(time.time()), symbol, side, shares, price))
        h = self.db.execute("SELECT shares,cost FROM holding WHERE symbol=?", (symbol,)).fetchone()
        if side == "buy":
            old_sh, old_cost = (h or (0, 0.0))
            new_sh = old_sh + shares
            new_cost = (old_sh * old_cost + shares * price) / new_sh
            self.db.execute("INSERT OR REPLACE INTO holding VALUES (?,?,?,?,?)", (symbol, new_sh, new_cost, "", int(time.time())))
        elif h:
            left = max(0, h[0] - shares)
            if left:
                self.db.execute("UPDATE holding SET shares=?, updated_at=? WHERE symbol=?", (left, int(time.time()), symbol))
            else:
                self.db.execute("DELETE FROM holding WHERE symbol=?", (symbol,))
        self.db.commit()
        return cur.lastrowid

    def alert_count_today(self, day: str, symbol: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM alert_log WHERE day=? AND symbol=?", (day, symbol)).fetchone()[0]

    def log_alert(self, day: str, symbol: str, name: str):
        self.db.execute("INSERT INTO alert_log VALUES (?,?,?,?)", (day, symbol, name, int(time.time()))); self.db.commit()

    def upsert_daily(self, symbol: str, rows: list[tuple]):
        self.db.executemany("INSERT OR REPLACE INTO daily VALUES (?,?,?,?,?,?,?)", [(symbol, *r) for r in rows])
        keep = CFG.get("market", {}).get("daily_keep", 250)
        self.db.execute("DELETE FROM daily WHERE symbol=? AND date NOT IN (SELECT date FROM daily WHERE symbol=? ORDER BY date DESC LIMIT ?)", (symbol, symbol, keep))
        self.db.commit()

    def daily(self, symbol: str) -> list[tuple]:
        return self.db.execute("SELECT date,open,high,low,close,volume FROM daily WHERE symbol=? ORDER BY date", (symbol,)).fetchall()


mem = Memory()
