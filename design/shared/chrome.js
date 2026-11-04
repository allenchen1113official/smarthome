// Top bar + theme toggle, mounted on every page.
(function () {
  const PAGES = [
    { href: "index.html", label: "總覽 Overview" },
    { href: "topology.html", label: "網路拓樸 Topology" },
    { href: "scenes.html", label: "35 場景 Scenes" },
    { href: "openclaw.html", label: "OpenClaw 架構" },
    { href: "hermes.html", label: "Hermes Agent" },
    { href: "sop.html", label: "建置手冊 SOP" },
  ];

  function getTheme() {
    return localStorage.getItem("aa-theme") || "light";
  }
  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("aa-theme", t);
  }
  setTheme(getTheme());

  function renderTopbar(currentHref) {
    const here = (currentHref || location.pathname.split("/").pop() || "index.html").toLowerCase();
    const bar = document.createElement("header");
    bar.className = "topbar";
    bar.innerHTML = `
      <div class="brand"><div class="dot"></div><span>Allen &amp; Ann · Smart Home</span></div>
      <nav>
        ${PAGES.map(p => {
          const cur = here.endsWith(p.href.toLowerCase()) ? ' aria-current="page"' : "";
          return `<a href="${p.href}"${cur}>${p.label}</a>`;
        }).join("")}
      </nav>
      <div class="spacer"></div>
      <span class="pill"><span class="live"></span>Mac mini M4 · 在線</span>
      <button class="theme-toggle" aria-label="切換主題">
        <span class="sun">☀</span><span class="moon">☾</span>
      </button>
    `;
    document.body.prepend(bar);
    bar.querySelector(".theme-toggle").addEventListener("click", () => {
      setTheme(getTheme() === "light" ? "dark" : "light");
    });
  }

  function renderFooter() {
    const f = document.createElement("footer");
    f.className = "footer-meta";
    f.innerHTML = `
      <div>Allen &amp; Ann 智慧家庭規劃 · OpenClaw Local AI · Home Assistant · 設計於 ${new Date().getFullYear()}</div>
      <div style="margin-top:6px;opacity:.7;">CHT 100M/40M · DuckDNS: <code>AllenandAnn.duckdns.org</code> · 22 Hue · 5 AC · 2 Curtain · 1 Robot</div>
    `;
    document.body.appendChild(f);
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderTopbar();
    renderFooter();
  });
})();
