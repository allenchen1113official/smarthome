"""股票模組：TWSE 公開行情（白名單唯讀）、本地指標計算、盤後掃描圖卡、模擬單。失敗明說，不猜數字。"""
from __future__ import annotations
import asyncio, logging, os, time
from datetime import date, datetime
import httpx
from .config import MARKET, CFG
from .memory import mem

log = logging.getLogger("hermes.market")
_quote_cache: dict[str, tuple[float, dict]] = {}
_names: dict[str, str] = {}


async def quote(symbol: str) -> dict:
    """即時報價。回傳 {symbol,name,price,change_pct,volume,as_of,delayed_min} 或 raise."""
    now = time.time()
    c = _quote_cache.get(symbol)
    if c and now - c[0] < 60:
        return c[1]
    url = MARKET["source"]["realtime"]
    params = {"ex_ch": f"tse_{symbol}.tw|otc_{symbol}.tw", "json": "1", "delay": "0"}
    async with httpx.AsyncClient(timeout=MARKET["source"]["timeout_s"]) as cl:
        r = await cl.get(url, params=params)
        r.raise_for_status()
        arr = r.json().get("msgArray") or []
    if not arr:
        raise LookupError(f"{symbol} 查無報價")
    m = arr[0]
    price = _f(m.get("z")) or _f((m.get("b") or "_").split("_")[0]) or _f(m.get("y"))
    prev = _f(m.get("y"))
    q = {"symbol": symbol, "name": m.get("n", symbol), "price": price,
         "change_pct": round((price - prev) / prev * 100, 2) if prev else 0.0,
         "volume": int(_f(m.get("v")) or 0), "as_of": m.get("t", ""), "delayed_min": 0}
    _names[symbol] = q["name"]
    _quote_cache[symbol] = (now, q)
    return q


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None


async def fetch_daily(symbol: str, months: int = 3):
    """抓最近幾個月日線進 hermes.db（batch lane 用）"""
    url = MARKET["source"]["daily"]
    today = date.today()
    async with httpx.AsyncClient(timeout=MARKET["source"]["timeout_s"]) as cl:
        for i in range(months):
            y, mth = today.year, today.month - i
            while mth <= 0: y -= 1; mth += 12
            r = await cl.get(url, params={"response": "json", "date": f"{y}{mth:02d}01", "stockNo": symbol})
            j = r.json()
            rows = []
            for d in j.get("data", []):
                # 民國日期 "115/10/24" → 2026-10-24
                yy, mm, dd = d[0].split("/")
                rows.append((f"{int(yy)+1911}-{mm}-{dd}", _f(d[3]), _f(d[4]), _f(d[5]), _f(d[6]), int(_f(d[1]) or 0)))
            if rows:
                mem.upsert_daily(symbol, rows)
            await asyncio.sleep(0.5)  # 禮貌性間隔


def indicators(symbol: str, want: list[str] | None = None) -> dict:
    rows = mem.daily(symbol)
    if len(rows) < 30:
        raise LookupError(f"{symbol} 日線資料不足（{len(rows)} 根），請先執行盤後掃描")
    closes = [r[4] for r in rows]; vols = [r[5] for r in rows]; highs = [r[2] for r in rows]
    out = {}
    ma = lambda n: round(sum(closes[-n:]) / n, 2) if len(closes) >= n else None
    out["ma5"], out["ma20"], out["ma60"] = ma(5), ma(20), ma(60)
    out["vol_ratio"] = round(vols[-1] / (sum(vols[-21:-1]) / 20), 2) if len(vols) > 21 else None
    out["high_20d"] = max(highs[-21:-1]) if len(highs) > 21 else None
    # RSI14
    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    ag, al = sum(gains[-14:]) / 14, sum(losses[-14:]) / 14
    out["rsi14"] = round(100 - 100 / (1 + ag / al), 1) if al else 100.0
    # MACD(12,26,9) hist 最近兩根
    def ema(seq, n):
        k = 2 / (n + 1); e = seq[0]; res = []
        for v in seq: e = v * k + e * (1 - k); res.append(e)
        return res
    e12, e26 = ema(closes, 12), ema(closes, 26)
    dif = [a - b for a, b in zip(e12, e26)]
    dea = ema(dif, 9)
    hist = [a - b for a, b in zip(dif, dea)]
    out["macd_hist"] = round(hist[-1], 3); out["macd_hist_prev"] = round(hist[-2], 3)
    out["close"] = closes[-1]; out["volume"] = vols[-1]
    return {k: v for k, v in out.items() if not want or k in want or k in ("close",)}


def score(symbol: str) -> tuple[int, list[str]]:
    ind = indicators(symbol)
    s, why = 0, []
    if ind["ma20"] and ind["ma60"] and ind["close"] > ind["ma20"] > ind["ma60"]:
        s += 30; why.append("站上均線")
    if ind["vol_ratio"] and ind["vol_ratio"] > 1.5:
        s += 25; why.append(f"量增 {ind['vol_ratio']} 倍")
    if 40 < ind["rsi14"] < 70:
        s += 20
    if ind["macd_hist_prev"] <= 0 < ind["macd_hist"]:
        s += 25; why.append("MACD 翻正")
    return s, why


async def screen(top_n: int | None = None, min_score: int | None = None) -> dict:
    top_n = top_n or MARKET["top_n"]; min_score = min_score or MARKET["min_score"]
    results = []
    for sym in MARKET["watchlist"]:
        try:
            await fetch_daily(sym, months=3)
            sc, why = score(sym)
            if sc >= min_score:
                results.append({"symbol": sym, "name": _names.get(sym, sym), "score": sc, "why": "＋".join(why) or "綜合評分"})
        except Exception as e:
            log.warning("screen %s: %s", sym, e)
    results.sort(key=lambda r: -r["score"])
    results = results[:top_n]
    card = render_card(results)
    return {"results": results, "generated_at": datetime.now().isoformat(timespec="minutes"), "card_path": card}


def render_card(results: list[dict]) -> str | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    d = CFG["paths"]["cards_dir"]
    if not os.path.isdir(d):
        log.warning("cards_dir %s 不存在（Samba 未掛載？）", d); return None
    img = Image.new("RGB", (1200, 400), "#0f172a"); dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 36); small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 26)
    except Exception:
        font = small = ImageFont.load_default()
    dr.text((40, 30), f"盤後掃描 {date.today():%m/%d}", fill="white", font=font)
    if not results:
        dr.text((40, 120), "今天沒有符合條件的", fill="#94a3b8", font=font)
    for i, r in enumerate(results):
        y = 110 + i * 80
        col = "#22c55e" if r["score"] >= 75 else "#eab308"
        dr.rectangle((40, y, 40 + r["score"] * 10, y + 50), fill=col)
        dr.text((60, y + 8), f"{r['symbol']} {r['name']}  {r['score']} 分  {r['why']}", fill="black", font=small)
    dr.text((40, 350), MARKET["disclaimer"], fill="#94a3b8", font=small)
    name = f"screen_{date.today():%m%d}.png"
    img.save(os.path.join(d, name)); img.save(os.path.join(d, "latest.png"))
    return f"{CFG['paths']['cards_url_prefix']}/{name}"


async def check_alerts() -> list[dict]:
    """盤中告警（由 HA 每 5 分鐘呼叫 /v1/alerts/check）。回傳觸發清單。"""
    day = str(date.today()); fired = []
    holdings = mem.holdings()
    for sym in set(MARKET["watchlist"]) | set(holdings):
        if mem.alert_count_today(day, sym) >= MARKET["alerts"]["max_per_symbol_per_day"]:
            continue
        try:
            q = await quote(sym); ind = indicators(sym, ["high_20d"])
        except Exception as e:
            log.info("alert skip %s: %s", sym, e); continue
        for rule in MARKET["alerts"]["rules"]:
            hit = False
            if rule["name"] == "breakout" and ind.get("high_20d") and q["price"] > ind["high_20d"]:
                hit = True; msg = f"📈 {sym} {q['name']} 突破 20 日高 {ind['high_20d']}，現價 {q['price']}"
            if rule["name"] == "stop_loss" and sym in holdings and q["price"] < holdings[sym]["cost"] * 0.92:
                hit = True; msg = f"⚠️ {sym} {q['name']} 跌破停損 {round(holdings[sym]['cost']*0.92,1)}（成本 {holdings[sym]['cost']:.1f}，現價 {q['price']}）"
            if hit:
                mem.log_alert(day, sym, rule["name"])
                fired.append({"symbol": sym, "name": rule["name"], "light": rule.get("light"), "push": rule.get("push", True), "tts": rule.get("tts", False), "priority": rule.get("priority", "normal"), "message": msg})
    return fired


def speak_quote(q: dict, ind: dict | None) -> str:
    parts = [f"{q['name']} {q['price']} 元，{'漲' if q['change_pct']>=0 else '跌'} {abs(q['change_pct'])}%。"]
    if ind:
        if ind.get("ma20"): parts.append(("站上" if q["price"] > ind["ma20"] else "跌破") + " 20 日均，")
        if ind.get("vol_ratio"): parts.append(f"量能是均量的 {ind['vol_ratio']} 倍，")
        if ind.get("rsi14"): parts.append(f"RSI {int(ind['rsi14'])}。")
    parts.append(MARKET["disclaimer"].replace("以上為資料整理，", ""))
    return "".join(parts)
