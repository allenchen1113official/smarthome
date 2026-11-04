# Hermes Agent v0.1（骨架）

Allen & Ann 智慧家庭的任務編排層：把 Llama 3 的自然語意轉成「可驗證、可重試、可回滾」的 HA 服務呼叫。
對應規格：`design/hermes.html`（v0.3 規格的 v0.1 實作）。完整安裝步驟見 `docs/SOP/05-Hermes-Agent-建置.md`。

```
hermes/
├── config/
│   ├── hermes.yaml        主設定（HA/Ollama 位址、區域實體對照、別名）
│   ├── policy.yaml        權限 scope、confirm_all、quiet hours、never 清單
│   ├── market.yaml        自選股、掃描規則、告警規則、模擬單
│   └── tools/*.yaml       14 個工具的精簡 schema（注入 LLM system prompt）
├── hermes/
│   ├── app.py             FastAPI：Ollama 相容 /api/chat（給 HA）、/v1/command、/v1/jobs/screen、/v1/alerts/check
│   ├── orchestrator.py    PARSE→GUARD→CONFIRM→DISPATCH→RETRY→SETTLE，fast lane，反向補償
│   ├── llm.py             Ollama 呼叫與上下文注入
│   ├── tools.py           工具實作（全部經 HA 服務）、快照/還原
│   ├── policy.py          scope / 確認 / 深夜限制
│   ├── memory.py          SQLite：session/pref/alias/holding/paper_orders/snapshot/daily
│   ├── market.py          TWSE 報價、指標、掃描圖卡、盤中告警
│   ├── textnorm.py        簡→繁、數字→中文（給 Piper）
│   └── ha.py              HA REST + WebSocket world model
├── requirements.txt
└── com.allenann.hermes.plist   launchd 常駐
```

快速啟動（Mac mini）：
```bash
cd ~/openclaw && source venv/bin/activate && pip install -r hermes/requirements.txt
export HERMES_HA_TOKEN='<HA 長效 token>'
cd hermes && uvicorn hermes.app:app --host 0.0.0.0 --port 8800
curl -s localhost:8800/v1/health
```
