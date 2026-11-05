"""青鳥 Magpie Admin — 設定模型、儲存與「套用」（把設定渲染成各服務的設定檔）"""
from __future__ import annotations
import base64, hashlib, os, secrets, shutil, time
from pathlib import Path
import yaml

PROJECT = Path(os.environ.get("MAGPIE_PROJECT", "/project"))
DATA = PROJECT / "data" / "admin"
SETTINGS_FILE = DATA / "settings.yaml"
CONFIG = PROJECT / "config"
PROVISION = PROJECT / "provision"

# ---- 設定結構：section → fields（label / type / default / help / secret）----
SCHEMA: list[dict] = [
    {"id": "site", "title": "網站與節點", "fields": [
        {"k": "name", "label": "系統名稱", "type": "text", "default": "青鳥 · Allen & Ann"},
        {"k": "timezone", "label": "時區", "type": "text", "default": "Asia/Taipei"},
        {"k": "role", "label": "節點角色", "type": "select", "options": ["primary", "standby"], "default": "primary", "help": "primary 跑全套；standby 只跑後台與 MQTT，等待接手"},
        {"k": "lan_ip", "label": "本機區網 IP", "type": "text", "default": "", "help": "給 Hermes、Companion、副節點回連用，例 192.168.0.11"},
        {"k": "network_mode", "label": "Home Assistant 網路模式", "type": "select", "options": ["bridge", "host"], "default": "bridge", "help": "Linux 用 host（install.sh 已套用 docker-compose.host.yml）；Docker Desktop 用 bridge"},
        {"k": "admin_password", "label": "後台密碼", "type": "password", "default": "", "secret": True, "help": "留空＝沿用 .env 的 ADMIN_PASSWORD"},
    ]},
    {"id": "ha", "title": "Home Assistant", "fields": [
        {"k": "token", "label": "長效存取權杖（給 Hermes 與後台）", "type": "password", "default": "", "secret": True, "help": "HA → 個人 → 安全性 → 長效存取權杖"},
        {"k": "external_url", "label": "外部網址", "type": "text", "default": "", "help": "例 https://AllenandAnn.duckdns.org"},
        {"k": "backup_password", "label": "備份加密密碼", "type": "password", "default": "", "secret": True, "help": "兩個節點必須相同；留空自動產生"},
        {"k": "install_packages", "label": "套用時安裝 35 情境 packages", "type": "bool", "default": True},
    ]},
    {"id": "mqtt", "title": "MQTT", "fields": [
        {"k": "user", "label": "帳號", "type": "text", "default": "mqtt"},
        {"k": "password", "label": "密碼", "type": "password", "default": "", "secret": True, "help": "留空自動產生；套用時寫入 Mosquitto、Zigbee2MQTT、HA secrets"},
    ]},
    {"id": "zigbee", "title": "Zigbee", "fields": [
        {"k": "mode", "label": "協調器連線", "type": "select", "options": ["tcp", "serial"], "default": "tcp", "help": "tcp＝SLZB-06 網路協調器（跨平台、熱備必要）；serial 僅 Linux"},
        {"k": "tcp_host", "label": "SLZB-06 IP", "type": "text", "default": "192.168.0.25"},
        {"k": "tcp_port", "label": "SLZB-06 埠", "type": "int", "default": 6638},
        {"k": "serial_port", "label": "USB 序列埠（serial 模式）", "type": "text", "default": "/dev/ttyUSB0"},
        {"k": "adapter", "label": "晶片驅動", "type": "select", "options": ["ember", "zstack", "deconz"], "default": "ember"},
        {"k": "channel", "label": "頻道", "type": "int", "default": 15},
    ]},
    {"id": "voice", "title": "語音（OpenClaw）", "fields": [
        {"k": "whisper_model", "label": "Whisper 模型", "type": "select", "options": ["tiny", "base", "small", "medium"], "default": "small"},
        {"k": "piper_voice", "label": "Piper 聲線", "type": "text", "default": "zh_CN-huayan-medium"},
        {"k": "ollama_source", "label": "Ollama 來源", "type": "select", "options": ["container", "host"], "default": "container", "help": "macOS 選 host（主機原生 Ollama 有 Metal 加速）"},
        {"k": "ollama_url", "label": "主機 Ollama 網址（host 模式）", "type": "text", "default": "http://host.docker.internal:11434"},
        {"k": "ollama_model", "label": "LLM 模型", "type": "text", "default": "llama3:8b"},
        {"k": "llm_provider", "label": "Hermes 大腦", "type": "select", "options": ["ollama", "grok"], "default": "ollama", "help": "⚠️ 原則 1：預設 ollama（全本地）。grok＝xAI 雲端，屬選配且預設關閉；開啟後每句指令的文字上下文會送到 x.ai（不送語音、錄音、在家狀態、用電），失敗自動退回本地"},
        {"k": "grok_api_key", "label": "Grok（xAI）API Key", "type": "password", "default": "", "secret": True, "help": "https://console.x.ai 建立；存於 .env 的 GROK_API_KEY"},
        {"k": "grok_model", "label": "Grok 模型", "type": "text", "default": "grok-4-fast"},
        {"k": "grok_fallback", "label": "Grok 失敗時退回本地 Ollama", "type": "bool", "default": True},
    ]},
    {"id": "hermes", "title": "Hermes 管家", "fields": [
        {"k": "autonomy", "label": "自主程度", "type": "select", "options": ["confirm_all", "confirm_write_only"], "default": "confirm_all"},
        {"k": "quiet_start", "label": "深夜時段開始", "type": "text", "default": "23:00"},
        {"k": "quiet_end", "label": "深夜時段結束", "type": "text", "default": "07:00"},
        {"k": "watchlist", "label": "自選股（逗號分隔）", "type": "text", "default": "2330,2454,3037,2317,2603"},
        {"k": "stop_loss_pct", "label": "停損告警（跌破成本 %）", "type": "int", "default": 8},
    ]},
    {"id": "energy", "title": "節能管家（憲章 VI）", "fields": [
        {"k": "enabled", "label": "啟用 Hermes 節能守門", "type": "bool", "default": True, "help": "所有空調/燈光/家電計畫先經 energy.clamp 只收緊不放寬；關掉僅在除錯時"},
        {"k": "default_mode", "label": "預設節能模式", "type": "select", "options": ["eco", "normal", "comfort"], "default": "eco"},
        {"k": "ac_min_cool", "label": "eco 冷氣最低溫（°C）", "type": "int", "default": 27},
        {"k": "light_max_pct", "label": "eco 燈光亮度上限（%）", "type": "int", "default": 70},
        {"k": "idle_off_min", "label": "無人幾分鐘關空調/燈", "type": "int", "default": 20},
        {"k": "carbon_factor", "label": "電力排碳係數 kgCO2e/kWh", "type": "text", "default": "0.474", "help": "台電每年公告；2024 年 0.474"},
        {"k": "baseline_kwh_day", "label": "基準日用電（kWh）", "type": "text", "default": "12", "help": "台電帳單度數 ÷ 天數"},
        {"k": "report_time", "label": "每日用電報告時間", "type": "text", "default": "21:30"},
    ]},
    {"id": "notify", "title": "通知對象", "fields": [
        {"k": "allen", "label": "Allen 的 notify 服務", "type": "text", "default": "notify.mobile_app_allen_iphone"},
        {"k": "ann", "label": "Ann 的 notify 服務", "type": "text", "default": "notify.mobile_app_ann_iphone"},
    ]},
    {"id": "bots", "title": "LINE / Telegram 機器人", "fields": [
        {"k": "telegram_token", "label": "Telegram Bot Token", "type": "password", "default": "", "secret": True, "help": "向 @BotFather 建立；用 long polling，不需開埠"},
        {"k": "line_channel_secret", "label": "LINE Channel Secret", "type": "password", "default": "", "secret": True},
        {"k": "line_access_token", "label": "LINE Channel Access Token", "type": "password", "default": "", "secret": True, "help": "Messaging API；Webhook URL = <外部 https 網址>/line/webhook（需反向代理到 :8900）"},
        {"k": "members", "label": "家庭成員白名單", "type": "text", "default": "", "help": "格式：名字:平台:ID:角色，逗號分隔。例 allen:telegram:123456789:admin, ann:line:Uxxxxxxxx:member；角色 admin / member / viewer（viewer 只能查詢）。成員第一次傳訊息時機器人會回覆自己的 ID"},
        {"k": "quick", "label": "快捷選單（標籤=指令，逗號分隔）", "type": "text", "default": "狀態=/狀態, 睡眠=/情境 睡眠 開, 影音=/情境 影音 開, 離家=/情境 離家, 客廳燈開=/燈 客廳 開, 客廳燈關=/燈 客廳 關, 主臥26度=/冷氣 主臥 26"},
        {"k": "notify_via_bot", "label": "HA 推播同時送到機器人", "type": "bool", "default": True},
    ]},
    {"id": "remote", "title": "遠端存取", "fields": [
        {"k": "duckdns_domain", "label": "DuckDNS 網域", "type": "text", "default": ""},
        {"k": "duckdns_token", "label": "DuckDNS token", "type": "password", "default": "", "secret": True},
        {"k": "tailscale_note", "label": "Tailscale", "type": "note", "default": "", "help": "在主機層安裝 Tailscale（brew / apt），兩個節點各自加入同一帳號；後台不代管"},
    ]},
    {"id": "cluster", "title": "熱備（雙節點）", "fields": [
        {"k": "peer_url", "label": "另一節點後台網址", "type": "text", "default": "", "help": "例 http://192.168.0.12:9000"},
        {"k": "lb_vip", "label": "負載均衡虛擬 IP（VIP）", "type": "text", "default": "", "help": "例 192.168.0.100；填了之後 Hermes、Whisper/Piper 的 HA 端串接都走 VIP（bluemagpie/lb，SOP 11 章）"},
        {"k": "shared_secret", "label": "節點共用密鑰", "type": "password", "default": "", "secret": True, "help": "兩邊相同；留空自動產生，請複製到另一節點"},
        {"k": "hourly_backup", "label": "每小時備份並推送", "type": "bool", "default": True},
        {"k": "keep", "label": "保留份數", "type": "int", "default": 30},
        {"k": "auto_promote", "label": "副節點失聯 5 分鐘自動接手", "type": "bool", "default": True},
    ]},
]


def defaults() -> dict:
    return {s["id"]: {f["k"]: f["default"] for f in s["fields"]} for s in SCHEMA}


def load() -> dict:
    d = defaults()
    if SETTINGS_FILE.exists():
        cur = yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8")) or {}
        for sec, vals in cur.items():
            if sec in d and isinstance(vals, dict):
                d[sec].update(vals)
    return d


def save(d: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def masked(d: dict) -> dict:
    """回前端用：secret 欄位以 ••••（有值）或空字串表示"""
    out = {}
    for s in SCHEMA:
        out[s["id"]] = {}
        for f in s["fields"]:
            v = d[s["id"]].get(f["k"], f["default"])
            out[s["id"]][f["k"]] = ("••••••••" if v else "") if f.get("secret") else v
    return out


def merge_from_client(cur: dict, incoming: dict) -> dict:
    """前端送回的值：secret 欄位若是遮罩就保留原值"""
    for s in SCHEMA:
        for f in s["fields"]:
            if s["id"] in incoming and f["k"] in incoming[s["id"]]:
                v = incoming[s["id"]][f["k"]]
                if f.get("secret") and v == "••••••••":
                    continue
                if f["type"] == "int":
                    try: v = int(v)
                    except (TypeError, ValueError): v = f["default"]
                if f["type"] == "bool":
                    v = bool(v) if not isinstance(v, str) else v.lower() in ("1", "true", "on", "yes")
                cur[s["id"]][f["k"]] = v
    return cur


# ---- Mosquitto 密碼雜湊（$7$ PBKDF2-SHA512，mosquitto 2.x 格式）----
def mosquitto_hash(password: str, iterations: int = 101) -> str:
    salt = secrets.token_bytes(12)
    dk = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, iterations)
    return f"$7${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _ensure_secrets(d: dict) -> list[str]:
    """空的密鑰自動產生；回傳有產生哪些"""
    gen = []
    if not d["mqtt"]["password"]:
        d["mqtt"]["password"] = secrets.token_urlsafe(16); gen.append("mqtt.password")
    if not d["ha"]["backup_password"]:
        d["ha"]["backup_password"] = secrets.token_urlsafe(20); gen.append("ha.backup_password")
    if not d["cluster"]["shared_secret"]:
        d["cluster"]["shared_secret"] = secrets.token_urlsafe(24); gen.append("cluster.shared_secret")
    return gen


# ---- 套用：渲染各服務設定檔 ----
def apply(d: dict) -> dict:
    gen = _ensure_secrets(d)
    save(d)
    changed = {"mosquitto": [], "zigbee2mqtt": [], "hermes": [], "bot": [], "homeassistant": [], "env": []}
    role = d["site"]["role"]
    ha_host = "host.docker.internal" if d["site"]["network_mode"] == "host" else "homeassistant"
    ha_url_internal = f"http://{ha_host}:8123"
    mqtt_host_for_ha = "host.docker.internal" if d["site"]["network_mode"] == "host" else "mosquitto"

    # Mosquitto
    (CONFIG / "mosquitto").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROVISION / "mosquitto" / "mosquitto.conf", CONFIG / "mosquitto" / "mosquitto.conf")
    (CONFIG / "mosquitto" / "passwd").write_text(f"{d['mqtt']['user']}:{mosquitto_hash(d['mqtt']['password'])}\n", encoding="utf-8")
    changed["mosquitto"] += ["mosquitto.conf", "passwd"]

    # Zigbee2MQTT（保留既有 network_key 等 advanced 設定）
    z2m_dir = CONFIG / "zigbee2mqtt"; z2m_dir.mkdir(parents=True, exist_ok=True)
    z2m_file = z2m_dir / "configuration.yaml"
    old = yaml.safe_load(z2m_file.read_text(encoding="utf-8")) if z2m_file.exists() else {}
    adv = (old or {}).get("advanced", {}) or {}
    z = d["zigbee"]
    z2m = {
        "homeassistant": {"enabled": True},
        "frontend": {"enabled": True, "port": 8080},
        "permit_join": False,
        "mqtt": {"base_topic": "zigbee2mqtt", "server": "mqtt://mosquitto:1883", "user": d["mqtt"]["user"], "password": d["mqtt"]["password"]},
        "serial": {"port": f"tcp://{z['tcp_host']}:{z['tcp_port']}" if z["mode"] == "tcp" else z["serial_port"], "adapter": z["adapter"], "baudrate": 115200},
        "advanced": {"channel": z["channel"], "network_key": adv.get("network_key", "GENERATE"), "pan_id": adv.get("pan_id", "GENERATE"), "ext_pan_id": adv.get("ext_pan_id", "GENERATE"), "log_level": "info"},
        "devices": (old or {}).get("devices", {}), "groups": (old or {}).get("groups", {}),
    }
    if z2m.get("devices") == {}: z2m.pop("devices")
    if z2m.get("groups") == {}: z2m.pop("groups")
    z2m_file.write_text(yaml.safe_dump(z2m, allow_unicode=True, sort_keys=False), encoding="utf-8")
    changed["zigbee2mqtt"].append("configuration.yaml")

    # Hermes
    hdir = CONFIG / "hermes"; hdir.mkdir(parents=True, exist_ok=True)
    for name in ("policy.yaml", "market.yaml"):
        if not (hdir / name).exists():
            shutil.copy(PROVISION / "hermes" / name, hdir / name)
    if not (hdir / "tools").exists():
        shutil.copytree(PROVISION / "hermes" / "tools", hdir / "tools")
    hcfg = yaml.safe_load((PROVISION / "hermes" / "hermes.yaml").read_text(encoding="utf-8"))
    urls = [ha_url_internal]
    if d["cluster"].get("lb_vip"):
        urls.insert(0, f"http://{d['cluster']['lb_vip']}:8123")   # 走 VIP：LB 自動導向活著的 HA
    peer = d["cluster"]["peer_url"]
    if peer:
        urls.append(peer.replace(":9000", ":8123"))
    hcfg["ha"]["urls"] = urls
    v = d["voice"]
    hcfg["ollama"]["url"] = v["ollama_url"] if v["ollama_source"] == "host" else "http://ollama:11434"
    hcfg["ollama"]["model"] = v["ollama_model"]
    hcfg["llm"] = {"provider": v["llm_provider"], "fallback": ("ollama" if v["grok_fallback"] else None) if v["llm_provider"] == "grok" else None}
    hcfg["grok"] = {"base_url": "https://api.x.ai/v1", "model": v["grok_model"], "api_key_env": "HERMES_GROK_API_KEY", "temperature": 0.1, "timeout_s": 15, "max_tokens": 600}
    hcfg["notify"] = {"allen": d["notify"]["allen"], "ann": d["notify"]["ann"], "both": "notify.both"}
    hcfg["paths"] = {"db": "/data/hermes.db", "tx_log": "/data/logs/hermes.tx.log", "cards_dir": "/cards", "cards_url_prefix": "/local/hermes"}
    hcfg["energy"] = {"enabled": bool(d["energy"]["enabled"])}
    (hdir / "hermes.yaml").write_text(yaml.safe_dump(hcfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # 節能管家參數：provision/hermes/energy.yaml 為範本，後台欄位覆蓋 eco 與係數
    en = yaml.safe_load((PROVISION / "hermes" / "energy.yaml").read_text(encoding="utf-8"))
    e = d["energy"]
    en["enabled"] = bool(e["enabled"])
    en["carbon_kg_per_kwh"] = float(e["carbon_factor"] or 0.474)
    en["modes"]["eco"]["ac_min_cool"] = int(e["ac_min_cool"]); en["modes"]["eco"]["peak_ac_min_cool"] = int(e["ac_min_cool"]) + 1
    en["modes"]["eco"]["light_max_pct"] = int(e["light_max_pct"]); en["modes"]["eco"]["idle_off_min"] = int(e["idle_off_min"])
    en["report"]["daily_at"] = e["report_time"]
    (hdir / "energy.yaml").write_text(yaml.safe_dump(en, allow_unicode=True, sort_keys=False), encoding="utf-8")
    changed["hermes"].append("energy.yaml")
    pol = yaml.safe_load((hdir / "policy.yaml").read_text(encoding="utf-8"))
    pol["autonomy"] = d["hermes"]["autonomy"]
    pol["confirm"]["quiet_hours"]["window"] = [d["hermes"]["quiet_start"], d["hermes"]["quiet_end"]]
    (hdir / "policy.yaml").write_text(yaml.safe_dump(pol, allow_unicode=True, sort_keys=False), encoding="utf-8")
    mk = yaml.safe_load((hdir / "market.yaml").read_text(encoding="utf-8"))
    mk["watchlist"] = [s.strip() for s in d["hermes"]["watchlist"].split(",") if s.strip()]
    for r in mk["alerts"]["rules"]:
        if r["name"] == "stop_loss":
            r["when"] = f"price < holding.cost * {1 - d['hermes']['stop_loss_pct'] / 100:.2f}"
    (hdir / "market.yaml").write_text(yaml.safe_dump(mk, allow_unicode=True, sort_keys=False), encoding="utf-8")
    changed["hermes"] += ["hermes.yaml", "policy.yaml", "market.yaml"]

    # Bot（LINE / Telegram）
    bdir = CONFIG / "bot"; bdir.mkdir(parents=True, exist_ok=True)
    members = []
    for item in d["bots"]["members"].split(","):
        parts = [x.strip() for x in item.split(":")]
        if len(parts) >= 3:
            members.append({"name": parts[0], "platform": parts[1].lower(), "id": parts[2], "role": parts[3] if len(parts) > 3 else "member"})
    quick = []
    for item in d["bots"]["quick"].split(","):
        if "=" in item:
            l, t = item.split("=", 1); quick.append([l.strip(), t.strip()])
    bot_cfg = {
        "ha_url": ha_url_internal, "ha_token": d["ha"]["token"],
        "hermes_url": "http://host.docker.internal:8800" if d["site"]["network_mode"] == "host" else "http://hermes:8800",
        "shared_secret": d["cluster"]["shared_secret"],
        "telegram": {"bot_token": d["bots"]["telegram_token"]},
        "line": {"channel_secret": d["bots"]["line_channel_secret"], "access_token": d["bots"]["line_access_token"]},
        "members": members, "quick": quick,
        "areas": {k: {kk: vv for kk, vv in v.items() if kk in ("light", "cover", "climate")} for k, v in hcfg.get("areas", {}).items()},
    }
    (bdir / "bot.yaml").write_text(yaml.safe_dump(bot_cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    changed["bot"] = ["bot.yaml"]

    # Home Assistant：configuration.yaml（只在不存在時建立）、secrets.yaml、packages、magpie 專用片段
    hac = CONFIG / "homeassistant"; (hac / "packages").mkdir(parents=True, exist_ok=True); (hac / "www" / "hermes").mkdir(parents=True, exist_ok=True)
    lan = d["site"]["lan_ip"] or "127.0.0.1"
    hermes_host = "host.docker.internal" if d["site"]["network_mode"] == "host" else "hermes"
    admin_host = "host.docker.internal" if d["site"]["network_mode"] == "host" else "admin"
    whisper_host = "host.docker.internal" if d["site"]["network_mode"] == "host" else "whisper"
    secrets_yaml = {
        "mqtt_password": d["mqtt"]["password"], "mqtt_user": d["mqtt"]["user"],
        "backup_password": d["ha"]["backup_password"],
        "openclaw_webhook_id": "openclaw_voice_" + secrets.token_hex(16), "white_noise_webhook_id": "white_noise_" + secrets.token_hex(16),
        "duckdns_token": d["remote"]["duckdns_token"], "magpie_shared_secret": d["cluster"]["shared_secret"],
        "twilio_sid": "", "twilio_token": "", "twilio_from": "", "sos_contact_1": "", "sos_contact_2": "",
    }
    sf = hac / "secrets.yaml"
    if sf.exists():  # 保留使用者已填的值（webhook id、twilio…），只覆蓋由後台管理的鍵
        old_s = yaml.safe_load(sf.read_text(encoding="utf-8")) or {}
        for k in ("openclaw_webhook_id", "white_noise_webhook_id", "twilio_sid", "twilio_token", "twilio_from", "sos_contact_1", "sos_contact_2"):
            if old_s.get(k): secrets_yaml[k] = old_s[k]
    sf.write_text(yaml.safe_dump(secrets_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (hac / "magpie.yaml").write_text(f"""# 由青鳥後台產生，請勿手改（每次「套用」會覆蓋）
rest_command:
  hermes_command:
    url: http://{hermes_host}:8800/v1/command
    method: POST
    content_type: application/json
    payload: '{{"text": "{{{{ text }}}}", "speaker": "{{{{ speaker }}}}", "output": "{{{{ output | default(''living_homepod'') }}}}", "say": {{{{ say | default(true) | lower }}}}}}'
    timeout: 20
  hermes_screen:
    url: http://{hermes_host}:8800/v1/jobs/screen
    method: POST
    content_type: application/json
    payload: '{{}}'
    timeout: 90
  hermes_alerts:
    url: http://{hermes_host}:8800/v1/alerts/check
    method: POST
    timeout: 30
  magpie_backup:
    url: http://{admin_host}:9000/api/backup/run
    method: POST
    headers: {{ "X-Magpie-Secret": "{d['cluster']['shared_secret']}" }}
    timeout: 120
  magpie_bot_notify:
    url: http://{'host.docker.internal' if d['site']['network_mode'] == 'host' else 'bot'}:8900/v1/notify
    method: POST
    content_type: application/json
    headers: {{ "X-Magpie-Secret": "{d['cluster']['shared_secret']}" }}
    payload: '{{"to": "{{{{ to | default(''all'') }}}}", "message": "{{{{ message }}}}"}}'
    timeout: 15
notify:
  - name: both
    platform: group
    services:
      - service: {d['notify']['allen'].split('.', 1)[-1]}
      - service: {d['notify']['ann'].split('.', 1)[-1]}
binary_sensor:
  - platform: ping
    name: wan_ping
    host: 1.1.1.1
    count: 2
    scan_interval: 30
proximity:
  home_allen: {{ zone: home, devices: [device_tracker.allen_iphone], tolerance: 50, unit_of_measurement: m }}
  home_ann: {{ zone: home, devices: [device_tracker.ann_iphone], tolerance: 50, unit_of_measurement: m }}
""", encoding="utf-8")
    cf = hac / "configuration.yaml"
    if not cf.exists():
        cf.write_text(f"""# 青鳥 BlueMagpie — Home Assistant 基本設定（可自行增修；magpie.yaml 由後台維護）
default_config:
homeassistant:
  name: "{d['site']['name']}"
  time_zone: {d['site']['timezone']}
  packages: !include_dir_named packages
  customize: !include customize.yaml
http:
  use_x_forwarded_for: true
  trusted_proxies: [172.16.0.0/12, 127.0.0.1]
logger:
  default: warning
magpie: !include magpie.yaml
""".replace("magpie: !include magpie.yaml", "# magpie.yaml 內容以 packages 方式載入"), encoding="utf-8")
        (hac / "customize.yaml").write_text("", encoding="utf-8")
    # magpie.yaml 以 package 載入（避免與使用者的 configuration.yaml 衝突）
    shutil.copy(hac / "magpie.yaml", hac / "packages" / "s00_magpie.yaml")
    (hac / "magpie.yaml").unlink()
    if d["ha"]["install_packages"]:
        for p in (PROVISION / "homeassistant" / "packages").glob("*.yaml"):
            shutil.copy(p, hac / "packages" / p.name)
        # s00_energy.yaml：把後台的節能預設寫進 helper 的 initial（憲章 VI）
        ep = hac / "packages" / "s00_energy.yaml"
        if ep.exists():
            import re as _re
            e = d["energy"]; txt = ep.read_text(encoding="utf-8")
            txt = _re.sub(r"(options: \[eco, normal, comfort\]\n    initial: )\w+", r"\g<1>" + e["default_mode"], txt)
            txt = _re.sub(r"(energy_baseline_kwh_day:(?:\n    .*)*?\n    initial: )[\d.]+", r"\g<1>" + str(float(e["baseline_kwh_day"] or 12)), txt)
            txt = _re.sub(r"(energy_carbon_factor:(?:\n    .*)*?\n    initial: )[\d.]+", r"\g<1>" + str(float(e["carbon_factor"] or 0.474)), txt)
            txt = txt.replace('at: "21:30:00"', f'at: "{e["report_time"]}:00"')
            ep.write_text(txt, encoding="utf-8")
    changed["homeassistant"] += ["secrets.yaml", "packages/s00_magpie.yaml"] + (["packages/*"] if d["ha"]["install_packages"] else [])

    # .env（容器層變數：埠、模型、token、profiles）
    env_path = PROJECT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, val = line.partition("="); env[k.strip()] = val.split("#")[0].strip()
    env.update({"TZ": d["site"]["timezone"], "HA_TOKEN": d["ha"]["token"], "WHISPER_MODEL": v["whisper_model"], "PIPER_VOICE": v["piper_voice"], "GROK_API_KEY": v["grok_api_key"]})
    if d["site"]["admin_password"]:
        env["ADMIN_PASSWORD"] = d["site"]["admin_password"]
    profiles = ["standby"] if role == "standby" else ["primary"] + (["ollama"] if v["ollama_source"] == "container" else [])
    env["COMPOSE_PROFILES"] = ",".join(profiles)
    env_path.write_text("\n".join(f"{k}={val}" for k, val in env.items()) + "\n", encoding="utf-8")
    changed["env"].append(".env")

    (DATA / "applied_at").write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    return {"changed": changed, "generated_secrets": gen, "role": role, "profiles": profiles}
