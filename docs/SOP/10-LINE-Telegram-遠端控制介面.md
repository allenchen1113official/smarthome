# 10 · LINE / Telegram 遠端控制介面規劃

> 目標：家庭成員在外面用 LINE 或 Telegram 就能控制個別裝置、執行情境、查詢家裡現況；指令與語音走同一套 Hermes 政策（覆誦確認、深夜限制、回滾），不另開一條沒有守門的路。
> 實作：`bluemagpie/bot/`（容器 `magpie-bot` :8900，一支程式同時服務兩個平台）；後台「LINE / Telegram 機器人」頁設定。

## 10.1 為什麼要兩個平台、怎麼分工

| | LINE | Telegram |
|---|---|---|
| 家人習慣 | 台灣幾乎人人有，Ann 不用裝新 App | Allen 技術向、群組機器人成熟 |
| 接收方式 | **Webhook**：LINE 伺服器主動 POST 到家裡，需要公開 https 網址 | **Long polling**：機器人自己向 Telegram 拉訊息，**不需開埠、不需網域** |
| 互動元件 | Quick Reply（最多 13 顆）、Rich Menu（固定底部選單） | Inline Keyboard（訊息下方按鈕）、Bot Commands（/ 指令選單） |
| 推播 | Push API（免費額度每月 200 則，超過付費） | 無限制 |
| 適合 | Ann 日常：按選單、看通知 | Allen：指令、告警、股票圖卡 |

建議：**兩個都開**，Telegram 先上（10 分鐘就能用），LINE 等 https 反向代理就緒再接。

## 10.2 架構

```
 LINE App ──► LINE Platform ──Webhook POST /line/webhook (簽章驗證)──┐
                                                                     ▼
 Telegram App ──► Telegram API ◄──getUpdates long polling──── magpie-bot :8900
                                                                     │
                     ┌──────────────── 成員白名單 / 角色 / 速率 / 稽核 ─┤
                     │                                               │
          結構化指令（/燈 /冷氣 /窗簾 /情境 /狀態 /掃地）        自然語言
                     │ 直接 HA REST（script.ac_set 等）               │ Hermes /v1/command (source=chat, say=false)
                     ▼                                               ▼
               Home Assistant ◄────────────────────────────── Hermes（guard → 覆誦確認 → dispatch → 回滾）
                     │
                     └── rest_command.magpie_bot_notify ──► POST /v1/notify ──► 推播給成員（LINE push / Telegram sendMessage）
```

設計原則：
1. **結構化指令不經 LLM**：格式明確、延遲 < 1 秒、不需確認（和 HA 儀表板按鈕等價）。
2. **自然語言一律經 Hermes**：`source=chat`，Hermes 仍覆誦「要我…嗎？」，機器人把它變成「好／取消」按鈕；深夜不受 quiet_hours 影響（文字本來就不吵）。
3. **身分**：LINE userId / Telegram chat_id 對應到成員名與角色；未知使用者只會收到自己的 ID 與「請管理員加入」。
4. **推播雙軌**：HA 的 `notify.both` 仍走 Companion App；需要時用 `rest_command.magpie_bot_notify` 同步送到機器人（告警、備援接手、股票圖卡摘要）。

## 10.3 指令文法

| 指令 | 範例 | 動作 | 需確認 |
|---|---|---|---|
| `/狀態` | `/狀態` | 兩人在家否、客廳/主臥溫度、兩台冷氣、睡眠模式、大門、掃地機 | 否 |
| `/情境 <名稱> [開\|關]` | `/情境 睡眠 開`、`/情境 離家` | `input_boolean.sleep_mode / movie_mode / guest_mode`；離家＝全屋關燈＋三台冷氣關 | 否 |
| `/燈 <區域> 開\|關\|<亮度%>` | `/燈 客廳 50` | `light.turn_on/off`、`brightness_pct` | 否 |
| `/冷氣 <區域> 開\|關\|<溫度>` | `/冷氣 主臥 26` | `script.ac_set`（雲端→IR 降級） | 否（18–30 範圍檢查） |
| `/窗簾 <區域> 開\|關\|<位置%>` | `/窗簾 客廳 關` | `cover.*` | 否 |
| `/掃地 [開始\|回充\|暫停]` | `/掃地 回充` | `vacuum.*` | 否 |
| 自然語言 | 「客廳暗一點」「Ann 還在睡嗎」「2330 現在怎樣」 | Hermes | 寫入類：是（按鈕）；唯讀：否 |
| `好` / `取消` | 按鈕或打字 | 回 Hermes 待確認 plan | — |
| `/help` | | 指令說明 | — |

區域別名：客廳／客餐廳 → living；主臥／房間 → master；次臥 → second；玄關 → entry；浴室 → bath（與 Hermes `aliases` 同步）。

## 10.4 介面設計

### Telegram
- `/` 指令選單：`/status`、`/help`（`setMyCommands`）。
- 每則回覆下方 Inline Keyboard：預設快捷（狀態／睡眠／影音／離家／客廳燈開／客廳燈關／主臥26度，可在後台改），每列 3 顆。
- 需確認時只顯示「好 ✅ / 取消 ✖」兩顆。
- 告警推播：純文字；股票圖卡用 `sendPhoto`（v0.2）。

### LINE
- 加好友 → 自動回覆「你的 LINE ID：Uxxxx，請交給管理員」+ 指令說明。
- 每則回覆附 Quick Reply（同上快捷），需確認時只有「好／取消」。
- Rich Menu（建議在 LINE Developers 後台建一個 2×3）：狀態｜睡眠｜影音｜離家｜客廳燈｜主臥冷氣，每顆對應一條指令文字（`message` action）。
- 群組：不建議，LINE 群組內的 userId 在未同意隱私時可能拿不到；一對一使用。

### 角色
| 角色 | 可做 |
|---|---|
| admin | 全部（含自然語言、情境） |
| member | 全部 |
| viewer | 只能 `/狀態`、`/help`（給長輩或訪客看家裡狀態） |

## 10.5 安全

| 面向 | 做法 |
|---|---|
| 身分 | 白名單（平台 + ID）；未列入者任何指令都不執行 |
| LINE 來源驗證 | `X-Line-Signature` HMAC-SHA256（channel secret）比對，不符回 403 |
| Telegram 來源 | long polling 由機器人主動拉，外部無法偽造；token 只在 `config/bot/bot.yaml` |
| 推播 API | `/v1/notify` 與 `/v1/reload` 需 `X-Magpie-Secret`（與熱備共用密鑰） |
| 速率 | 每成員每分鐘 20 則；超過回「指令太頻繁」 |
| 危險動作 | 不開放：開鎖、SOS 透過機器人（`policy.never` 與指令文法都不含） |
| 稽核 | `data/bot/audit.log`：時間、平台、成員、指令、回覆 |
| 公開面 | Telegram 零開埠；LINE 只開 443 → 反向代理 → `bot:8900/line/webhook`（其他路徑不轉） |

## 10.6 建置步驟

### A. Telegram（10 分鐘）
1. Telegram 找 `@BotFather` → `/newbot` → 取得 token。
2. 後台 → LINE / Telegram 機器人 → 貼 token → 套用（會重啟 `magpie-bot`）。
3. 每位成員對機器人送 `/start` → 收到「你的 ID：telegram:123456789」。
4. 後台成員白名單填 `allen:telegram:123456789:admin, ann:telegram:987654321:member` → 套用。
5. 傳 `/狀態` 驗證。

### B. LINE（需公開 https）
1. LINE Developers Console → Provider → Messaging API channel → 取得 Channel secret 與 Channel access token（long-lived）。
2. 反向代理：主機層 Caddy
   ```
   AllenandAnn.duckdns.org {
     handle /line/webhook { reverse_proxy localhost:8900 }
     handle { reverse_proxy localhost:8123 }
   }
   ```
   （或 Cloudflare Tunnel：`cloudflared tunnel --url http://localhost:8900` 只對外露 `/line/webhook`）。
3. Channel 設定 Webhook URL = `https://AllenandAnn.duckdns.org/line/webhook`、開啟 Use webhook、關閉自動回覆訊息。
4. 後台貼 secret / token → 套用；加機器人好友 → 收到 ID → 填白名單 → 套用。
5. LINE Official Account Manager 建 Rich Menu（選配）。

### C. HA 推播同步到機器人（選配）
在任何自動化加一步：
```yaml
- action: rest_command.magpie_bot_notify
  data: { to: all, message: "🛟 主節點失聯，副節點已接手" }
```
`to` 可為 `all`、成員名或角色（`admin`）。建議接的情境：25 凌晨告警、27 設備離線、33 停損告警、熱備接手／回切。

## 10.7 範例對話

```
Ann（LINE）：/情境 睡眠 開
Bot：✅ 睡眠模式已開。   [狀態][睡眠][影音][離家][客廳燈開]…

Allen（Telegram）：客廳燈調到百分之五十
Bot：要我把客廳燈調到50%嗎？   [好 ✅][取消 ✖]
Allen：好
Bot：好了。

Allen：2330 現在怎樣
Bot：台積電 1085 元，漲 1.2%。站上 20 日均，量能是均量的 1.4 倍，RSI 58。非投資建議。

（陌生人）：/燈 客廳 開
Bot：你還不是家庭成員。請把這組 ID 交給管理員加入白名單：telegram:555000
```

## 10.8 驗證清單

| # | 檢查 | 預期 |
|---|---|---|
| 1 | 後台總覽 | `LINE / Telegram 機器人` 綠點；`/v1/health` 顯示成員數與平台 |
| 2 | 未加入白名單者傳指令 | 只回 ID，不執行 |
| 3 | `/燈 客廳 50` | 1 秒內燈變、回覆 💡 |
| 4 | `/冷氣 主臥 35` | 回「溫度要在 18–30 之間」 |
| 5 | 自然語言寫入指令 | 出現「好／取消」按鈕；按「好」才執行 |
| 6 | 深夜 23:30 傳自然語言 | 仍以文字確認（不受語音 quiet_hours 影響） |
| 7 | viewer 角色傳 `/燈 …` | 回「你的權限只能查詢」 |
| 8 | 1 分鐘內傳 25 則 | 第 21 則起回「指令太頻繁」 |
| 9 | LINE：以錯誤簽章 POST webhook | 403 |
| 10 | HA 開發者工具執行 `rest_command.magpie_bot_notify` | 所有成員收到推播 |
| 11 | `data/bot/audit.log` | 每筆指令一行 |

## 10.9 Grok 接口的定位

「Grok Bot」不是訊息平台（X 私訊 API 不對一般機器人開放），所以不列為第三個聊天通道；Grok 以 **Hermes 的雲端大腦選項**接入（05 章 §5.9、後台「語音」頁）。LINE / Telegram 送來的自然語言，會依後台設定由 Ollama 或 Grok 解析成 Plan，其餘流程相同。

## 10.10 v0.2 規劃

- 股票圖卡以圖片推送（Telegram `sendPhoto`、LINE image message）。
- LINE Flex Message 的「家裡現況」卡片（溫度、燈、冷氣一張圖）。
- 成員自助綁定：後台產生一次性邀請碼，成員傳 `/join <碼>` 自動加入。
- 群組模式（Telegram 群組 + `/` 指令），LINE 維持一對一。
