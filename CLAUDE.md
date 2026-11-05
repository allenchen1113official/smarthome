<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# Allen & Ann 智慧家庭 — 專案守則（摘要；全文 `.specify/memory/constitution.md` v1.1.0）

1. **在地執行、機敏資料不外洩**：語音/LLM 預設全本地（Ollama）；雲端 LLM 只能選配、預設關閉、只送文字。在家狀態、睡眠、用電、語音文字只存 HA 與 Hermes 本地 DB。
2. **金鑰不進 GitHub**：只放 `secrets.yaml` / `bluemagpie/.env` / launchd env；推送前 `python3 tools/check_secrets.py` 必須 0 findings（`git config core.hooksPath .githooks` 自動執行）。手冊範例一律用 `xai-...`、`<token>` 佔位。
3. **節能省碳是最高目標，且只由一個 AI 助理決策**：所有空調/燈光/家電計畫先經 Hermes `energy.clamp`（只收緊不放寬）；預設 `eco`；HA 只做量測與反射動作；新情境必須寫明 eco 模式行為（`docs/SOP/13`）。

語言：繁體中文；日期以台北時間（UTC+8）為準。
