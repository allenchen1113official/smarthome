# 拓樸圖設計準則（topology-canvas.html）

**Layered Clarity** — 一張工程圖應該像一本精心校對的技術年鑑：每一層是一條帶狀的「地層」，從外部網路沉降到使用者介面；資訊靠位置與連線樣式傳達，文字只做標籤。

- **紙感底色 + 低飽和五層色**：`#f6f4ee` 底、40 px 細格；五層各一個低飽和主色（靛／青／赭／綠／酒紅），只用於帶狀底、節點左色條與圖示圓底，正文一律墨色。
- **節點三行制**：標題（Inter/Noto Sans CJK 600）、位址（JetBrains Mono，層色）、兩到三行說明（11 px 墨灰）。白卡、12 px 圓角、極淺陰影；不用漸層與 3D。
- **連線即語意**：有線實線靛藍、WiFi 虛線青、Zigbee 點線赭、VIP 實線酒紅、邏輯／備份／接手長虛線灰；全部正交折線，匯流排共用一條幹線，標籤放在垂直落線中點的白底膠囊。
- **通道規劃**：層與層之間留 30–50 px 水平通道，各走一種線型；左右各留一條垂直通道給跨層回連。節點之間至少 60 px 空隙，任何標籤不壓節點。
- **輸出**：以 Playwright `deviceScaleFactor: 2` 截 1800×1240 → 3600×2480 PNG；改內容只改 `node(...)` 與 `edge(...)` 宣告，重跑即可。

```bash
node -e "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1800,height:1240},deviceScaleFactor:2});await p.goto('file://'+process.cwd()+'/topology-canvas.html');await p.waitForTimeout(1200);await p.screenshot({path:'topology.png',clip:{x:0,y:0,width:1800,height:1240}});await b.close()})()"
```
