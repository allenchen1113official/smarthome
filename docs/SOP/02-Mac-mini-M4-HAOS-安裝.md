# 02 · Mac mini M4 整備與 HAOS 安裝

> 目標：Mac mini 24/7 不睡、斷電自動開機；HAOS 以 UTM 虛擬機跑在上面，拿到 `192.168.0.11`，Zigbee Stick 直通進 VM；HA 完成初始化並裝好基礎附加元件。
> 完成判準：§2.9 檢查全部通過。

## 2.1 macOS 初始設定（約 30 分鐘）

1. 全新開機 → Apple ID 登入（與 HomePod 同一組）→ 使用者名稱 `allen`，**開啟自動登入**（系統設定 → 使用者與群組 → 自動登入 → allen；FileVault 必須關閉才能自動登入，Mac mini 放在家裡可接受）。
2. 系統設定 → 一般 → 共享：開 **螢幕共享**、**遠端登入（SSH）**、**檔案共享**（之後 Hermes 要掛 HAOS 的 Samba，反向不需要）。
3. 電源與睡眠（終端機執行）：

```bash
sudo pmset -a sleep 0 disksleep 0 displaysleep 10
sudo pmset -a disablesleep 1          # 連蓋上也不睡（Mac mini 無蓋，保險）
sudo pmset -a autorestart 1           # 斷電恢復後自動開機
sudo pmset -a womp 1                  # 網路喚醒
pmset -g | grep -E "sleep|autorestart"
```

4. 系統設定 → 一般 → 軟體更新 → **關閉「自動安裝 macOS 更新」**（保留安全性回應）。更新時間由你決定，避免半夜重開。
5. 系統設定 → 一般 → 登入項目：之後會把 UTM 與 Hermes 加進來。
6. 時區 `台北`，24 小時制。
7. 安裝 Homebrew 與基本工具：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile && eval "$(/opt/homebrew/bin/brew shellenv)"
brew install git python@3.12 jq wget htop
brew install --cask utm
```

## 2.2 下載 HAOS 映像檔

HAOS 的 Apple Silicon 版本是 **generic-aarch64** 的 qcow2：

```bash
mkdir -p ~/VM && cd ~/VM
# 到 https://github.com/home-assistant/operating-system/releases 找最新穩定版，例如 16.x
# 檔名格式：haos_generic-aarch64-<版本>.qcow2.xz
wget https://github.com/home-assistant/operating-system/releases/latest/download/haos_generic-aarch64-16.2.qcow2.xz
xz -d haos_generic-aarch64-*.qcow2.xz
ls -lh ~/VM          # 應看到約 1.5 GB 的 .qcow2
```

（版本號以 releases 頁面實際最新為準；`latest/download/` 路徑需帶正確檔名。）

## 2.3 用 UTM 建立 HAOS 虛擬機（約 20 分鐘）

1. 開 UTM → **Create a New Virtual Machine** → **Virtualize**（不是 Emulate）→ **Other**。
2. Boot：勾 **Skip ISO boot**。
3. Hardware：記憶體 **2048 MB**（設計記憶體預算 2 GB；若 Ollama 之後改小模型可提到 3072），CPU **2 核**。
4. Storage：隨便給 1 GB（等下會刪掉換成 qcow2）。
5. Shared Directory：跳過。
6. Summary：名稱 `HAOS`，勾 **Open VM Settings** → Save。
7. 在 VM Settings：
   - **System**：確認 Architecture `ARM64 (aarch64)`，Machine `QEMU 7.x ARM Virtual Machine (virt)`。
   - **QEMU**：勾 **UEFI Boot**（預設已勾）。
   - **Drives**：選取剛才那顆 1 GB 磁碟 → Delete。再 **New…** → **Import** → 選 `~/VM/haos_generic-aarch64-16.2.qcow2`，Interface `VirtIO`。
   - **Network**：Network Mode **Bridged (Advanced)**，Bridged Interface 選有線 `en0`。MAC Address 按 Random 產生一次後**記下來**（DHCP 保留用）。
   - **Sharing**：USB Sharing 只有改用 USB Stick 備案時才需要。
   - Save。
8. 按 ▶ 啟動。畫面跑完 HAOS 開機後會停在 `homeassistant login:` 或 `ha >` 提示字元。
9. 在 VM 主控台輸入 `ha network info`（若是 `login:` 先打 `root` 無密碼）→ 記下 VM 拿到的 IP（動態池 .1xx）。
10. 回路由器 DHCP 保留：把這個 MAC 保留成 `192.168.0.11`，然後在 VM 主控台 `ha host reboot`。重開後 `ha network info` 應顯示 `192.168.0.11`。

### 讓 UTM 開機自動啟動 HAOS

```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.allenann.utm-haos.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.allenann.utm-haos</string>
  <key>ProgramArguments</key><array>
    <string>/Applications/UTM.app/Contents/MacOS/utmctl</string><string>start</string><string>HAOS</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>300</integer>   <!-- 每 5 分鐘確認一次：已在跑就無事 -->
  <key>StandardOutPath</key><string>/tmp/utm-haos.log</string>
  <key>StandardErrorPath</key><string>/tmp/utm-haos.err</string>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.allenann.utm-haos.plist
/Applications/UTM.app/Contents/MacOS/utmctl list        # 應看到 HAOS started
```

同時把 **UTM.app** 加進「登入項目」（系統設定 → 一般 → 登入項目），搭配自動登入，斷電重開後 5 分鐘內 HA 會自己回來。

## 2.4 Zigbee 協調器：SLZB-06（網路型，建議）或 USB Stick 直通

熱備雙節點（07 章）需要兩台 HA 都連得到同一個協調器，所以採 **SLZB-06**：接 PoE、DHCP 保留 `192.168.0.25`，網頁設定為 Zigbee Coordinator (Ethernet)，Z2M 的 `serial.port` 填 `tcp://192.168.0.25:6638`（§2.7）。不需要任何 USB 直通，以下 USB 作法保留為備案。

### 備案：USB Stick 直通

1. SONOFF ZBDongle-E 用 1 m USB 延長線插 Mac mini。
2. UTM 視窗工具列 → USB 圖示 → 勾選 `ITEAD SONOFF Zigbee 3.0 USB Dongle Plus V2`（或 `Silicon Labs CP210x`）。
3. VM 主控台：`ha hardware info | grep -A3 tty` 應看到 `/dev/ttyUSB0` 或 `/dev/ttyACM0`。
4. 讓它每次開機都自動直通：VM Settings → **USB** → 把該裝置加入「Connected USB devices」清單（UTM 會記住 VID/PID，下次啟動自動接上）。

⚠️ 若直通不穩（Zigbee2MQTT 頻繁 `Adapter disconnected`），備案是**在 macOS 主機跑 Zigbee2MQTT**（`brew install node && npm i -g zigbee2mqtt`），改連 HAOS 內的 Mosquitto；功能完全一樣，只是不經 USB 直通。08 章有步驟。

## 2.5 Home Assistant 初始化（約 15 分鐘）

1. 瀏覽器開 `http://192.168.0.11:8123`（第一次要等 10–20 分鐘下載容器，看到「準備中」正常）。
2. 建立擁有者帳號：`allen`（強密碼，存密碼管理器）。
3. 家的名稱 `Allen & Ann`、地點（地圖點到家，這決定日出日落與天氣）、時區 `Asia/Taipei`、單位公制。
4. 分析資料：全部關閉（憲章 III）。
5. 自動發現的整合先**跳過**，03 章逐一加。
6. 設定 → 人員：新增 `Ann`（允許登入、一般使用者）。
7. 設定 → 區域與區塊：新增 §0.5 的六個區域 `玄關 / 客餐廳 / 臥室玄關 / 主臥 / 次臥 / 浴室`。

## 2.6 基礎附加元件（設定 → 附加元件 → 附加元件商店）

依序安裝並啟動，全部勾「開機時啟動」與「看門狗」：

| 附加元件 | 用途 | 關鍵設定 |
|---|---|---|
| **File editor** 或 **Studio Code Server** | 編 YAML | 側欄顯示 |
| **Terminal & SSH** | 進 HAOS 下指令 | 設密碼或公鑰；側欄顯示 |
| **Samba share** | 把 `/config`、`/media`、`/backup` 分享給 Mac mini | username `ha`、密碼存密碼管理器；`allow_hosts` 加 `192.168.0.0/24` |
| **Mosquitto broker** | MQTT 匯流排 | 不用改設定；在 HA 設定 → 人員 新增使用者 `mqtt`（給 Z2M 與 Hermes 用） |
| **Zigbee2MQTT** | Zigbee 設備 | 見 §2.7 |
| **Google Drive Backup**（選）或內建備份 | 07 章 | — |

### 在 Mac mini 掛載 HAOS 分享（Hermes 寫圖卡用）

Finder → 前往 → 連接伺服器 → `smb://ha@192.168.0.11/config` 與 `smb://ha@192.168.0.11/media`，勾「記住密碼」。掛載後路徑為 `/Volumes/config`、`/Volumes/media`。要開機自動掛載：系統設定 → 登入項目 → 把這兩個磁碟拖進去。

## 2.7 Zigbee2MQTT 設定

附加元件 → Zigbee2MQTT → 設定（YAML 模式）：

```yaml
data_path: /config/zigbee2mqtt
socat:
  enabled: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://core-mosquitto:1883
  user: mqtt
  password: !secret mqtt_password   # 附加元件設定頁不支援 !secret，直接填密碼
serial:
  port: tcp://192.168.0.25:6638     # SLZB-06（07 章熱備）；USB 備案改 /dev/ttyUSB0
  adapter: ember                    # SLZB-06 / ZBDongle-E 用 ember；zstack 型號改 zstack
  baudrate: 115200
advanced:
  channel: 15                       # 避開 WiFi 2.4G ch 11；WiFi 用 ch 1 就選 20/25
  network_key: GENERATE
  pan_id: GENERATE
  ext_pan_id: GENERATE
  log_level: info
frontend:
  port: 8099
homeassistant:
  enabled: true
permit_join: false
```

啟動 → 記錄顯示 `Zigbee2MQTT started!` → 側欄打開 Z2M 前端。配對設備在 03 章。

## 2.8 configuration.yaml 基礎片段

用 File editor 開 `/config/configuration.yaml`，確保有以下內容（完整版在 `ha-config/configuration.yaml.snippet`）：

```yaml
default_config:

homeassistant:
  packages: !include_dir_named packages      # 每個情境一個 package
  customize: !include customize.yaml

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.30.33.0/24                          # NGINX / 附加元件內網
    - 127.0.0.1

logger:
  default: warning

# 之後各章會加：rest_command / shell_command / notify 群組 / template
```

建立空資料夾與檔案：

```bash
# Terminal & SSH 附加元件內
mkdir -p /config/packages /config/www/hermes /media/hermes /config/python_scripts
touch /config/customize.yaml /config/secrets.yaml
```

開發者工具 → YAML → **檢查設定** 必須顯示「設定有效」→ 重新啟動。

## 2.9 驗證清單

| # | 檢查 | 指令 / 位置 | 預期 |
|---|---|---|---|
| 1 | VM 固定 IP | VM 主控台 `ha network info` | `192.168.0.11` |
| 2 | 自動啟動 | 重開 Mac mini，等 5 分鐘 | `http://192.168.0.11:8123` 可開 |
| 3 | 不睡 | `pmset -g` | `sleep 0`、`autorestart 1` |
| 4 | Zigbee（SLZB-06） | Z2M 記錄；SLZB-06 網頁 | `Zigbee2MQTT started!`；SLZB-06 顯示 1 個 client |
| 5 | MQTT | Mosquitto 記錄 | `New client connected from ... as zigbee2mqtt` |
| 6 | Samba | Mac mini Finder | `/Volumes/config` 可寫入 |
| 7 | 設定有效 | 開發者工具 → YAML | 設定有效 |
| 8 | 兩位使用者 | 設定 → 人員 | allen（擁有者）、ann |
| 9 | 區域 | 設定 → 區域 | 6 個 |
| 10 | 快照一次 | 設定 → 系統 → 備份 → 立即備份 | 成功 |

全部通過 → 進 03 章。
