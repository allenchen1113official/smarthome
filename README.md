# Allen & Ann 智慧家庭（青鳥 · 台灣藍鵲 BlueMagpie）

Home Assistant + OpenClaw 本地語音 + Hermes AI 管家；Mac mini M4 主節點、HA Black 熱備。

- 建置手冊：`docs/SOP/README.md`（成品網頁 `docs/SOP/sop.html`）
- 一鍵部署：`bluemagpie/`（Docker，跨平台，後台 :9000）
- 設計文件：`design/`；規格：`specs/`；憲章：`.specify/memory/constitution.md`

## 三條不可妥協的原則

| | 原則 | 落實 |
|---|---|---|
| 1 | 系統在地執行，機敏資料不外洩 | STT/LLM/TTS 全本地；雲端 LLM 選配且預設關閉、只送文字；感測與用電資料不上雲 |
| 2 | 金鑰、機敏資料不推上 GitHub | `.env`/`config/`/`data/`/`backups/` 已 git-ignore；推送前 `python3 tools/check_secrets.py` 須 0 findings |
| 3 | 節能省碳為最高目標，由**一個** AI 助理決策 | Hermes 節能管家守門所有空調/燈光/家電動作（`docs/SOP/13`）；預設 eco；每日用電與碳排報告 |

```bash
git config core.hooksPath .githooks     # 啟用推送前金鑰掃描
```
