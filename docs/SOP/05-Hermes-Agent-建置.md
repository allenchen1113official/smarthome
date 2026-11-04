# 05 · Hermes Agent 建置

> 目標：Hermes 以 launchd 常駐於 Mac mini `:8800`，成為 HA Assist 的對話代理；任何改變實體狀態的動作先覆誦確認（`autonomy: confirm_all`），深夜改推播；失敗反向回滾；股票模組可用。
> 完成判準：§5.9。
> 程式碼：`docs/SOP/hermes/`（v0.1 骨架，已通過語法與離線功能測試；對應 `design/hermes.html` v0.3 規格）。

## 5.1 Hermes 在管線中的位置與串接方式

```
HA Assist 管線 ── 對話代理 = 「Ollama」整合 ──► http://192.168.0.10:8800  (Hermes 偽裝成 Ollama 端點)
                                                      │
                                   ┌──────────────────┼──────────────────┐
                                   ▼                  ▼                  ▼
                          fast lane（免 LLM）   Ollama :11434      HA REST / WS / MQTT
                          報價、幾度、還在睡嗎   Llama 3 8B → Plan    guard → confirm → dispatch
```

**為什麼偽裝成 Ollama？** HA 內建的 Ollama 整合允許自訂 URL 並且會把對話歷史送過來；Hermes 實作 `/api/tags`、`/api/show`、`/api/chat` 三個端點就能零客製化整合進 Assist，確認對話（「要我…嗎？」→「好」）也自然成為下一輪 Assist 對話。

## 5.2 安裝

```bash
# 1) 複製程式碼到 Mac mini
mkdir -p ~/openclaw && cp -R "<SmartHome>/docs/SOP/hermes" ~/openclaw/hermes
mkdir -p ~/openclaw/hermes/logs

# 2) 相依套件（沿用 04 章的 venv）
source ~/openclaw/venv/bin/activate
pip install -r ~/openclaw/hermes/requirements.txt

# 3) HA 長效 token：HA 右下角個人 → 安全性 → 長效存取權杖 → 建立「hermes」→ 複製
export HERMES_HA_TOKEN='eyJhbGciOi...'

# 4) 手動試跑
cd ~/openclaw/hermes
uvicorn hermes.app:app --host 0.0.0.0 --port 8800
# 另開終端機
curl -s localhost:8800/v1/health | jq          # ok: true, world_entities > 0（WS 已拉到全部狀態）
curl -s localhost:8800/api/tags | jq '.models[0].name'   # hermes:latest
```

## 5.3 設定檔逐一檢查

| 檔案 | 要改的地方 |
|---|---|
| `config/hermes.yaml` | `ha.urls`（主 `.11` → 副 `.12`，07 章熱備）、`areas.*` 的 entity_id 要與 03 章命名一致、`paths.cards_dir` 指向已掛載的 `/Volumes/config/www/hermes` |
| `config/policy.yaml` | 預設即設計值：`confirm_all`、12 秒逾時、23:00–07:00 推播、`never` 含 `broker.place_order` |
| `config/market.yaml` | `watchlist` 填自選股；`alerts.rules` 停損 8%（`cost * 0.92`） |
| `config/tools/*.yaml` | 工具 schema，一般不用改。新增工具 = 加一段 YAML + 在 `tools.py` 加一個分支 |
| `com.allenann.hermes.plist` | 貼入 token，路徑改成實際使用者名稱 |

## 5.4 HA 端把對話代理切到 Hermes

1. 設定 → 整合 → **Ollama** → 新增第二個項目：URL `http://192.168.0.10:8800`，模型選 `hermes:latest`（Hermes 的 `/api/tags` 提供）。
2. 該項目的選項：「控制 Home Assistant」選 **不控制**（由 Hermes 決定與確認，不要讓 HA 自己執行）。對話代理名稱改 `Hermes`。
3. 設定 → 語音助理 → `OpenClaw` → 對話代理改 **Hermes**。
4. Assist 打字「客廳燈調到百分之五十」→ 回覆「要我把客廳燈調到50%嗎？」→ 打「好」→ 燈變、回覆「好了」。

## 5.5 HA 端輔助腳本（`packages/s00_common.yaml` 與 `s00_voice.yaml`）

Hermes 不直接碰設備；下列 HA 腳本是它的「手」：

| HA script | 由哪個工具呼叫 | 功能 |
|---|---|---|
| `script.ac_set` | `climate.set` | 參數 `room/temperature/hvac_mode/fan_mode`；Comfort Cloud `unavailable` 時改走 SmartIR |
| `script.say` | `media.say` | 參數 `message/target/volume`；深夜音量 20%，sleep_mode 時主臥改推播 |
| `script.vacuum_rooms` | `vacuum.control spot` | 依房間名呼叫 Roborock 分區清掃 |
| `script.emergency_sos` | `emergency.sos` | 簡訊 + 全屋紅光 + HomePod 最大音量 |
| `script.hermes_alert` | `/v1/alerts/check` | 參數 `message/light(pulse_red/pulse_blue/none)/tts/priority`；深夜只推播 |
| `rest_command.hermes_command` | HA 自動化 → Hermes | `POST /v1/command`（Siri 捷徑 webhook 路徑） |
| `rest_command.hermes_screen` | 情境 32 | `POST /v1/jobs/screen` |
| `rest_command.hermes_alerts` | 情境 33 | `POST /v1/alerts/check` |

`configuration.yaml` 需含（snippet 已有）：

```yaml
rest_command:
  hermes_command:
    url: http://192.168.0.10:8800/v1/command
    method: POST
    content_type: application/json
    payload: '{"text": "{{ text }}", "speaker": "{{ speaker }}", "output": "{{ output | default(''living_homepod'') }}", "say": {{ say | default(true) | lower }}}'
    timeout: 20
  hermes_screen:
    url: http://192.168.0.10:8800/v1/jobs/screen
    method: POST
    content_type: application/json
    payload: '{}'
    timeout: 90
  hermes_alerts:
    url: http://192.168.0.10:8800/v1/alerts/check
    method: POST
    timeout: 30
```

## 5.6 launchd 常駐

```bash
sed -i '' "s#把HA長效token貼在這裡#$HERMES_HA_TOKEN#" ~/openclaw/hermes/com.allenann.hermes.plist
cp ~/openclaw/hermes/com.allenann.hermes.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.allenann.hermes.plist
sleep 3; curl -s localhost:8800/v1/health
tail -f ~/openclaw/hermes/logs/hermes.err     # 看 "Hermes v0.1 ready" 與 "WS 已連線"
```

plist 檔案含 token，權限收緊：`chmod 600 ~/Library/LaunchAgents/com.allenann.hermes.plist`。

## 5.7 編排流程對照（設計 → 程式）

| 設計步驟 | 程式位置 | 行為 |
|---|---|---|
| 01 PARSE | `llm.plan()` + `orchestrator.validate_steps()` | JSON 解析；未知工具回「這個我還不會」；enum/範圍錯誤直接回人話 |
| 02 GUARD | `execute_plan()` 開頭 | `device_online`、`write.appliance` 在 sleep_mode / 深夜拒絕、主臥 sleep_mode 跳過燈光、plan 總時 8 s |
| 03 CONFIRM | `handle()` 第 4 步 | `confirm_all`；12 s 逾時取消；深夜改 `notify.push` |
| 04 DISPATCH | `tools.execute()` | 全部經 HA 服務；每步先 `tools.snapshot()` 寫入 `hermes.db/snapshot`（TTL 10 min） |
| 05 RETRY | `execute_plan()` 迴圈 | 指數退避 0.4 / 1.2 / 3.6 s；`cover.set_position` 標 `on_fail: skip` |
| 06 SETTLE | `_rollback()` | 失敗依 tx log 反向 `tools.restore()`；回報人話原因 |
| fast lane | `fast_lane()` | 報價、「幾度」、「還在睡嗎」不經 LLM（~300 ms） |
| 記憶 | `memory.py` | session 6 輪 / 10 min；pref 以 n 與 confidence 累積，< 0.6 不套用 |
| 併發 | `app.py` `_llm_sem` + `_queue_len` | LLM 車道 ×1，佇列 3，滿載回「等我一下」 |

交易記錄：`~/openclaw/hermes/logs/hermes.tx.log`，格式與 `design/hermes.html` 的範例相同：

```
14:23:01.102 plan pln_2f7a PARSED intent=home_arrival steps=['light.activate_scene','climate.set','cover.set_position']
14:23:01.110 confirm → '要我開客廳的 Welcome 場景並把客廳冷氣設 24 度並把客廳窗簾開到 100%嗎？'
14:23:04.630 confirm ← '好'
14:23:04.640 snap s1 ['light.living_all']
14:23:04.812 exec s1 light.activate_scene OK 172ms
...
```

## 5.8 股票模組啟用

```bash
# 先灌日線（第一次需要 1–2 分鐘；之後情境 32 每天 13:30 自動做）
curl -s -X POST localhost:8800/v1/jobs/screen | jq '.results, .card_path'
ls /Volumes/config/www/hermes/        # screen_MMDD.png, latest.png
# 報價
curl -s -X POST localhost:8800/api/chat -H 'content-type: application/json' \
  -d '{"model":"hermes:latest","stream":false,"messages":[{"role":"user","content":"2330 現在怎樣"}]}' | jq -r .message.content
# 模擬單（會先要求確認）
... "幫我模擬買 2330 一張" → "要我模擬買進 2330 1000 股，以現價記錄嗎？" → "好"
curl -s localhost:8800/v1/holdings
```

⚠️ 邊界：`broker.place_order` 在 `policy.never`，`validate_steps()` 第一行就擋；`market.yaml` 的 `broker.enabled: false`。每次播報結尾附免責。

## 5.9 Grok（xAI）雲端大腦接口（選配）

Hermes 的 LLM 層做成可抽換：`llm.provider` 可選 `ollama`（本地，預設）或 `grok`（xAI Grok，OpenAI 相容 `chat/completions`）。

```yaml
# config/hermes.yaml
llm:
  provider: grok          # ollama | grok
  fallback: ollama        # Grok 逾時／金鑰失效／額度用完 → 自動退回本地；null 則不退回
grok:
  base_url: https://api.x.ai/v1
  model: grok-4-fast      # 或 grok-3-mini；以 https://docs.x.ai 當期清單為準
  api_key_env: HERMES_GROK_API_KEY
  timeout_s: 15
  max_tokens: 600
```

```bash
export HERMES_GROK_API_KEY='xai-...'     # launchd plist 的 EnvironmentVariables 再加一組
launchctl kickstart -k gui/$(id -u)/com.allenann.hermes
```

與憲章 I「本地優先」的關係：Grok 是**顯式選用**，預設關閉；開啟後送出的只有 Hermes 組好的文字上下文（指令、家中狀態摘要、偏好），**語音錄音與影像不會離開家**；`net.egress` 白名單加入 `api.x.ai`。適合用在 Mac mini 記憶體吃緊、或想要更強的中文語意理解時；fast lane（報價、幾度、還在睡嗎）與 guard／確認／回滾完全不變，只有「解析成 Plan」這一步換了模型。

| 比較 | Ollama Llama 3 8B（本地） | Grok（雲端） |
|---|---|---|
| 延遲 | ~250 ms 首 token | ~0.8–2 s（含網路） |
| 隱私 | 不出家門 | 文字上下文送 xAI |
| 成本 | 電費 | 依 token 計費 |
| 斷網 | 正常 | 退回 Ollama |
| 中文語意 | 可用，偶爾要重講 | 較強 |

## 5.10 驗證清單

| # | 測試 | 預期 |
|---|---|---|
| 1 | `launchctl list \| grep hermes` | 存在，PID 非 0 |
| 2 | 重開 Mac mini 後 `curl .10:8800/v1/health` | `ok: true` |
| 3 | Assist：「客廳燈調到百分之五十」 | 回「要我把客廳燈調到50%嗎？」 |
| 4 | 接著說「好」 | 燈 50%，回「好了」；tx log 有 `exec s1 light.set OK` |
| 5 | 接著說「再暗一點」→「好」 | 亮度降（指代解析） |
| 6 | 把 `climate.living` 整合停用（模擬離線）→「客廳冷氣 24 度」→「好」 | 回「...沒回應，先不動」；不留半套 |
| 7 | 「Allen 回家了」（情境 29）→「好」→ 中途停用冷氣整合 | 燈先亮再被還原；回「...已把前面的動作還原」 |
| 8 | 開 `input_boolean.sleep_mode` →「啟動掃地機」 | 回「睡眠模式中，不啟動家電」 |
| 9 | 改系統時間到 23:30（或等到深夜）→「客廳燈開」 | 回「深夜時段，我把確認改用推播送到手機了」，手機收到 |
| 10 | 「2330 現在怎樣」 | < 2 秒回報價 + 均線 + 免責 |
| 11 | 「幫我模擬買 2330 一張」→「好」 | `/v1/holdings` 多一筆 |
| 12 | 「幫我真的下單」 | 回「broker.place_order 是永久封鎖的動作」或「這個我還不會」 |
| 13 | 連說 4 句指令 | 第 4 句回「等我一下，前面還有指令在處理」 |
| 14 | `llm.provider: grok` + 拔網路線 →「客廳燈開」 | hermes.err 出現 `fallback → ollama`，仍回覆確認句 |

通過 → 06 章情境 29–35。
