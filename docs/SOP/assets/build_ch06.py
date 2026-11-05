# -*- coding: utf-8 -*-
"""由 ha-config/packages/*.yaml 與下方情境中繼資料組出 06-35情境逐一建置.md（維護時改這裡再重新產生）"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "ha-config", "packages")
OUT = os.path.join(HERE, "..", "06-35情境逐一建置.md")

CATS = {
    "A": ("晨間與通勤", "01–06", "第 3 週"),
    "B": ("下班與休憩", "07–12", "第 3 週"),
    "C": ("輪班與深度睡眠", "13–18", "第 4 週"),
    "D": ("家電與維護", "19–24", "第 4 週"),
    "E": ("安全與 AI 管家", "25–30", "第 4–5 週"),
    "F": ("Hermes 主導", "31–35", "第 5 週"),
}

# n, cat, file, title, who, purpose, prereq(list), devices(list), trigger, cond, action, test(list), override, offline, spec
S = [
 (1,"A","s01_morning_wakeup.yaml","溫柔喚醒","Allen / Ann",
  "依各自喚醒時間，主臥 Hue 模擬日出並把窗簾開 20%，取代鬧鐘的突兀感。",
  ["Hue 場景 `Sunrise`（主臥）已在 Hue App 建好 → HA 顯示為 `scene.master_sunrise`","`cover.bedroom_curtain` 已校正行程","`input_datetime.allen_wake / ann_wake`、`input_select.*_shift`（s00）"],
  ["Hue 主臥 ×4","Aqara 主臥窗簾"],
  "時間 = `input_datetime.allen_wake`（Allen，平日、早班）／`ann_wake`（Ann，依班別）",
  "本人在家；Allen 為 morning 班且平日；Ann 班別非 off",
  "開 Sunrise 場景 → 窗簾 20% → 關閉睡眠模式 → 送出 `allenann_wakeup` 事件（給 02）",
  ["把 `input_datetime.allen_wake` 改成 2 分鐘後，等待觸發","確認主臥燈由暗漸亮、窗簾開到 20%","開發者工具 → 事件 監聽 `allenann_wakeup` 有收到","把 `allen_shift` 切 off 再試，應不觸發"],
  "儀表板關 `input_boolean.s01_enabled`；或在主臥 Dimmer 按「關」即可關燈",
  "窗簾離線時 HA 會記錄錯誤但燈光照常（動作彼此獨立）",
  "specs/001-morning-wake-up"),
 (2,"A","s02_weather_briefing.yaml","天氣預報","Allen / Ann",
  "喚醒 5 分鐘後由 HomePod 播報今日天氣、降雨機率、帶傘與高溫提醒、空品。",
  ["`weather.home`（Met.no）可用","`tts.piper` 與 HomePod 已能播報（04 章）","選配 `sensor.aqi_home`"],
  ["HomePod / HomePod mini","Piper TTS"],
  "事件 `allenann_wakeup`（由 01 送出）",
  "02 啟用",
  "等 5 分鐘 → `weather.get_forecasts` 取今日 → 組句 → `script.say`（Ann 用主臥 mini）",
  ["開發者工具 → 動作 執行 `script.weather_briefing`，HomePod 應播出完整句子","把 `rain` 模擬成 80（暫改模板）確認有「記得帶傘」","深夜執行應以 20% 音量播"],
  "`script.weather_briefing` 可從儀表板手動按；關 `s02_enabled` 停用",
  "天氣整合不可用時模板會出錯 → 自動化記錄錯誤、不播報；建議加 `continue_on_error`",
  "specs/003-weather-forecast"),
 (3,"A","s03_shift_mode.yaml","輪班模式","Ann",
  "Ann 切到早班時，喚醒時段客廳打 5000K 白光提神；任何班別切換自動更新喚醒時間並通知兩人。",
  ["`input_select.ann_shift`（day/evening/night/off）","客廳燈群 `light.living_all`"],
  ["Hue 客餐廳 ×10"],
  "`ann_shift` 變成 day，或到達 `ann_wake`",
  "Ann 在家、05:00–10:00",
  "客廳 100% 5000K；班別改變 → 重設 `ann_wake` 並推播",
  ["把 `ann_shift` 切到 day → 客廳白光，手機收到班別通知","切到 night → `ann_wake` 變 16:00"],
  "手動改 `input_datetime.ann_wake`",
  "無設備依賴問題",
  "specs/008-shift-mode"),
 (4,"A","s04_leave_home.yaml","全屋離家","兩人",
  "兩人都離家 2 分鐘後：全屋關燈、關 Sync Box、三台冷氣關、HomePod 停止、白天啟動掃地機並推播。",
  ["兩支手機 Companion 位置追蹤正常、`person.*` 會變 not_home","`script.ac_set`（s00）","`vacuum.qrevo`"],
  ["Hue 全部","Panasonic ×3","Roborock","HomePod ×2"],
  "`person.allen` 或 `person.ann` 變 not_home 持續 2 分鐘",
  "兩人皆 not_home；訪客模式關",
  "關燈 → 關 Sync Box → 逐台 `script.ac_set off` → 停音樂 → 08–20 且在座充 → 掃地 → 推播",
  ["開發者工具 → 狀態 把 `person.allen`/`person.ann` 都設成 not_home（或兩人真的出門）","2 分鐘後全屋燈與冷氣應關；白天掃地機出動","手機收到「全屋離家」通知","開訪客模式再試，不應觸發"],
  "`input_boolean.guest_mode` 開啟即停用；或關 `s04_enabled`",
  "每個動作 `continue_on_error`，某台冷氣離線不影響其他",
  "specs/004-leave-home-lights-off"),
 (5,"A","s05_door_entry_light.yaml","門鎖連動","兩人",
  "大門打開且玄關照度 < 30 lx → 玄關燈亮（睡眠模式只 20%）；3 分鐘無動作自動關。",
  ["Aqara 門窗感測器 `binary_sensor.front_door`（加購）","`sensor.hallway_illuminance`（Hue Motion 附帶）"],
  ["門窗感測","Hue 玄關"],
  "`front_door` 變 on",
  "照度 < 30",
  "開玄關燈 → 等走廊無動作 3 分鐘（最長 10 分鐘）→ 關",
  ["夜間開門 → 玄關燈亮 70%","白天開門（照度高）不亮","離開玄關 3 分鐘後自動關"],
  "玄關燈實體開關 / App 直接操作；關 `s05_enabled`",
  "照度感測離線 → numeric_state 條件不成立 → 不觸發（安全降級：不會半夜亂亮）",
  "specs/005-arrive-home-lights-on"),
 (6,"A","s06_morning_stock.yaml","晨間股市摘要","Allen",
  "平日 06:35 由 Hermes 取前一日盤後掃描結果，HomePod 播報前 3 檔與一句話理由，結尾免責聲明。",
  ["Hermes 線上（05 章）且前一天 13:35 已跑過掃描（32）","`rest_command.hermes_screen`"],
  ["HomePod","Hermes / Ollama"],
  "06:35",
  "平日、Allen 在家、早班",
  "呼叫 Hermes `/v1/jobs/screen` → 取 `speech` → `script.say`；Hermes 離線改播「管家離線」",
  ["開發者工具 執行 `rest_command.hermes_screen`，回應含 `speech`","手動觸發自動化 → HomePod 播報含「非投資建議」","停掉 Hermes 再觸發 → 播「暫時離線」"],
  "關 `s06_enabled`",
  "Hermes 離線 → 降級播報；行情 API 失敗 → Hermes 回「今天沒有符合條件的」",
  "specs/002-morning-stock-summary"),
 (7,"B","s07_arrival_precool.yaml","返家預熱","Allen / Ann",
  "手機距家 2 km 且朝家方向、室溫 > 26°C → 先開冷氣到舒適溫度；30 分鐘未到家自動關。",
  ["`proximity.home_allen / home_ann`（configuration.yaml snippet）","`sensor.living_temperature / master_temperature`"],
  ["Panasonic 客廳 / 主臥"],
  "`proximity.home_*` 低於 2000 m",
  "方向 towards、本人 not_home、非訪客模式、10–23 點、室溫 > 26",
  "`script.ac_set cool` → 推播 → 等 30 分鐘到家，否則關",
  ["Companion App → 設定 → 感測器 → 強制更新位置，從外面走近家","手機收到「正在為您預冷」","人到家後自動化結束；故意不回家 30 分鐘 → 冷氣關並通知"],
  "關 `s07_enabled`；或直接用 App 關冷氣（之後不會再開，因 mode: single 已結束）",
  "Comfort Cloud 不可用時 `script.ac_set` 自動改 IR",
  "specs/007-smart-ac-control"),
 (8,"B","s08_movie_mode.yaml","影音模式","兩人",
  "Hue Tap 鍵 2 或儀表板開關 → 快照當前狀態、窗簾關、崁燈 10%、Sync Box 開 video 模式；關閉或 3 小時後還原。",
  ["HACS Hue Sync Box 整合（03 章）","`input_boolean.movie_mode`（s00）","Tap 鍵 2 的 `hue_event` id"],
  ["Sync Box","Play 燈條","Hue 客廳 ×10","客廳窗簾"],
  "`hue_event` Tap 鍵 2 短按 → 切換 `movie_mode`；`movie_mode` on/off",
  "08 啟用",
  "on：`scene.create` 快照 → 關窗簾 → 燈 10% → Sync Box on → 3 小時倒數；off：Sync Box off → 還原快照",
  ["按 Tap 鍵 2 → 燈暗、窗簾關、電視同步燈效","再按一次 → 燈與窗簾回原狀","儀表板開關 `movie_mode` 也能切換","開影音模式時 19:00 的晚餐情境不應覆蓋（09 有條件）"],
  "儀表板 `movie_mode` 開關；關 `s08_enabled`",
  "Sync Box 離線 → `continue_on_error`，燈光部分照常",
  "specs/009-movie-mode"),
 (9,"B","s09_dinner_ambience.yaml","晚餐氛圍","兩人",
  "平日 19:00 或 Tap 鍵 3 → 客餐廳 2700K 65% 暖光，10 秒漸變。",
  ["客廳燈群","Tap 鍵 3 id"],
  ["Hue 客餐廳 ×10"],
  "19:00 或 Tap 鍵 3",
  "有人在家、非影音模式",
  "客廳 65% 2700K",
  ["按 Tap 鍵 3 → 10 秒內暖光","影音模式中按 → 無反應"],
  "任何 Hue 開關／App；關 `s09_enabled`",
  "—",
  "—"),
 (10,"B","s10_bathroom.yaml","浴室自動化","兩人",
  "有人進浴室開燈（深夜 15%）；濕度 > 70% 開抽風；濕度 < 60% 且無人 10 分鐘關抽風；無人 5 分鐘關燈。",
  ["Aqara Motion P1 `binary_sensor.bath_motion`、溫濕度 `sensor.bath_humidity`、繼電器 `switch.bath_fan`（加購）","浴室燈 `light.bath_1`（若浴室燈非 Hue，改用繼電器）"],
  ["浴室 PIR","濕度感測","抽風繼電器"],
  "動作 on；濕度 > 70 ×2 分；濕度 < 60 ×10 分",
  "10 啟用",
  "開燈 → 等無人 5 分 → 關；抽風依濕度開關",
  ["進浴室燈亮；出來 5 分鐘後關","洗澡後濕度上升 → 抽風開；約 10–20 分鐘後自動關"],
  "實體牆面開關；關 `s10_enabled`",
  "感測離線 → 不動作；請保留實體開關",
  "—"),
 (11,"B","s11_night_quiet.yaml","深夜靜音","兩人",
  "23:00 把兩顆 HomePod 音量降到 20%；07:00（非睡眠模式）回 40%。`script.say` 也內建同樣限制。",
  ["HomePod 媒體播放器"],
  ["HomePod ×2"],
  "23:00 / 07:00",
  "11 啟用；07:00 需 sleep_mode off",
  "`media_player.volume_set`",
  ["23:00 後對 HomePod 說話，音量明顯變小","07:00 後恢復"],
  "直接轉 HomePod 頂部音量",
  "HomePod 離線 `continue_on_error`",
  "—"),
 (12,"B","s12_post_shower_dry.yaml","洗完澡乾燥","兩人",
  "19:00–02:00 主臥濕度 > 75% 持續 10 分鐘 → 主臥冷氣切除濕 26°C；濕度 < 60% 持續 15 分鐘（最長 2 小時）還原原本狀態。",
  ["`sensor.master_humidity`（Aqara）","`script.ac_set`"],
  ["Panasonic 主臥","Aqara 濕度"],
  "濕度 > 75 ×10 分",
  "19:00–02:00、有人在家",
  "快照 `climate.master` → dry 26 → 等濕度降 → 還原快照",
  ["用加濕器或洗澡讓主臥濕度破 75% 十分鐘 → 冷氣轉除濕","濕度降回後冷氣回到原本模式"],
  "App 直接改冷氣模式；關 `s12_enabled`",
  "雲端不可用走 IR；IR 無法讀回狀態，快照還原以 SmartIR 內部狀態為準",
  "specs/007-smart-ac-control"),
 (13,"C","s13_ann_nap.yaml","女友補眠","Ann",
  "Tap 鍵 1 → 主臥窗簾全閉、主臥燈關、HomePod mini 靜音、睡眠模式開、通知 Allen。",
  ["Tap 鍵 1 id","`cover.bedroom_curtain`"],
  ["Aqara 主臥窗簾","HomePod mini","Hue 主臥 ×4"],
  "`hue_event` Tap 鍵 1 短按",
  "13 啟用",
  "`script.ann_nap`",
  ["按 Tap 鍵 1 → 窗簾關、燈關、`sleep_mode` on、Allen 收到通知","語音「Ann 還在睡嗎」（30）應回「還在補眠」"],
  "關 `sleep_mode`（儀表板）即解除；窗簾可手拉",
  "窗簾離線 `continue_on_error`，其餘照常",
  "specs/008-shift-mode"),
 (14,"C","s14_sleep_nightlight.yaml","睡眠防擾","兩人",
  "睡眠模式或 23:30–06:00 走廊有動作 → 臥室玄關燈 1% 暖光 2 分鐘；睡眠模式開啟時主臥燈與音樂自動關。",
  ["`binary_sensor.hallway_motion`","`light.bedroom_hall_1`"],
  ["Hue Motion 走廊","臥室玄關燈"],
  "走廊動作 on；`sleep_mode` on",
  "睡眠模式或深夜",
  "1% 夜燈 2 分鐘；睡眠模式開 → 關主臥燈/音樂",
  ["開 `sleep_mode` 後在走廊走動 → 1% 微光，2 分鐘後熄","白天走動（非睡眠）不亮"],
  "關 `s14_enabled`",
  "—",
  "specs/006-bedtime-lights-off"),
 (15,"C","s15_bedroom_thermostat.yaml","臥室恆溫","Allen",
  "02:00–06:00 主臥室溫 < 22°C 持續 10 分鐘且冷氣在 cool → 設定溫度 +1（上限 28）。每 30 分鐘再評估。",
  ["`sensor.master_temperature`","`climate.master`"],
  ["Panasonic 主臥","Aqara 溫度"],
  "溫度 < 22 ×10 分；每 30 分鐘",
  "02–06 點、cool 模式、溫度 < 22",
  "`script.ac_set temperature+1`",
  ["把條件暫改為 < 30 測試 → 冷氣溫度 +1，記錄簿有紀錄","還原條件"],
  "App 直接改溫度；關 `s15_enabled`",
  "感測離線 → 不動作",
  "specs/007-smart-ac-control"),
 (16,"C","s16_white_noise.yaml","快速入睡","兩人",
  "Siri 捷徑「白噪音」→ 主臥 HomePod mini 15% 音量播白噪音，20 分鐘後自動停。",
  ["`/config/www/audio/white_noise.mp3`（自備音檔）","`timer.white_noise`（s00）","secrets `white_noise_webhook_id`"],
  ["HomePod mini"],
  "webhook（Siri 捷徑）",
  "16 啟用",
  "`script.white_noise` → 計時 20 分 → 停",
  ["iPhone 捷徑 POST webhook → mini 開始播","20 分鐘後自動停止（可把 timer 暫改 1 分鐘測）"],
  "對 HomePod 說「嘿 Siri 停止」",
  "—",
  "specs/006-bedtime-lights-off"),
 (17,"C","s17_arrival_greeting.yaml","早退晚回判斷","Ann",
  "開門時依班別與時間決定回饋：大夜班 Ann 07–11 回家 → 歡迎語 + 主臥預冷 + 3 分鐘後補眠模式；深夜回家 → 只推播；白天 → 簡單歡迎。10 分鐘內不重複。",
  ["`binary_sensor.front_door`","`script.ann_nap`（13）","`script.say`"],
  ["門窗感測","HomePod","Panasonic 主臥"],
  "大門 on",
  "10 分鐘冷卻",
  "`choose` 依時段分流",
  ["把 `ann_shift` 設 night，早上 8 點開門 → 播歡迎語、主臥冷氣開、3 分鐘後補眠模式","深夜開門 → 無聲音、手機推播"],
  "關 `s17_enabled`",
  "HomePod 離線 → `script.say` 失敗但其餘照常",
  "specs/008-shift-mode"),
 (18,"C","s18_study_room.yaml","次臥工作室","Allen",
  "電腦插座功率 > 30 W 持續 2 分鐘 → 次臥 5000K 100%、室溫 > 27 開冷氣；< 10 W 持續 10 分鐘 → 關燈關冷氣。",
  ["Zigbee 智慧插座 `sensor.second_desk_plug_power`（加購）","`light.second_all`"],
  ["智慧插座","Hue 次臥 ×2","Panasonic 次臥"],
  "功率門檻",
  "18 啟用",
  "Focus 照明 + 空調；關機後關",
  ["開電腦 2 分鐘後燈亮","關機 10 分鐘後燈關"],
  "實體開關；關 `s18_enabled`",
  "插座離線 → 不動作",
  "—"),
 (19,"D","s19_vacuum_yield.yaml","掃地避讓","兩人",
  "清掃中客廳感應器持續 3 分鐘有人 → 暫停 10 分鐘並通知，之後若仍暫停就續掃。",
  ["`binary_sensor.living_motion`","`vacuum.qrevo`"],
  ["Hue Motion 客廳","Roborock"],
  "客廳動作 on ×3 分",
  "掃地機 cleaning",
  "pause → 10 分 → start",
  ["啟動掃地，坐在沙發 3 分鐘 → 掃地機暫停、收到通知","10 分鐘後續掃"],
  "App 直接操作掃地機；關 `s19_enabled`",
  "—",
  "—"),
 (20,"D","s20_energy_watch.yaml","節能監控","兩人",
  "任一冷氣 cool/dry 連續 12 小時 → 推播附「關閉」按鈕；主臥開窗 5 分鐘且冷氣運轉 → 提醒關窗。",
  ["`binary_sensor.master_window`（加購）","Companion 通知動作"],
  ["Panasonic ×3","門窗感測"],
  "冷氣狀態持續 12h；窗戶 on ×5 分",
  "20 啟用",
  "推播（含動作按鈕）→ 按鈕觸發 `script.ac_set off`",
  ["暫改 12h 為 1 分鐘測試 → 收到含「關閉」按鈕通知 → 按下 → 冷氣關","開主臥窗 5 分鐘（冷氣開）→ 提醒"],
  "—",
  "—",
  "specs/007-smart-ac-control"),
 (21,"D","s21_dehumidify.yaml","除濕自動化","兩人",
  "08–22 有人在家、客廳冷氣關著、濕度 > 65% 持續 15 分鐘 → 除濕 26°C；濕度 < 55% 持續 15 分鐘 → 關。",
  ["`sensor.living_humidity`（Aqara）"],
  ["Panasonic 客廳","Aqara 濕度"],
  "濕度門檻（15 分鐘）",
  "時段、在家、冷氣 off / dry",
  "`script.ac_set dry 26` / off",
  ["雨天濕度破 65 → 冷氣除濕；記錄簿有「啟動除濕」","濕度降回 55 以下 → 關"],
  "App 操作；關 `s21_enabled`",
  "雲端不可用走 IR",
  "specs/007-smart-ac-control"),
 (22,"D","s22_vacuum_water.yaml","Qrevo 水箱提醒","兩人",
  "掃地機從 returning 變 docked（清掃完成）→ 計數 +1、HomePod 提醒補水、推播 Allen。",
  ["`counter.vacuum_runs`（s00）"],
  ["Roborock","HomePod"],
  "`vacuum.qrevo` returning → docked",
  "22 啟用",
  "計數 → 播報 → 推播",
  ["跑一次小範圍清掃 → 回充後 HomePod 提醒、手機通知含次數"],
  "關 `s22_enabled`",
  "—",
  "—"),
 (23,"D","s23_nightly_backup.yaml","HA 快照同步副節點","兩人",
  "每晚 03:00 全備（本機 + 副節點 SMB），10 分鐘後推播；每小時 :05 只備設定（含 helpers 狀態）到副節點，讓熱備接手後最多落後 1 小時。只在主節點執行。",
  ["設定 → 系統 → 備份：位置加入 `standby`（//192.168.0.12/backup，07 章）、保留 7 份、加密","`secrets.yaml` 的 `backup_password` 兩台相同","`binary_sensor.is_primary_node`（s00_node）","HA ≥ 2025.1（`backup.create_automatic`）"],
  ["Mac mini","HA Black","SLZB-06"],
  "03:00 全備；每小時 :05 設定備份",
  "23 啟用；小時備只在主節點",
  "`backup.create_automatic` → 推播；`hassio.backup_partial`（config + Z2M + Mosquitto → standby）",
  ["手動觸發全備 → 10 分鐘後手機收到「全備完成」","副節點 Samba `backup` 資料夾出現當日 .tar 與 `hourly_HH.tar`","設定 → 備份 顯示最近成功時間","在副節點上這個自動化不會跑（`is_primary_node` off）"],
  "設定 → 系統 → 備份 → 立即備份",
  "備援機離線 → 本機仍完成備份；推播訊息會顯示時間",
  "constitution §Storage & Backup"),
 (24,"D","s24_consumables.yaml","耗材更換提醒","兩人",
  "每小時若任一冷氣在運轉就把濾網時數 +1，達 500 小時提醒清洗；掃地機每 30 次提醒保養；儀表板按鈕歸零。",
  ["`counter.ac_filter_hours`、`counter.vacuum_runs`（s00）","22 情境負責掃地次數計數"],
  ["Panasonic","Roborock"],
  "每小時整點；計數器門檻",
  "24 啟用",
  "推播；`script.reset_ac_filter` / `reset_vacuum_runs`",
  ["開發者工具把 `counter.ac_filter_hours` 設 499 → 下個整點（冷氣開著）收到提醒","按儀表板「已清洗濾網」→ 歸零"],
  "—",
  "—",
  "—"),
 (25,"E","s25_night_motion_alert.yaml","運動偵測告警","兩人",
  "00:00–05:00 走廊動作或大門開啟，且（睡眠模式中或無人在家）→ 擷取掃地機地圖快照並時效性推播（5 分鐘冷卻）。",
  ["`camera.qrevo_map`（Roborock 整合）","`/media/hermes` 資料夾存在（02 章）"],
  ["Hue Motion 走廊","門窗感測","Roborock 地圖","推播"],
  "走廊動作 / 大門",
  "凌晨、睡眠模式或無人",
  "`camera.snapshot` → `notify.both` 附圖",
  ["開 `sleep_mode`，把時間條件暫改為全天 → 走過走廊 → 兩支手機收到附圖通知","還原時間條件"],
  "關 `s25_enabled`；訪客留宿時關 `sleep_mode` 即不觸發（仍需兩人在家）",
  "相機不可用 `continue_on_error`，通知照送（無圖）",
  "constitution II（安全類需復原程序：見 08 章）"),
 (26,"E","s26_wan_alert.yaml","網路警告","兩人",
  "WAN ping 失敗 2 分鐘 → 白天客廳燈紅閃 3 次 + HA 本機通知；恢復 1 分鐘 → 推播。",
  ["`binary_sensor.wan_ping`（snippet）","`script.flash_lights`（s00）"],
  ["tp-link","Hue 客廳"],
  "`wan_ping` off ×2 分 / on ×1 分",
  "26 啟用",
  "閃紅 → persistent notification；恢復推播",
  ["拔掉路由器 WAN 線 2 分鐘 → 客廳紅閃、HA 畫面出現通知","插回 → 手機收到「網路已恢復」"],
  "關 `s26_enabled`",
  "斷網時推播送不出去是預期行為，所以用燈效 + 本機通知",
  "—"),
 (27,"E","s27_device_offline.yaml","設備離線與主機失聯偵測","兩人",
  "關鍵設備 unavailable 5 分鐘 → 推播；恢復 → 通知 Allen。主機（Mac mini）失聯 5 分鐘的偵測放在備援機 HA Black（07 章）。",
  ["03 章全部整合完成"],
  ["全設備","HA Black"],
  "狀態 → unavailable ×5 分",
  "27 啟用",
  "推播實體名稱",
  ["拔掉 Hue Bridge 網路線 5 分鐘 → 收到離線通知","插回 → 收到恢復通知"],
  "關 `s27_enabled`",
  "—",
  "constitution II"),
 (28,"E","s28_sos.yaml","緊急 SOS","兩人",
  "主臥 Dimmer「關」鍵長按約 5 秒（`repeat` 事件累計 5 次）→ Twilio 簡訊給緊急聯絡人、兩人手機 critical 推播、全屋紅光 10 次、HomePod 最大音量播報。硬體路徑直通，不經 Hermes 確認。",
  ["Twilio（snippet `notify.sms`）或改用其他簡訊服務","Dimmer 鍵 4 的 `hue_event` id","`script.emergency_sos`（s00）"],
  ["Hue Dimmer","SMS","Hue 全部","HomePod ×2"],
  "`hue_event` repeat（計數）",
  "28 啟用",
  "`counter.dimmer_hold` ≥ 5 → `script.emergency_sos`",
  ["先把 `notify.sms` 的號碼改成自己的 → 長按 Dimmer 關鍵 5 秒 → 收到簡訊、推播、紅光、播報","短按不觸發；長按 2 秒放開不觸發（計數重設）","Hue `repeat` 間隔約 1 秒；若 5 秒觸發太快/太慢，調整門檻 5"],
  "關 `s28_enabled`（出國或訪客時）",
  "Twilio 失敗 `continue_on_error` → 仍推播與紅光",
  "constitution II（安全類復原：08 章）"),
 (29,"E","s29_home_arrival_ai.yaml","OpenClaw 全屋情境切換","Allen",
  "說「Allen 回家了」→ Siri 捷徑 → webhook → Hermes：LLM 解析為 Welcome 場景 + 冷氣 24 + 窗簾開（白天）→ 覆誦確認 → 執行 → 回報。Hermes 離線時由純 HA 版 `script.home_arrival` 接手（無確認）。",
  ["04/05 章完成；Siri 捷徑「Allen 回家了」已建","Hue 場景 `scene.living_welcome`"],
  ["OpenClaw","Hermes","全部"],
  "語音（webhook）／Assist",
  "Hermes 線上；29 啟用（fallback 用）",
  "Hermes plan：light.activate_scene → climate.set → cover.set_position（非關鍵）",
  ["對 HomePod 說「嘿 Siri，Allen 回家了」→ HomePod 問「要我開客廳的 Welcome 場景並把客廳冷氣設 24 度…嗎？」","說「好」（或 Assist 打字）→ 燈亮、冷氣開、回報","停掉 Hermes 再說一次 → 純 HA 版直接執行、播「歡迎回家」","tx log 可見 plan 全程"],
  "任何 App/開關；Hermes 12 秒不回答即取消",
  "冷氣沒回應 → Hermes 回滾燈光並說明",
  "design/hermes.html Plan 範例"),
 (30,"E","s30_status_query_ai.yaml","OpenClaw 家電狀態查詢","兩人",
  "說「Ann 還在睡嗎？」→ Hermes fast lane 讀主臥窗簾/動作 → 回「窗簾全閉…還在補眠」；「客廳幾度」同理。Hermes 離線由純 HA 模板回答。",
  ["Hermes world model 已同步（`/v1/health` world_entities > 0）"],
  ["OpenClaw","Hermes","Aqara","TTS"],
  "語音",
  "唯讀，免確認",
  "`home.get_state` → 樣板句",
  ["Tap 鍵 1 進補眠 → 問「Ann 還在睡嗎」→ 回「還在補眠」（~300 ms）","開窗簾 → 再問 → 回「應該起來了」","停 Hermes → 純 HA 版回答"],
  "—",
  "—",
  "design/hermes.html"),
 (31,"F","s31_stock_voice_qa.yaml","股票語音問答","Allen",
  "「2330 現在怎樣？」→ Hermes fast lane 抓 TWSE 報價 + 本地指標 → 「台積電 1085 元，漲 1.2%，站上 20 日均，量能 1.4 倍，RSI 58。非投資建議。」抓不到就明說。",
  ["Hermes 已跑過一次 `/v1/jobs/screen`（有日線）","Siri 捷徑「股票」：聽寫文字 → webhook"],
  ["OpenClaw","Hermes","HomePod"],
  "語音（唯讀、免確認）",
  "`net.egress` 白名單",
  "`market.quote` + `market.indicators` → TTS",
  ["問「2330 現在怎樣」→ 2 秒內回報價","拔網路線再問 → 回「現在拿不到報價…要我五分鐘後再試一次嗎」","儀表板 `binary_sensor.hermes_online` 為 on"],
  "—",
  "API 失敗不編造數字",
  "design/hermes.html 股票模組"),
 (32,"F","s32_closing_card.yaml","收盤圖卡推送","Allen",
  "平日 13:35 呼叫 Hermes 盤後掃描（batch lane，~40 秒）：評分自選股、產出 `/local/hermes/latest.png` 圖卡、推播 Allen、HomePod 播摘要；不足門檻回「今天沒有符合條件的」。",
  ["Mac mini 已掛載 `/Volumes/config`（02 章）→ Hermes `cards_dir`","儀表板加 Picture 卡片 `image: /local/hermes/latest.png`"],
  ["Hermes","客廳平板","推播"],
  "13:35 平日",
  "Hermes 線上",
  "`rest_command.hermes_screen` → 播摘要",
  ["手動觸發 → 約 1 分鐘後手機收到附圖通知、平板圖卡更新","`/config/www/hermes/` 有當日 png"],
  "關 `s32_enabled`",
  "Samba 未掛載 → 無圖卡但仍推文字",
  "design/hermes.html"),
 (33,"F","s33_intraday_alerts.yaml","盤中停損告警","Allen",
  "平日 09:00–13:35 每 5 分鐘呼叫 Hermes 告警檢查：跌破成本 8% → 紅光脈衝 3 次 + 時效性推播 + 語音；突破 20 日高 → 藍光 + 推播；每檔每日最多 2 次；深夜只推播。",
  ["`script.hermes_alert`（s00）","有模擬持股（34）才會有停損告警"],
  ["Hermes","Hue 客廳","Companion"],
  "每 5 分鐘",
  "盤中、Hermes 線上",
  "`rest_command.hermes_alerts` → Hermes 回呼 `script.hermes_alert`",
  ["先用 34 建一筆模擬持股，把 `market.yaml` 停損改成 `cost * 1.5`（必觸發）→ 5 分鐘內紅光 + 推播 + 播報","改回 0.92"],
  "關 `s33_enabled`",
  "—",
  "design/hermes.html"),
 (34,"F","s34_paper_trading.yaml","模擬單與持股記帳","Allen",
  "「幫我模擬買 2330 一張」→ Hermes 覆誦「模擬買進 2330 1000 股，以現價記錄，確認嗎？」→「好」→ 記進 `hermes.db`；不連券商、`broker.place_order` 永久封鎖。HA 以 REST 感測器顯示持股。",
  ["Hermes finance.sim scope"],
  ["Hermes","hermes.db"],
  "語音 + 覆誦確認",
  "finance.sim 必確認",
  "`market.paper_order`",
  ["語音下模擬單 → 確認 → `/v1/holdings` 出現","說「幫我真的下單」→ 被拒","儀表板 `sensor.hermes_paper_holdings` 顯示檔數"],
  "—",
  "—",
  "design/hermes.html"),
 (35,"F","s35_quiet_confirm.yaml","深夜確認改推播","兩人",
  "23:00–07:00 Hermes 不出聲覆誦，改推播附「好／取消」按鈕（按鈕事件由 s00_voice 回傳 Hermes）；Ann 睡眠時主臥全靜音；唯讀與 SOS 例外。另：Hermes 離線 10 分鐘提醒。",
  ["policy.yaml `quiet_hours`","Companion 通知動作"],
  ["Hermes","Companion","HomePod mini"],
  "policy（quiet_hours）",
  "—",
  "推播確認；按鈕 → `rest_command.hermes_command 好/取消`",
  ["深夜（或暫改 Mac 時間）說「客廳燈開」→ 無聲、手機收到含按鈕通知 → 按「好」→ 燈亮","按「取消」→ 不動作","停 Hermes 10 分鐘 → 收到離線提醒"],
  "—",
  "—",
  "design/hermes.html policy.yaml"),
]

def pkg(fn):
    with open(os.path.join(PKG, fn), encoding="utf-8") as f:
        return f.read().rstrip()

out = []
out.append("""# 06 · 35 種情境逐一建置

> 每個情境一個 HA **package**（`ha-config/packages/sXX_*.yaml`），內含它自己的啟停開關 `input_boolean.sXX_enabled`、自動化與腳本。本章每一節的 YAML 與該檔完全相同。
> 先決條件：03 章全部通過；`s00_common.yaml` 與 `s00_voice.yaml` 已放進 `/config/packages/`。情境 29–35 另需 04、05 章。

## 6.0 共通做法

### 安裝一個情境的固定流程

1. 把 `sXX_*.yaml` 複製到 HAOS 的 `/config/packages/`（Samba `\\\\192.168.0.88\\config\\packages`）。
2. 檔內標 ⚠️ 的地方（`hue_event` id、房間 ID）改成你在 03 章記下的值。
3. 開發者工具 → YAML → **檢查設定** → 「設定有效」→ **重新載入所有 YAML 設定**（不用整台重啟）。
4. 設定 → 自動化：確認該情境的自動化出現；開發者工具 → 狀態：`input_boolean.sXX_enabled` 存在。
5. 依該節「測試步驟」逐項打勾；通過後把 `specs/0XX/spec.md` 的 Status 改 **Deployed** 並記錄 as-built 差異（憲章 V）。
6. 把結果填進該節末的「實測紀錄」表（本手冊即工作底稿；網頁版可列印或用 Markdown 直接編輯）。「部分」= 有步驟失敗但不影響主要功能，須在備註寫明哪一步；三次都填完、驗收列打勾，才算 08 章 C 表的「通過」。

### 儀表板（建議）

新增一個「情境總控」頁面，用 Entities 卡片列出 35 個 `input_boolean.sXX_enabled` 加上 `sleep_mode / movie_mode / guest_mode / ann_shift / allen_shift`；再放 `script.reset_ac_filter`、`script.reset_vacuum_runs`、`script.weather_briefing`、`script.home_arrival` 當按鈕；Picture 卡片 `image: /local/hermes/latest.png` 顯示股票圖卡。

```yaml
# 儀表板原始碼範例（Lovelace YAML）
type: entities
title: 情境總控
entities:
  - input_select.allen_shift
  - input_select.ann_shift
  - input_boolean.sleep_mode
  - input_boolean.movie_mode
  - input_boolean.guest_mode
  - type: divider
  - input_boolean.s01_enabled
  - input_boolean.s04_enabled
  - input_boolean.s07_enabled
  - input_boolean.s25_enabled
  - input_boolean.s28_enabled
  - type: divider
  - script.weather_briefing
  - script.reset_ac_filter
  - script.reset_vacuum_runs
```

### 共用 package：s00_common.yaml（先裝）

```yaml
""" + pkg("s00_common.yaml") + """
```

### 共用 package：s00_voice.yaml（語音入口；29–35 與 Siri 捷徑都靠它）

```yaml
""" + pkg("s00_voice.yaml") + """
```

### 共用 package：s00_node.yaml（節點感知；隨備份到副節點，接手後自動啟動 Z2M）

```yaml
""" + pkg("s00_node.yaml") + """
```

### 情境總表

| # | 情境 | 類別 | 對象 | 主要觸發 | 依賴加購 |
|---|---|---|---|---|---|
""")
need = {5:"門窗感測",10:"PIR+濕度+繼電器",12:"溫濕度",15:"溫濕度",17:"門窗感測",18:"智慧插座",20:"門窗感測",21:"溫濕度",25:"門窗感測",28:"Twilio"}
for s in S:
    out.append(f"| {s[0]:02d} | {s[3]} | {CATS[s[1]][0]} | {s[4]} | {s[8]} | {need.get(s[0],'—')} |")

cur = None
for s in S:
    n, cat, fn, title, who, purpose, prereq, devices, trig, cond, act, tests, override, offline, spec = s
    if cat != cur:
        cur = cat
        out.append(f"\n---\n\n## 6.{cat} {CATS[cat][0]}（情境 {CATS[cat][1]}）· 建議 {CATS[cat][2]}\n")
    out.append(f"### 情境 {n:02d} · {title}\n")
    out.append(f"**目的**：{purpose}\n")
    out.append(f"| 項目 | 內容 |\n|---|---|\n| 適用對象 | {who} |\n| 涉及設備 | {'、'.join(devices)} |\n| 觸發 | {trig} |\n| 條件 | {cond} |\n| 動作 | {act} |\n| 手動覆寫 | {override} |\n| 設備離線時 | {offline} |\n| 對應規格 | {spec} |\n")
    out.append("**前置條件**\n")
    for p in prereq: out.append(f"- {p}")
    out.append(f"\n**package：`ha-config/packages/{fn}`**\n\n```yaml\n{pkg(fn)}\n```\n")
    out.append("**測試步驟（全部通過才算完成）**\n")
    for i, t in enumerate(tests, 1): out.append(f"{i}. [ ] {t}")
    out.append(f"\n**實測紀錄（情境 {n:02d}）**\n")
    out.append("| 次 | 日期（台北） | 測試者 | 結果 | as-built 差異 / 備註 |\n|---|---|---|---|---|")
    out.append("| 初測 | ____-__-__ | Allen ☐ Ann ☐ | 通過 ☐ 失敗 ☐ 部分 ☐ | |")
    out.append("| 複測 | ____-__-__ | Allen ☐ Ann ☐ | 通過 ☐ 失敗 ☐ 部分 ☐ | |")
    out.append("| 驗收（08 章 C 表） | ____-__-__ | 兩人 ☐ | 通過 ☐ | spec Status → Deployed ☐ |")
    out.append("")

out.append("""
---

## 6.Z 全部裝完之後

1. 開發者工具 → 狀態 搜尋 `_enabled`：應有 34 個（31 沒有開關）。
2. 設定 → 自動化：共 54 個自動化；全部「已啟用」。
3. 設定 → 系統 → 記錄：沒有 `Invalid config` 或 `Template error`。
4. 進 07 章做備援，再進 08 章做整體驗收。
""")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote", OUT, sum(len(x) for x in out), "chars")
