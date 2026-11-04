# -*- coding: utf-8 -*-
"""把 docs/SOP/*.md 組成單一成品網頁 sop.html（沿用 design/shared/tokens.css 的設計 token）"""
import os, re, base64, html, markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CH = [
    ("README.md", "手冊首頁", "📘"),
    ("00-總覽與建置路線圖.md", "00 總覽與路線圖", "🗺️"),
    ("01-網路拓樸實作.md", "01 網路拓樸實作", "📡"),
    ("02-Mac-mini-M4-HAOS-安裝.md", "02 Mac mini + HAOS", "🖥️"),
    ("03-設備整合.md", "03 設備整合", "🔌"),
    ("04-OpenClaw-本地語音管線.md", "04 OpenClaw 語音管線", "🎙️"),
    ("05-Hermes-Agent-建置.md", "05 Hermes Agent", "⚡"),
    ("06-35情境逐一建置.md", "06 35 情境建置", "🎬"),
    ("07-備援備份與遠端存取.md", "07 備援與遠端", "🛟"),
    ("08-驗收測試與故障排除.md", "08 驗收與排除", "✅"),
    ("09-青鳥一鍵部署.md", "09 青鳥一鍵部署", "🐦"),
    ("10-LINE-Telegram-遠端控制介面.md", "10 LINE / Telegram 遠端控制", "💬"),
    ("11-雙節點安裝範例-負載均衡.md", "11 雙節點負載均衡範例", "⚖️"),
    ("12-儀表板建置.md", "12 儀表板建置", "📟"),
    ("A-附錄-總表.md", "附錄 A 總表", "📎"),
]
SCENE_CAT = {}
for n in range(1, 7): SCENE_CAT[n] = "morning"
for n in range(7, 13): SCENE_CAT[n] = "evening"
for n in range(13, 19): SCENE_CAT[n] = "sleep"
for n in range(19, 25): SCENE_CAT[n] = "home"
for n in range(25, 31): SCENE_CAT[n] = "secure"
for n in range(31, 36): SCENE_CAT[n] = "hermes"
CAT_NAME = {"morning": "晨間與通勤", "evening": "下班與休憩", "sleep": "輪班與深度睡眠", "home": "家電與維護", "secure": "安全與 AI 管家", "hermes": "Hermes 主導"}

md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists"], extension_configs={"toc": {"toc_depth": "2-3", "slugify": lambda v, s: re.sub(r"[^\w一-鿿.-]+", "-", v).strip("-").lower()}})

with open(os.path.join(ROOT, "assets", "topology.png"), "rb") as f:
    TOPO = "data:image/png;base64," + base64.b64encode(f.read()).decode()

sections, nav, scene_cards = [], [], []
for i, (fn, label, ico) in enumerate(CH):
    sid = f"ch{i}"
    with open(os.path.join(ROOT, fn), encoding="utf-8") as f:
        src = f.read()
    # 相對連結改成頁內錨點
    for j, (fn2, _, _) in enumerate(CH):
        src = src.replace(f"]({fn2})", f"](#ch{j})")
    # mermaid 區塊 → 已渲染圖 + 可展開原始碼
    src = re.sub(r"```mermaid\n(.*?)```", lambda m: f'<figure class="topo"><img src="{TOPO}" alt="五層網路拓樸圖"><figcaption>五層網路拓樸（assets/topology.png）</figcaption></figure>\n<details><summary>Mermaid 原始碼</summary>\n\n```text\n{m.group(1)}```\n</details>', src, flags=re.S)
    # Siri 捷徑截圖：assets/siri/siri-NN.png 存在時，把表格內的 siri-NN 代碼換成縮圖
    SIRI_DIR = os.path.join(ROOT, "assets", "siri")
    def siri_img(m):
        p = os.path.join(SIRI_DIR, f"{m.group(1)}.png")
        if os.path.exists(p):
            with open(p, "rb") as f:
                data = "data:image/png;base64," + base64.b64encode(f.read()).decode()
            return f'<a class="siri-shot" href="{data}" target="_blank"><img src="{data}" alt="{m.group(1)}" loading="lazy"></a>'
        return f'<span class="siri-ph" title="尚無截圖：放到 assets/siri/{m.group(1)}.png 後重建">📷 {m.group(1)}</span>'
    src = re.sub(r"\| (siri-\d{2}) \|$", lambda m: "| " + siri_img(m) + " |", src, flags=re.M)
    md.reset()
    body = md.convert(src)
    # 情境標題加上類別色與錨點
    def scene_h(m):
        n = int(m.group(1)); cat = SCENE_CAT.get(n, "home")
        scene_cards.append((n, cat, m.group(2)))
        return f'<h3 id="s{n:02d}" class="scene-h" data-cat="{cat}"><span class="scene-num">{n:02d}</span>{m.group(2)}</h3>'
    body = re.sub(r'<h3 id="[^"]*">情境 (\d{2}) · (.*?)</h3>', scene_h, body)
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    body = body.replace("[ ]", '<input type="checkbox" class="chk">')
    body = body.replace("<pre><code", '<pre class="code"><button class="copy" type="button" aria-label="複製">複製</button><code')
    sections.append(f'<section id="{sid}" class="chapter"><div class="eyebrow">{ico} {html.escape(label)}</div>{body}</section>')
    # 子目錄（h2）
    h2s = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body)
    sub = "".join(f'<a href="#{a}">{re.sub("<.*?>","",t)}</a>' for a, t in h2s[:12])
    nav.append(f'<div class="nav-ch"><a class="nav-top" href="#{sid}"><span>{ico}</span>{html.escape(label)}</a><div class="nav-sub">{sub}</div></div>')

grid = "".join(f'<a class="sc" data-cat="{c}" href="#s{n:02d}"><b>{n:02d}</b><span>{html.escape(t)}</span></a>' for n, c, t in scene_cards)
filters = "".join(f'<button type="button" class="f" data-f="{k}">{v}</button>' for k, v in CAT_NAME.items())

CSS = r"""
:root{
  --font-sans:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang TC","Noto Sans TC","Helvetica Neue",Helvetica,Arial,sans-serif;
  --font-mono:"SF Mono",ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace;
  --bg:oklch(98.5% 0.005 80);--bg-elev:oklch(100% 0 0);--bg-tint:oklch(96% 0.008 80);
  --line:oklch(90% 0.006 80);--line-soft:oklch(94% 0.005 80);
  --ink:oklch(20% 0.01 80);--ink-2:oklch(40% 0.012 80);--ink-3:oklch(58% 0.012 80);--ink-4:oklch(72% 0.01 80);
  --accent:oklch(60% 0.14 250);--warn:oklch(70% 0.15 60);--warn-bg:oklch(96% 0.05 75);
  --c-morning:oklch(74% 0.12 75);--c-evening:oklch(74% 0.12 290);--c-sleep:oklch(74% 0.12 250);--c-home:oklch(74% 0.12 165);--c-secure:oklch(74% 0.12 25);--c-hermes:oklch(70% 0.14 330);
  --c-morning-bg:oklch(96% 0.04 75);--c-evening-bg:oklch(96% 0.04 290);--c-sleep-bg:oklch(96% 0.04 250);--c-home-bg:oklch(96% 0.04 165);--c-secure-bg:oklch(96% 0.04 25);--c-hermes-bg:oklch(96% 0.04 330);
  --code-bg:oklch(24% 0.012 260);--code-ink:oklch(92% 0.01 80);
  --shadow-2:0 1px 2px oklch(20% 0.01 80 / .06),0 8px 24px -8px oklch(20% 0.01 80 / .08),0 0 0 1px oklch(20% 0.01 80 / .05);
  --radius-sm:10px;--radius-md:14px;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:oklch(18% 0.008 260);--bg-elev:oklch(22% 0.01 260);--bg-tint:oklch(25% 0.012 260);--line:oklch(32% 0.014 260);--line-soft:oklch(28% 0.012 260);
  --ink:oklch(96% 0.005 80);--ink-2:oklch(82% 0.008 80);--ink-3:oklch(64% 0.01 80);--ink-4:oklch(46% 0.012 80);--accent:oklch(74% 0.12 250);--warn-bg:oklch(30% 0.05 75);
  --c-morning-bg:oklch(28% 0.04 75);--c-evening-bg:oklch(28% 0.04 290);--c-sleep-bg:oklch(28% 0.04 250);--c-home-bg:oklch(28% 0.04 165);--c-secure-bg:oklch(28% 0.04 25);--c-hermes-bg:oklch(28% 0.04 330);
  --code-bg:oklch(14% 0.01 260);--shadow-2:0 1px 2px oklch(0% 0 0/.35),0 12px 28px -10px oklch(0% 0 0/.55),0 0 0 1px oklch(100% 0 0/.07);color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:oklch(18% 0.008 260);--bg-elev:oklch(22% 0.01 260);--bg-tint:oklch(25% 0.012 260);--line:oklch(32% 0.014 260);--line-soft:oklch(28% 0.012 260);
  --ink:oklch(96% 0.005 80);--ink-2:oklch(82% 0.008 80);--ink-3:oklch(64% 0.01 80);--ink-4:oklch(46% 0.012 80);--accent:oklch(74% 0.12 250);--warn-bg:oklch(30% 0.05 75);
  --c-morning-bg:oklch(28% 0.04 75);--c-evening-bg:oklch(28% 0.04 290);--c-sleep-bg:oklch(28% 0.04 250);--c-home-bg:oklch(28% 0.04 165);--c-secure-bg:oklch(28% 0.04 25);--c-hermes-bg:oklch(28% 0.04 330);
  --code-bg:oklch(14% 0.01 260);--shadow-2:0 1px 2px oklch(0% 0 0/.35),0 12px 28px -10px oklch(0% 0 0/.55),0 0 0 1px oklch(100% 0 0/.07);color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:72px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;font-family:var(--font-sans);background:var(--bg);color:var(--ink);line-height:1.65;-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg-elev)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:9;background:color-mix(in oklab,var(--bg-elev) 88%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:10px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.top .brand{font-weight:700;letter-spacing:.01em}.top .brand small{color:var(--ink-3);font-weight:500;margin-left:8px;font-size:12px}
.top .sp{flex:1}
.btn{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--bg-elev);color:var(--ink-2);border-radius:999px;padding:6px 12px;cursor:pointer}
.btn:hover{border-color:var(--ink-4)}.btn:focus-visible,.copy:focus-visible,.f:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.menu{display:none}
.wrap{display:grid;grid-template-columns:268px minmax(0,1fr);gap:40px;max-width:1240px;margin:0 auto;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 80px}
nav.side{position:sticky;top:76px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;font-size:13px;padding-right:6px}
.nav-ch{margin-bottom:6px}.nav-top{display:flex;gap:8px;align-items:center;padding:6px 10px;border-radius:8px;color:var(--ink);font-weight:600}
.nav-top:hover,.nav-top.cur{background:var(--bg-tint);text-decoration:none}
.nav-sub{display:none;flex-direction:column;padding:2px 0 6px 30px}.nav-ch.open .nav-sub{display:flex}
.nav-sub a{color:var(--ink-3);padding:3px 0;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.nav-sub a:hover{color:var(--ink)}
main{min-width:0}
.hero{padding:8px 0 28px;border-bottom:1px solid var(--line);margin-bottom:28px}
.hero h1{font-size:clamp(26px,3.6vw,40px);line-height:1.15;margin:0 0 10px;letter-spacing:-.01em;text-wrap:balance}
.hero p{color:var(--ink-2);max-width:62ch;margin:0 0 18px}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--bg-elev);border:1px solid var(--line);border-radius:var(--radius-sm);padding:8px 14px;font-size:13px;color:var(--ink-2)}
.stat b{display:block;font-size:20px;color:var(--ink);font-variant-numeric:tabular-nums}
.scenes{margin:22px 0 0}.scenes h2{font-size:15px;margin:0 0 10px}
.filters{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.f{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--bg-elev);color:var(--ink-2);border-radius:999px;padding:4px 10px;cursor:pointer}
.f[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.sc{display:flex;gap:8px;align-items:baseline;padding:8px 10px;border-radius:var(--radius-sm);background:var(--bg-elev);border:1px solid var(--line);border-left:4px solid var(--cat);color:var(--ink);font-size:13px;min-width:0}
.sc:hover{text-decoration:none;background:var(--bg-tint)}.sc b{font-family:var(--font-mono);font-size:12px;color:var(--ink-3)}.sc span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc.hide{display:none}
[data-cat="morning"]{--cat:var(--c-morning);--cat-bg:var(--c-morning-bg)}[data-cat="evening"]{--cat:var(--c-evening);--cat-bg:var(--c-evening-bg)}
[data-cat="sleep"]{--cat:var(--c-sleep);--cat-bg:var(--c-sleep-bg)}[data-cat="home"]{--cat:var(--c-home);--cat-bg:var(--c-home-bg)}
[data-cat="secure"]{--cat:var(--c-secure);--cat-bg:var(--c-secure-bg)}[data-cat="hermes"]{--cat:var(--c-hermes);--cat-bg:var(--c-hermes-bg)}
.chapter{padding:34px 0;border-top:1px solid var(--line)}.chapter:first-of-type{border-top:0;padding-top:0}
.eyebrow{font-family:var(--font-mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin-bottom:6px}
.chapter h1{font-size:clamp(22px,3vw,30px);margin:0 0 14px;letter-spacing:-.01em;text-wrap:balance}
.chapter h2{font-size:19px;margin:38px 0 12px;padding-top:4px;text-wrap:balance}
.chapter h3{font-size:16px;margin:26px 0 8px}.chapter h4{font-size:14px;margin:18px 0 6px;color:var(--ink-2)}
.chapter p,.chapter li{max-width:78ch}.chapter p{margin:0 0 12px}
.chapter blockquote{margin:0 0 18px;padding:12px 16px;border-left:3px solid var(--accent);background:var(--bg-tint);border-radius:0 var(--radius-sm) var(--radius-sm) 0;color:var(--ink-2)}
.chapter blockquote p{margin:0 0 6px}.chapter blockquote p:last-child{margin:0}
.chapter ul,.chapter ol{padding-left:1.4em;margin:0 0 14px}.chapter li{margin:3px 0}
.chapter code{font-family:var(--font-mono);font-size:.86em;background:var(--bg-tint);border:1px solid var(--line-soft);border-radius:5px;padding:1px 5px;word-break:break-word}
pre.code{position:relative;background:var(--code-bg);color:var(--code-ink);border-radius:var(--radius-md);padding:14px 16px;overflow-x:auto;margin:0 0 18px;font-size:12.5px;line-height:1.55}
pre.code code{background:none;border:0;padding:0;color:inherit;font-size:inherit;word-break:normal}
.copy{position:absolute;top:8px;right:8px;font:inherit;font-size:11px;border:1px solid oklch(100% 0 0/.2);background:oklch(100% 0 0/.08);color:var(--code-ink);border-radius:6px;padding:3px 8px;cursor:pointer}
.copy:hover{background:oklch(100% 0 0/.16)}
.tbl{overflow-x:auto;margin:0 0 18px;border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--bg-elev)}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:8px 11px;border-bottom:1px solid var(--line-soft);text-align:left;vertical-align:top}
th{background:var(--bg-tint);font-weight:600;color:var(--ink-2);white-space:nowrap}tr:last-child td{border-bottom:0}td code{white-space:nowrap}
.topo{margin:0 0 18px}.topo img{max-width:100%;border-radius:var(--radius-md);border:1px solid var(--line);background:#fff}.topo figcaption{font-size:12px;color:var(--ink-3);margin-top:6px}
details{margin:0 0 18px}summary{cursor:pointer;color:var(--ink-2);font-size:13px}
.scene-h{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:var(--radius-sm);background:var(--cat-bg);border-left:4px solid var(--cat);margin-top:40px!important}
.scene-num{font-family:var(--font-mono);font-size:13px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.chk{width:15px;height:15px;vertical-align:-2px;margin-right:4px;accent-color:var(--accent)}
.siri-shot img{width:84px;border-radius:8px;border:1px solid var(--line);display:block}.siri-ph{font-size:11px;color:var(--ink-3);white-space:nowrap;border:1px dashed var(--line);border-radius:6px;padding:2px 6px}
hr{border:0;border-top:1px solid var(--line);margin:28px 0}
.toast{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:999px;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.on{opacity:1}
@media (max-width:860px){
  .wrap{grid-template-columns:1fr;gap:16px}
  nav.side{position:fixed;inset:calc(54px + env(safe-area-inset-top,0px)) 0 0 0;z-index:8;background:var(--bg-elev);max-height:none;padding:14px max(16px,env(safe-area-inset-left,0px)) 40px;display:none}
  nav.side.open{display:block}.menu{display:inline-block}
}
"""

JS = r"""
(function(){
  var root=document.documentElement;
  try{var t=localStorage.getItem('sop-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}
  document.getElementById('theme').addEventListener('click',function(){
    var dark=root.getAttribute('data-theme')==='dark'||(!root.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches);
    var n=dark?'light':'dark';root.setAttribute('data-theme',n);try{localStorage.setItem('sop-theme',n);}catch(e){}
  });
  var side=document.getElementById('side');
  document.getElementById('menu').addEventListener('click',function(){side.classList.toggle('open');});
  side.addEventListener('click',function(e){if(e.target.tagName==='A'&&innerWidth<=860)side.classList.remove('open');});
  var toast=document.getElementById('toast');function say(m){toast.textContent=m;toast.classList.add('on');setTimeout(function(){toast.classList.remove('on');},1400);}
  document.querySelectorAll('.copy').forEach(function(b){b.addEventListener('click',function(){
    var code=b.parentNode.querySelector('code').innerText;
    function fb(){var r=document.createRange();r.selectNodeContents(b.parentNode.querySelector('code'));var s=getSelection();s.removeAllRanges();s.addRange(r);say('已選取，請按 ⌘C');}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(code).then(function(){say('已複製');},fb);}else fb();
  });});
  document.querySelectorAll('.f').forEach(function(f){f.addEventListener('click',function(){
    var on=f.getAttribute('aria-pressed')==='true';
    document.querySelectorAll('.f').forEach(function(x){x.setAttribute('aria-pressed','false');});
    f.setAttribute('aria-pressed',on?'false':'true');var k=on?null:f.dataset.f;
    document.querySelectorAll('.sc').forEach(function(c){c.classList.toggle('hide',!!k&&c.dataset.cat!==k);});
  });});
  var tops=[].slice.call(document.querySelectorAll('.nav-top'));var chs=tops.map(function(a){return document.querySelector(a.getAttribute('href'));});
  function spy(){var y=scrollY+120,i=0;chs.forEach(function(c,k){if(c&&c.offsetTop<=y)i=k;});
    tops.forEach(function(a,k){a.classList.toggle('cur',k===i);a.parentNode.classList.toggle('open',k===i);});}
  addEventListener('scroll',spy,{passive:true});spy();
  if(location.hash){var el=document.querySelector(location.hash);if(el)setTimeout(function(){el.scrollIntoView();},50);}
})();
"""

BODY = f"""<title>Allen & Ann 智慧家庭建置手冊</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{CSS}</style>
<header class="top">
  <button class="btn menu" id="menu" type="button" aria-label="目錄">☰ 目錄</button>
  <div class="brand">Allen & Ann 智慧家庭建置手冊<small>SOP v1.4 · 2026-11-05</small></div>
  <div class="sp"></div>
  <a class="btn" href="#s01">35 情境</a>
  <button class="btn" id="theme" type="button" aria-label="切換深淺色">◐ 主題</button>
</header>
<div class="wrap">
  <nav class="side" id="side" aria-label="章節">{''.join(nav)}</nav>
  <main>
    <div class="hero">
      <h1>從無到有：Mac mini M4 × Home Assistant × OpenClaw × Hermes</h1>
      <p>依 <code>design/</code> 規劃文件逐章實作的新手建置手冊：網路拓樸、HAOS 虛擬機、設備整合、本地語音管線、Hermes 管家，以及 35 個自動化情境的完整 YAML 與驗收步驟。</p>
      <div class="stats">
        <div class="stat"><b>14</b>章</div><div class="stat"><b>35</b>情境</div><div class="stat"><b>54</b>HA 自動化</div><div class="stat"><b>14</b>Hermes 工具</div><div class="stat"><b>6</b>週路線</div>
      </div>
      <div class="scenes">
        <h2>情境索引</h2>
        <div class="filters">{filters}</div>
        <div class="grid">{grid}</div>
      </div>
    </div>
    {''.join(sections)}
  </main>
</div>
<div class="toast" id="toast" role="status"></div>
<script>{JS}</script>
"""

with open(os.path.join(ROOT, "sop.html"), "w", encoding="utf-8") as f:
    f.write(BODY)
with open(os.path.join(ROOT, "sop.full.html"), "w", encoding="utf-8") as f:
    f.write('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' + BODY.replace("<style>", "</head>\n<body>\n<style>", 1).replace("<meta name=\"claude:viewport-fit-sides\" content=\"cover\">\n", "") + "\n</body></html>")
print("ok", len(BODY), "chars;", len(scene_cards), "scenes")
