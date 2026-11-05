# 04 · OpenClaw 本地語音管線

> 目標：MLX-Whisper（STT，Metal GPU）、Ollama Qwen3 8B（推理，Metal GPU）、Piper（TTS）全部在 Mac mini 原生跑，HA 的 Assist 管線用它們；語音可從 Companion App / Apple Watch / Siri 捷徑進來，回覆從 HomePod 出去。
> 完成判準：§4.9。本章先用 Ollama 直接當對話代理做通路測試；05 章再把對話代理換成 Hermes。

## 4.1 架構與資源預算

```
 麥克風 ─► HA Assist 管線 ─► STT: Wyoming mlx-whisper (.8:10300)
                           ─► 對話代理: Ollama 整合 → (04) Ollama :11434 / (05) Hermes :8800
                           ─► TTS: Wyoming piper (.8:10200) ─► HomePod (AirPlay) 或 App
```

| 元件 | 跑在哪 | 記憶體 | 延遲（設計值） |
|---|---|---|---|
| MLX-Whisper `large-v3-turbo`（語言固定 zh） | macOS 原生 Python（**Metal GPU**） | 1.6 GB（q4 版 0.5 GB） | ~200 ms（5 秒內短句，近即時） |
| Ollama **Qwen3 8B** Q4_K_M（非 thinking） | macOS 原生（Metal） | 5.2 GB | ~250 ms 首 token |
| Piper `zh_CN-huayan-medium` | macOS 原生 Python | 0.2 GB | ~80 ms |
| Hermes（05 章） | macOS 原生 Python | 0.4 GB | ~40 ms |
| HAOS VM | UTM | 2.0 GB | — |
| macOS | — | 3.0 GB | — |
| 合計 | | **12.4 / 16 GB** | 端到端 ~570 ms |

選型說明（v1.6 起）：

- **STT 改 MLX-Whisper**：Faster-Whisper（CTranslate2）在 Apple Silicon 只能用 CPU，只跑得動 `small`；`wyoming-mlx-whisper` 走 Metal，可以用 `large-v3-turbo`，中文辨識準確度明顯高於 small（「主臥／主握」這類誤辨大幅減少），仍是 Wyoming 協定，HA 端設定完全一樣。只支援 Apple Silicon；青鳥 Linux 節點（HA Black）仍用容器版 faster-whisper。
- **LLM 改 Qwen3 8B**：Llama 3 的繁體中文理解與 JSON 結構化輸出都弱於 Qwen3；Hermes 靠模型輸出 JSON 計畫，中文理解直接影響「這個我還不會」的比例。Qwen3 要關 thinking（Hermes 呼叫時帶 `think: false`），否則回覆會夾 `<think>` 拖慢。
- 記憶體仍在 16 GB 安全範圍；24 GB 機器可改 `qwen3:14b`（9 GB）。

## 4.2 目錄與 Python 環境

```bash
mkdir -p ~/openclaw/{whisper,piper,voices,logs}
cd ~/openclaw
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install wyoming-mlx-whisper wyoming-piper piper-tts     # mlx-whisper 需 Apple Silicon + Python 3.10–3.13
```

## 4.3 Ollama（Metal 推理）

```bash
brew install ollama
# 讓 Ollama 監聽區域網路（HAOS VM 在 .88 要連得到）
launchctl setenv OLLAMA_HOST 0.0.0.0
launchctl setenv OLLAMA_KEEP_ALIVE -1          # 模型常駐，免首句冷啟動
brew services restart ollama
ollama pull qwen3:8b                            # Q4_K_M，約 5.2 GB
# 試跑（/no_think 關掉思考模式；Hermes 程式內是用 API 參數 think:false）
ollama run qwen3:8b "/no_think 用繁體中文回答：客廳燈打開，輸出 JSON {intent, actions}"   # 第一次會慢，之後 < 1 秒
curl -s http://192.168.0.8:11434/api/tags | jq '.models[].name'   # 從 HAOS VM 也要通：ha 終端機 curl 同網址
```

brew services 會隨登入自動啟動。要讓 `OLLAMA_HOST` 永久生效，再把它寫進 brew 的 plist：

```bash
sed -i '' 's#<dict>#<dict><key>EnvironmentVariables</key><dict><key>OLLAMA_HOST</key><string>0.0.0.0</string><key>OLLAMA_KEEP_ALIVE</key><string>-1</string></dict>#' \
  ~/Library/LaunchAgents/homebrew.mxcl.ollama.plist
brew services restart ollama
```

## 4.4 MLX-Whisper（Wyoming 伺服器，Metal GPU）

```bash
cat > ~/Library/LaunchAgents/com.allenann.whisper.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.allenann.whisper</string>
  <key>ProgramArguments</key><array>
    <string>/Users/allen/openclaw/venv/bin/wyoming-mlx-whisper</string>
    <string>--uri</string><string>tcp://0.0.0.0:10300</string>
    <string>--model</string><string>mlx-community/whisper-large-v3-turbo</string>
    <string>--language</string><string>zh</string>
    <string>--initial-prompt</string><string>以下是台灣繁體中文的智慧家庭語音指令：客廳、主臥、次臥、玄關、冷氣、窗簾、掃地機。</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>HF_HOME</key><string>/Users/allen/openclaw/whisper</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/allen/openclaw/logs/whisper.log</string>
  <key>StandardErrorPath</key><string>/Users/allen/openclaw/logs/whisper.err</string>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.allenann.whisper.plist
sleep 60; tail -5 ~/openclaw/logs/whisper.err      # 第一次會從 Hugging Face 下載 large-v3-turbo（~1.6 GB），看到 Ready 即成功
```

- 記憶體緊時把 `--model` 改成 `mlx-community/whisper-large-v3-turbo-q4`（0.5 GB，準確度接近）。
- `--initial-prompt` 放常用房間與設備名，能把專有名詞的辨識率再拉高；輸出可能簡繁混用，Hermes 一律轉繁體（05 章 `textnorm.py`），HA 內建 Assist 不受影響。
- 若 Mac 不是 Apple Silicon 或 Python 版本是 3.14：退回 `pip install wyoming-faster-whisper`，plist 的程式改 `wyoming-faster-whisper --model small --compute-type int8`。

## 4.5 Piper（Wyoming 伺服器，中文聲線）

```bash
cd ~/openclaw/voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
# 試聽
echo "歡迎回家，冷氣已設為二十四度。" | ~/openclaw/venv/bin/piper -m zh_CN-huayan-medium.onnx -f /tmp/test.wav && afplay /tmp/test.wav

cat > ~/Library/LaunchAgents/com.allenann.piper.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.allenann.piper</string>
  <key>ProgramArguments</key><array>
    <string>/Users/allen/openclaw/venv/bin/wyoming-piper</string>
    <string>--uri</string><string>tcp://0.0.0.0:10200</string>
    <string>--piper</string><string>/Users/allen/openclaw/venv/bin/piper</string>
    <string>--voice</string><string>zh_CN-huayan-medium</string>
    <string>--data-dir</string><string>/Users/allen/openclaw/voices</string>
    <string>--download-dir</string><string>/Users/allen/openclaw/voices</string>
    <string>--length-scale</string><string>1.05</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/allen/openclaw/logs/piper.log</string>
  <key>StandardErrorPath</key><string>/Users/allen/openclaw/logs/piper.err</string>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.allenann.piper.plist
```

數字讀法：Piper 中文聲線對阿拉伯數字讀得不穩，Hermes 回覆前會把 `24` 轉成「二十四」（05 章 `textnorm.py`）。HA 自己的 TTS 文字也請用中文數字。

## 4.6 HA 端：Wyoming ×2 + Ollama 整合 + Assist 管線

1. 設定 → 整合 → 新增 → **Wyoming Protocol** → 主機 `192.168.0.8`、埠 `10300` → 名稱 `mlx-whisper`。
2. 再新增一次 Wyoming → `192.168.0.8`、`10200` → `piper`。
3. 設定 → 整合 → 新增 → **Ollama** → URL `http://192.168.0.8:11434` → 模型 `qwen3:8b` → 「控制 Home Assistant」先選 **Assist**（本章測通路用；05 章會改成指向 Hermes 並選「不控制」）。
4. 設定 → 語音助理 → 新增助理：
   - 名稱 `OpenClaw`
   - 語言 `中文（台灣）`
   - 對話代理 `Ollama`（05 章改 `Hermes`）
   - 語音轉文字 `mlx-whisper`
   - 文字轉語音 `piper`，聲線 `zh_CN-huayan-medium`
   - 設為 **偏好的助理**。
5. 設定 → 語音助理 → 「公開」：讓 Assist 看得到的實體**只勾**燈、空調、窗簾、掃地機、媒體播放器與感測器（不要公開 `input_boolean.sXX_enabled` 之類內部開關）。

測試：HA 右上角 Assist 圖示 → 打字「把客廳燈調到百分之五十」→ 應該有回覆且燈變動。再按麥克風講一次。

## 4.7 語音進聲路徑（三條都做，HomePod 麥克風不可用）

⚠️ Apple 不開放 HomePod 麥克風給第三方。設計文件的「AirPlay → mic-bridge」不可行；以下三條是真的能用的。

### A. Siri 捷徑（HomePod / iPhone / Watch 都能叫）— 固定句型

適合「Allen 回家了」「晚安」這種固定指令。原理：HomePod 聽到「嘿 Siri，Allen 回家了」→ 執行同名捷徑 → 捷徑把文字 POST 到 HA webhook → HA 自動化丟給 Assist 處理並由 HomePod 播回覆。

欄位對應 `packages/s00_voice.yaml` 的 `s00_voice_webhook`：捷徑 POST `{"text","speaker","output"}` → `rest_command.hermes_command`（Hermes 離線時自動退回 HA 內建 Assist）→ `script.say` 到指定 HomePod。

#### A-0 事前準備（一次）

| 項目 | 怎麼拿 |
|---|---|
| webhook id | `secrets.yaml` 的 `openclaw_webhook_id`（青鳥路線：後台 → 語音 頁自動產生，複製即可）。格式 `openclaw_voice_` + 32 位隨機字，例如 `openclaw_voice_k3Jd9...`。 |
| HA 網址 | 07 章做完前：`http://192.168.0.88:8123`（在家 Wi-Fi 才能用）；做完後：`https://AllenandAnn.duckdns.org`（在外也能用，HomePod 在家兩者皆可）。青鳥 + LB 路線用 VIP `http://192.168.0.100:8123`。 |
| 先驗證 webhook 活著 | Mac 終端機：`curl -X POST http://192.168.0.88:8123/api/webhook/<id> -H 'Content-Type: application/json' -d '{"text":"客廳幾度","speaker":"allen","output":"living_homepod"}'`；HomePod 應說出溫度。這一步不通就不要往下做捷徑。 |

#### A-1 建立第一個捷徑「Allen 回家了」（iPhone，約 5 分鐘）

每一步後面的 📷 是建議截圖位置；截下來放進 `docs/SOP/assets/siri/` 並以同名檔名取代（`siri-01.png` …），`build_site.py` 會自動帶進網頁。

| 步 | 操作 | 要看到什麼 | 📷 |
|---|---|---|---|
| 1 | 開 **捷徑** App → 右上 **＋** | 空白捷徑編輯頁，上方標題「新捷徑 1」 | siri-01 |
| 2 | 點上方標題 → **重新命名** → 輸入 `Allen 回家了` | 標題變成這五個字。**這個名字就是對 Siri 說的話**，不要加標點 | siri-02 |
| 3 | 下方搜尋動作 → 輸入「URL」→ 選 **取得 URL 內容**（Get Contents of URL） | 動作卡片出現，顯示「取得 [URL] 的內容」 | siri-03 |
| 4 | 點卡片裡的 `URL` 欄 → 貼上 `http://192.168.0.88:8123/api/webhook/<你的 id>` | URL 完整、結尾是你的 id | siri-04 |
| 5 | 點卡片右側 **▸ 顯示更多** | 展開「方法 / 標頭 / 請求本文」 | siri-05 |
| 6 | **方法** 改成 `POST` | 方法顯示 POST | siri-06 |
| 7 | **請求本文** 選 `JSON` | 出現「新增欄位」 | siri-07 |
| 8 | 新增欄位 → 類型 **文字**：鍵 `text`、值 `Allen 回家了` | 第一列 text | siri-08 |
| 9 | 再新增文字欄位：鍵 `speaker`、值 `allen` | 第二列 speaker | — |
| 10 | 再新增文字欄位：鍵 `output`、值 `living_homepod` | 第三列 output（主臥用 `master_mini`，全部用 `all`；對應 `script.say` 的 target 選項） | siri-09 |
| 11 | **標頭** 新增：鍵 `Content-Type`、值 `application/json` | 標頭一列（HA 收 JSON 必須） | siri-10 |
| 12 | 點右下 **▶** 試跑 | 第一次會問「允許 Allen 回家了 連線到 192.168.0.88？」→ **總是允許**；HomePod 應播出回覆 | siri-11 |
| 13 | 右上 **完成** | 捷徑出現在「所有捷徑」 | — |
| 14 | 捷徑上長按 → **詳細資訊** → 關掉「在分享工作表中顯示」、開 **「在 Apple Watch 上顯示」** | 手錶也能按 | siri-12 |

HomePod 執行條件：HomePod 與 iPhone 同一 Apple ID、家庭 App 裡「個人請求」對此 HomePod 已開（家庭 App → 你的名字 → 個人請求 → 勾該 HomePod），且 iPhone 在家中網路。這樣對 HomePod 說「嘿 Siri，Allen 回家了」，它會跑 iPhone 上的這個捷徑。

#### A-2 複製出其餘捷徑

長按「Allen 回家了」→ **複製** → 改名與改 `text` 值即可（其他欄位不動）：

| 捷徑名（對 Siri 說的話） | text | speaker | output | 對應情境 |
|---|---|---|---|---|
| `Ann 回家了` | Ann 回家了 | ann | living_homepod | 30 |
| `晚安` | 晚安 | allen | master_mini | 13 / 15 |
| `我出門了` | 我出門了 | allen | living_homepod | 04 |
| `Ann 還在睡嗎` | Ann 還在睡嗎 | allen | living_homepod | 14 |
| `二三三零現在怎樣` | 2330 現在怎樣 | allen | living_homepod | 32 |
| `還原剛剛那個` | 還原剛剛那個 | allen | living_homepod | Hermes 回滾 |

Siri 聽不懂名字時：把捷徑名改成口語更常見的講法（例如「晚安」有時會被 Siri 自己的晚安回應吃掉 → 改成「家裡晚安」）。

#### A-3 可選：帶變數的自由句捷徑「跟管家說」

1. 新捷徑 `跟管家說` → 動作 **聽寫文字**（Dictate Text，語言 中文台灣）。
2. 動作 **取得 URL 內容**，同 A-1，但 `text` 的值點選「聽寫的文字」魔法變數。
3. 說「嘿 Siri，跟管家說」→ Siri 回「好，請說」→ 講任何一句 → 走 Hermes。

這條路徑的 STT 是 Apple 的（不是 Whisper），準確度高但句子會上傳 Apple；只在 B 路徑不方便時用。

#### A-4 測試與排錯

| 症狀 | 檢查 | 處置 |
|---|---|---|
| 試跑跳「無法連線」 | iPhone 是否在家 Wi-Fi；URL 打錯 | 用 A-0 的 curl 先驗證 |
| 回 `405` / `400` | 方法不是 POST；本文不是 JSON；少 Content-Type | 重做第 6、7、11 步 |
| 捷徑成功但 HomePod 沒聲 | HA 記錄簿有無 `語音：Siri 捷徑 webhook` 觸發 | `output` 拼錯 → 看 `script.say` 的 target 清單；深夜 sleep_mode 會改推播（§4.8） |
| HomePod 回「我在 iPhone 上找不到」 | 個人請求沒開 / Apple ID 不同 | 家庭 App → 個人請求 |
| 在外面 4G 跑失敗 | URL 仍是 192.168.0.88 | 07 章完成後改成 https 網址 |

### B. Companion App / Apple Watch Assist — 自由句

- iPhone：HA App → 設定 → Companion App → Assist → 預設管線 `OpenClaw`；加到主畫面小工具或動作按鈕。
- Apple Watch：HA Watch App → 複雜功能加 Assist → 抬腕按一下直接講。
- 回覆：App 會自己播；若要改由 HomePod 播，在 `s00_voice.yaml` 的 `conversation` 事件自動化裡轉送。

### C. HA Voice Preview Edition（選配，真正的本地喚醒詞麥克風）

買一顆放客廳：設定 → 整合 → 自動發現 → 選管線 `OpenClaw` → 喚醒詞 `Okay Nabu`（或自訓）。這是唯一「不用拿手機」的免手路徑。音訊輸出可設為本機喇叭或在自動化中轉到 HomePod。

## 4.8 HomePod 播報與深夜音量（`script.say`）

`packages/s00_common.yaml` 的 `script.say`：

- 參數 `message`、`target`（`living_homepod` / `master_mini` / `all`，預設客廳）。
- 23:00–07:00 音量上限 20%；`input_boolean.sleep_mode` 開且 target 含主臥 → 改推播 `notify.both`，不出聲。
- 先 `media_player.volume_set` → `tts.speak`（piper）→ 不還原音量（HomePod 自己會記住上次音量，避免切換時爆音）。

## 4.9 驗證清單

| # | 檢查 | 預期 |
|---|---|---|
| 1 | `curl http://192.168.0.8:11434/api/tags` 在 HAOS 終端機 | 列出 `qwen3:8b` |
| 2 | `launchctl list \| grep allenann` | whisper、piper 都在 |
| 3 | HA → 整合 | Wyoming ×2、Ollama 綠色 |
| 4 | HA Assist 打字「客廳燈開」 | 燈亮，有中文回覆 |
| 5 | HA Assist 講話「主臥冷氣二十六度」 | STT 正確（large-v3-turbo 不會聽成「主握」）；冷氣設 27（eco 守門）或 26（守門暫停） |
| 6 | HomePod 說「嘿 Siri，Allen 回家了」 | HomePod 播回覆（內容先隨 Ollama，05 章後變 Hermes 覆誦確認） |
| 7 | 深夜（或手動開 sleep_mode）呼叫 `script.say` target 主臥 | 不出聲，改推播 |
| 8 | 活動監視器 | 記憶體壓力綠色；Ollama 常駐約 5–6 GB |
| 9 | 重開 Mac mini | 5 分鐘內 whisper/piper/ollama/HAOS 全部回來 |

通過 → 05 章。
