# 04 · OpenClaw 本地語音管線

> 目標：Faster-Whisper（STT）、Ollama Llama 3 8B（推理）、Piper（TTS）全部在 Mac mini 原生跑（Ollama 走 Metal GPU），HA 的 Assist 管線用它們；語音可從 Companion App / Apple Watch / Siri 捷徑進來，回覆從 HomePod 出去。
> 完成判準：§4.9。本章先用 Ollama 直接當對話代理做通路測試；05 章再把對話代理換成 Hermes。

## 4.1 架構與資源預算

```
 麥克風 ─► HA Assist 管線 ─► STT: Wyoming faster-whisper (.10:10300)
                           ─► 對話代理: Ollama 整合 → (04) Ollama :11434 / (05) Hermes :8800
                           ─► TTS: Wyoming piper (.10:10200) ─► HomePod (AirPlay) 或 App
```

| 元件 | 跑在哪 | 記憶體 | 延遲（設計值） |
|---|---|---|---|
| Faster-Whisper `small` INT8（語言固定 zh） | macOS 原生 Python（CPU） | 0.6 GB | ~150 ms（5 秒內短句） |
| Ollama Llama 3 8B Q4_0 | macOS 原生（Metal） | 5.4 GB | ~250 ms 首 token |
| Piper `zh_CN-huayan-medium` | macOS 原生 Python | 0.2 GB | ~80 ms |
| Hermes（05 章） | macOS 原生 Python | 0.4 GB | ~40 ms |
| HAOS VM | UTM | 2.0 GB | — |
| macOS | — | 3.0 GB | — |
| 合計 | | **11.6 / 16 GB** | 端到端 ~520 ms |

⚠️ Faster-Whisper 在 Apple Silicon 只用 CPU（CTranslate2 無 Metal）。短指令 150 ms 夠用；若想用 GPU 可改 `whisper.cpp`（`brew install whisper-cpp`）搭配 `wyoming-whisper-cpp`，本 SOP 以 Faster-Whisper 為主因為安裝最簡單。

## 4.2 目錄與 Python 環境

```bash
mkdir -p ~/openclaw/{whisper,piper,voices,logs}
cd ~/openclaw
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install wyoming-faster-whisper wyoming-piper piper-tts
```

## 4.3 Ollama（Metal 推理）

```bash
brew install ollama
# 讓 Ollama 監聽區域網路（HAOS VM 在 .11 要連得到）
launchctl setenv OLLAMA_HOST 0.0.0.0
launchctl setenv OLLAMA_KEEP_ALIVE -1          # 模型常駐，免首句冷啟動
brew services restart ollama
ollama pull llama3:8b                           # Q4_0，約 4.7 GB
ollama run llama3:8b "用繁體中文回答：客廳燈打開，輸出 JSON {intent, actions}"   # 第一次會慢，之後 < 1 秒
curl -s http://192.168.0.10:11434/api/tags | jq '.models[].name'   # 從 HAOS VM 也要通：ha 終端機 curl 同網址
```

brew services 會隨登入自動啟動。要讓 `OLLAMA_HOST` 永久生效，再把它寫進 brew 的 plist：

```bash
sed -i '' 's#<dict>#<dict><key>EnvironmentVariables</key><dict><key>OLLAMA_HOST</key><string>0.0.0.0</string><key>OLLAMA_KEEP_ALIVE</key><string>-1</string></dict>#' \
  ~/Library/LaunchAgents/homebrew.mxcl.ollama.plist
brew services restart ollama
```

## 4.4 Faster-Whisper（Wyoming 伺服器）

```bash
cat > ~/Library/LaunchAgents/com.allenann.whisper.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.allenann.whisper</string>
  <key>ProgramArguments</key><array>
    <string>/Users/allen/openclaw/venv/bin/wyoming-faster-whisper</string>
    <string>--uri</string><string>tcp://0.0.0.0:10300</string>
    <string>--model</string><string>small</string>
    <string>--language</string><string>zh</string>
    <string>--compute-type</string><string>int8</string>
    <string>--beam-size</string><string>2</string>
    <string>--data-dir</string><string>/Users/allen/openclaw/whisper</string>
    <string>--download-dir</string><string>/Users/allen/openclaw/whisper</string>
    <string>--initial-prompt</string><string>以下是繁體中文的智慧家庭語音指令。</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/allen/openclaw/logs/whisper.log</string>
  <key>StandardErrorPath</key><string>/Users/allen/openclaw/logs/whisper.err</string>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.allenann.whisper.plist
sleep 20; tail -5 ~/openclaw/logs/whisper.err      # 第一次會下載 small 模型（~480 MB），看到 Ready 即成功
```

（`small` 是多語模型，`--language zh` 固定中文；設計文件寫的 `small.zh` 即此組合。輸出會是簡體，Hermes/Ollama 不受影響；TTS 前由 05 章 Hermes 轉繁體。）

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

1. 設定 → 整合 → 新增 → **Wyoming Protocol** → 主機 `192.168.0.10`、埠 `10300` → 名稱 `faster-whisper`。
2. 再新增一次 Wyoming → `192.168.0.10`、`10200` → `piper`。
3. 設定 → 整合 → 新增 → **Ollama** → URL `http://192.168.0.10:11434` → 模型 `llama3:8b` → 「控制 Home Assistant」先選 **Assist**（本章測通路用；05 章會改成指向 Hermes 並選「不控制」）。
4. 設定 → 語音助理 → 新增助理：
   - 名稱 `OpenClaw`
   - 語言 `中文（台灣）`
   - 對話代理 `Ollama`（05 章改 `Hermes`）
   - 語音轉文字 `faster-whisper`
   - 文字轉語音 `piper`，聲線 `zh_CN-huayan-medium`
   - 設為 **偏好的助理**。
5. 設定 → 語音助理 → 「公開」：讓 Assist 看得到的實體**只勾**燈、空調、窗簾、掃地機、媒體播放器與感測器（不要公開 `input_boolean.sXX_enabled` 之類內部開關）。

測試：HA 右上角 Assist 圖示 → 打字「把客廳燈調到百分之五十」→ 應該有回覆且燈變動。再按麥克風講一次。

## 4.7 語音進聲路徑（三條都做，HomePod 麥克風不可用）

⚠️ Apple 不開放 HomePod 麥克風給第三方。設計文件的「AirPlay → mic-bridge」不可行；以下三條是真的能用的。

### A. Siri 捷徑（HomePod / iPhone / Watch 都能叫）— 固定句型

適合「Allen 回家了」「晚安」這種固定指令。原理：HomePod 聽到「嘿 Siri，Allen 回家了」→ 執行同名捷徑 → 捷徑把文字 POST 到 HA webhook → HA 自動化丟給 Assist 處理並由 HomePod 播回覆。

1. iPhone 捷徑 App → 新增捷徑 → 名稱 `Allen 回家了`：
   - 動作 1：**取得 URL 內容** — URL `https://AllenandAnn.duckdns.org/api/webhook/openclaw_voice_<隨機32字>`（07 章前先用 `http://192.168.0.11:8123/...`），方法 `POST`，請求本文 JSON：`text` = `Allen 回家了`，`speaker` = `allen`，`output` = `living_homepod`。
   - 不需 token：webhook 本身不驗證，所以 ID 要長且隨機。
2. 在 HomePod 說「嘿 Siri，Allen 回家了」即可（HomePod 會執行同一 Apple ID 下的個人捷徑）。
3. 對應 HA 自動化在 `packages/s00_voice.yaml`：webhook → `conversation.process`（agent = OpenClaw/Hermes）→ 回覆文字 → `script.say` 到指定 HomePod。
4. 再做幾個：`晚安`、`我出門了`、`Ann 還在睡嗎`、`二三三零現在怎樣`。

### B. Companion App / Apple Watch Assist — 自由句

- iPhone：HA App → 設定 → Companion App → Assist → 預設管線 `OpenClaw`；加到主畫面小工具或動作按鈕。
- Apple Watch：HA Watch App → 複雜功能加 Assist → 抬腕按一下直接講。
- 回覆：App 會自己播；若要改由 HomePod 播，在 `s00_voice.yaml` 的 `conversation` 事件自動化裡轉送。

### C. HA Voice Preview Edition（選配，真正的本地喚醒詞麥克風）

買一顆放客廳：設定 → 整合 → 自動發現 → 選管線 `OpenClaw` → 喚醒詞 `Okay Nabu`（或自訓）。這是唯一「不用拿手機」的免手路徑。音訊輸出可設為本機喇叭或在自動化中轉到 HomePod。

## 4.8 HomePod 播報與深夜音量（`script.say`）

`packages/s00_common.yaml` 的 `script.say`：

- 參數 `message`、`target`（`living_homepod` / `master_homepod_mini` / `all`，預設客廳）。
- 23:00–07:00 音量上限 20%；`input_boolean.sleep_mode` 開且 target 含主臥 → 改推播 `notify.both`，不出聲。
- 先 `media_player.volume_set` → `tts.speak`（piper）→ 不還原音量（HomePod 自己會記住上次音量，避免切換時爆音）。

## 4.9 驗證清單

| # | 檢查 | 預期 |
|---|---|---|
| 1 | `curl http://192.168.0.10:11434/api/tags` 在 HAOS 終端機 | 列出 `llama3:8b` |
| 2 | `launchctl list \| grep allenann` | whisper、piper 都在 |
| 3 | HA → 整合 | Wyoming ×2、Ollama 綠色 |
| 4 | HA Assist 打字「客廳燈開」 | 燈亮，有中文回覆 |
| 5 | HA Assist 講話「主臥冷氣二十六度」 | STT 正確；冷氣設 26 |
| 6 | HomePod 說「嘿 Siri，Allen 回家了」 | HomePod 播回覆（內容先隨 Ollama，05 章後變 Hermes 覆誦確認） |
| 7 | 深夜（或手動開 sleep_mode）呼叫 `script.say` target 主臥 | 不出聲，改推播 |
| 8 | 活動監視器 | 記憶體壓力綠色；Ollama 常駐約 5–6 GB |
| 9 | 重開 Mac mini | 5 分鐘內 whisper/piper/ollama/HAOS 全部回來 |

通過 → 05 章。
