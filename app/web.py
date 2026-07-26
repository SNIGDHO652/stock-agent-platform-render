"""Browser-facing single-page UI for the stock agent platform."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    """Render the secure browser UI."""
    return HTMLResponse(content=INDEX_HTML)


@router.get("/app", response_class=HTMLResponse)
async def app_page() -> HTMLResponse:
    """Render the secure browser UI at /app."""
    return HTMLResponse(content=INDEX_HTML)


INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stock Agent Platform</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070915;
      --bg-soft: #0b1020;
      --card: rgba(15, 23, 42, 0.82);
      --card-strong: rgba(17, 24, 39, 0.94);
      --border: rgba(148, 163, 184, 0.18);
      --border-strong: rgba(148, 163, 184, 0.32);
      --text: #e8eefc;
      --muted: #9aa8bd;
      --soft: #cbd5e1;
      --accent: #38bdf8;
      --accent-2: #22c55e;
      --violet: #a78bfa;
      --warning: #fbbf24;
      --danger: #fb7185;
      --good: #34d399;
      --shadow: rgba(0, 0, 0, 0.42);
    }

    * {
      box-sizing: border-box;
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 8% -10%, rgba(56, 189, 248, 0.24), transparent 34rem),
        radial-gradient(circle at 88% 0%, rgba(167, 139, 250, 0.18), transparent 34rem),
        radial-gradient(circle at 50% 100%, rgba(34, 197, 94, 0.13), transparent 30rem),
        linear-gradient(180deg, #070915 0%, #0b1020 58%, #070915 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    .shell {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 56px;
    }

    .nav {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 30px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 900;
      letter-spacing: -0.03em;
    }

    .logo {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: linear-gradient(135deg, #38bdf8, #22c55e);
      color: #03111c;
      box-shadow: 0 16px 42px rgba(56, 189, 248, 0.26);
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .security-pill {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      border: 1px solid rgba(52, 211, 153, 0.34);
      background: rgba(34, 197, 94, 0.1);
      color: #bbf7d0;
      border-radius: 999px;
      padding: 9px 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(330px, 0.82fr);
      gap: 22px;
      align-items: stretch;
      margin-bottom: 22px;
    }

    .card {
      background: linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 0.72));
      border: 1px solid var(--border);
      border-radius: 28px;
      box-shadow: 0 30px 80px var(--shadow);
      backdrop-filter: blur(18px);
      overflow: hidden;
    }

    .card-inner {
      padding: 26px;
    }

    .hero-copy {
      min-height: 390px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }

    .hero-copy::after {
      content: "";
      position: absolute;
      right: -90px;
      bottom: -120px;
      width: 320px;
      height: 320px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(56, 189, 248, 0.18), transparent 65%);
      pointer-events: none;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      color: #bae6fd;
      font-size: 0.78rem;
      font-weight: 900;
      letter-spacing: 0.13em;
      text-transform: uppercase;
    }

    .eyebrow::before {
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--accent-2);
      box-shadow: 0 0 22px var(--accent-2);
    }

    h1 {
      margin: 18px 0 0;
      max-width: 850px;
      font-size: clamp(2.35rem, 6vw, 5.3rem);
      line-height: 0.92;
      letter-spacing: -0.08em;
    }

    h2 {
      margin: 0 0 14px;
      font-size: 1.12rem;
      letter-spacing: -0.025em;
    }

    h3 {
      margin: 0 0 10px;
      font-size: 0.98rem;
      color: var(--soft);
    }

    p {
      color: var(--muted);
      margin: 12px 0 0;
    }

    .subtitle {
      font-size: 1.08rem;
      max-width: 720px;
      color: #b6c2d8;
    }

    .feature-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 26px;
    }

    .feature {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.34);
      border-radius: 18px;
      padding: 14px;
    }

    .feature b {
      display: block;
      color: var(--text);
      font-size: 0.92rem;
    }

    .feature span {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.82rem;
    }

    form {
      position: relative;
      z-index: 2;
    }

    label {
      display: block;
      color: #cbd5e1;
      font-size: 0.88rem;
      font-weight: 800;
      margin: 16px 0 8px;
    }

    input,
    button,
    select {
      width: 100%;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.58);
      color: var(--text);
      padding: 14px 15px;
      font: inherit;
      outline: none;
    }

    input:focus {
      border-color: rgba(56, 189, 248, 0.8);
      box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.12);
    }

    .hint {
      color: var(--muted);
      font-size: 0.84rem;
      margin-top: 7px;
    }

    .inline {
      display: grid;
      grid-template-columns: 1fr 0.9fr;
      gap: 12px;
    }

    .check-row {
      display: flex;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 0.92rem;
      font-weight: 700;
      margin-top: 15px;
    }

    .check-row input {
      width: 18px;
      height: 18px;
      accent-color: var(--accent);
    }

    .primary {
      cursor: pointer;
      margin-top: 18px;
      border: 0;
      color: #03111c;
      font-weight: 950;
      letter-spacing: -0.015em;
      background: linear-gradient(135deg, #38bdf8, #22c55e);
      box-shadow: 0 18px 45px rgba(34, 197, 94, 0.18);
      transition: transform 0.16s ease, filter 0.16s ease, opacity 0.16s ease;
    }

    .primary:hover {
      transform: translateY(-1px);
      filter: brightness(1.08);
    }

    .primary:disabled {
      opacity: 0.58;
      cursor: not-allowed;
      transform: none;
    }

    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
      min-height: 34px;
    }

    .suggestion {
      cursor: pointer;
      border: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.86);
      border-radius: 999px;
      padding: 8px 11px;
      color: #dbeafe;
      font-size: 0.84rem;
      font-weight: 800;
    }

    .suggestion small {
      color: var(--muted);
      font-weight: 700;
      margin-left: 6px;
    }

    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }

    .mini {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.34);
      border-radius: 18px;
      padding: 14px;
    }

    .mini .value {
      font-size: 1.55rem;
      font-weight: 950;
      letter-spacing: -0.05em;
    }

    .mini .caption {
      color: var(--muted);
      font-size: 0.84rem;
      margin-top: 3px;
    }

    .workspace {
      display: grid;
      grid-template-columns: 390px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .sticky {
      position: sticky;
      top: 18px;
    }

    .progress-list {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }

    .event {
      display: grid;
      grid-template-columns: 34px 1fr;
      gap: 10px;
      align-items: start;
    }

    .dot {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.26);
      color: #bae6fd;
      font-size: 0.75rem;
      font-weight: 900;
    }

    .event-body {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.28);
      border-radius: 16px;
      padding: 10px 12px;
    }

    .event-body b {
      display: block;
      font-size: 0.9rem;
    }

    .event-body span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      margin-top: 2px;
    }

    .status {
      display: none;
      margin-top: 12px;
      border-radius: 16px;
      border: 1px solid var(--border);
      padding: 13px 14px;
      color: #dbeafe;
      background: rgba(2, 6, 23, 0.34);
    }

    .status.error {
      color: #fecdd3;
      border-color: rgba(251, 113, 133, 0.35);
      background: rgba(251, 113, 133, 0.09);
    }

    .results {
      display: grid;
      gap: 18px;
    }

    .empty {
      min-height: 460px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
    }

    .empty svg {
      opacity: 0.8;
      margin-bottom: 16px;
    }

    .result-header {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 16px;
    }

    .company-title {
      font-size: clamp(1.45rem, 3vw, 2.15rem);
      font-weight: 950;
      letter-spacing: -0.055em;
      margin: 0;
    }

    .ticker {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 64px;
      border-radius: 14px;
      padding: 9px 12px;
      color: #03111c;
      font-weight: 950;
      background: linear-gradient(135deg, #38bdf8, #22c55e);
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }

    .kpi {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.28);
      border-radius: 18px;
      padding: 14px;
    }

    .kpi .label {
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .kpi .num {
      margin-top: 6px;
      font-size: 1.25rem;
      font-weight: 950;
      letter-spacing: -0.04em;
    }

    canvas {
      width: 100%;
      height: 260px;
      display: block;
      background: rgba(2, 6, 23, 0.22);
      border: 1px solid var(--border);
      border-radius: 20px;
    }

    .rating-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .rating {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.28);
      border-radius: 20px;
      padding: 16px;
    }

    .rating .bucket {
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }

    .rating .label {
      margin-top: 8px;
      font-size: 1.28rem;
      font-weight: 950;
      letter-spacing: -0.04em;
      text-transform: capitalize;
    }

    .rating.good .label { color: var(--good); }
    .rating.warn .label { color: var(--warning); }
    .rating.bad .label { color: var(--danger); }

    .rating .meta {
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.86rem;
    }

    .columns {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    ul {
      margin: 0;
      padding-left: 20px;
      color: var(--soft);
    }

    li {
      margin: 8px 0;
    }

    .table-wrap {
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 18px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 580px;
    }

    th,
    td {
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      font-size: 0.9rem;
    }

    th {
      color: var(--muted);
      background: rgba(2, 6, 23, 0.36);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.74rem;
    }

    tr:last-child td {
      border-bottom: 0;
    }

    details {
      border: 1px solid var(--border);
      background: rgba(2, 6, 23, 0.24);
      border-radius: 18px;
      padding: 14px;
    }

    summary {
      cursor: pointer;
      font-weight: 850;
      color: #dbeafe;
    }

    pre {
      overflow: auto;
      max-height: 520px;
      padding: 14px;
      border-radius: 14px;
      background: #020617;
      color: #dbeafe;
      font-size: 0.8rem;
    }

    .footer-note {
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.82rem;
    }

    .hidden {
      display: none !important;
    }

    @media (max-width: 980px) {
      .hero,
      .workspace {
        grid-template-columns: 1fr;
      }

      .sticky {
        position: static;
      }

      .feature-grid,
      .kpi-grid,
      .rating-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 620px) {
      .shell {
        width: min(100% - 22px, 1180px);
        padding-top: 18px;
      }

      .nav {
        align-items: flex-start;
        flex-direction: column;
      }

      .hero-copy {
        min-height: auto;
      }

      .card-inner {
        padding: 18px;
      }

      .feature-grid,
      .inline,
      .mini-grid,
      .kpi-grid,
      .rating-grid,
      .columns {
        grid-template-columns: 1fr;
      }

      .nav-actions {
        width: 100%;
        justify-content: space-between;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <nav class="nav">
      <div class="brand">
        <div class="logo" aria-hidden="true">◆</div>
        <div>
          <div>Stock Agent Platform</div>
          <small style="color: var(--muted); font-weight: 700;">Free Render demo • secure same-origin UI</small>
        </div>
      </div>
      <div class="nav-actions">
        <span class="security-pill">🔐 No API key in browser</span>
        <a href="/docs" target="_blank" rel="noreferrer">API Docs</a>
      </div>
    </nav>

    <section class="hero">
      <div class="card hero-copy">
        <div class="card-inner">
          <div class="eyebrow">Agentic equity research</div>
          <h1>Analyze a public company in one click.</h1>
          <p class="subtitle">
            Enter a company name or ticker. The backend resolves the stock, runs LangGraph analysis,
            computes forecasts and ratings, then synthesizes the evidence with CrewAI or a deterministic fallback.
          </p>
          <div class="feature-grid">
            <div class="feature"><b>Forecasts</b><span>5–252 trading-day horizons with intervals.</span></div>
            <div class="feature"><b>Ratings</b><span>Short, medium, and long-term buy/sell signals.</span></div>
            <div class="feature"><b>Risk</b><span>Drawdown, VaR, beta, volatility, scenarios.</span></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-inner">
          <h2>Run analysis</h2>
          <p>The UI talks to <code>/web/*</code> routes. Your Render <code>API_KEY</code> stays server-side and is never sent to users.</p>

          <form id="analysisForm">
            <label for="company">Company name or ticker</label>
            <input id="company" name="company" type="text" value="Microsoft" autocomplete="organization" minlength="1" maxlength="120" required />
            <div class="hint">Examples: Microsoft, Apple, Tesla, Nvidia, RELIANCE.NS</div>
            <div id="suggestions" class="suggestions"></div>

            <div class="inline">
              <div>
                <label for="horizons">Horizons</label>
                <input id="horizons" name="horizons" type="text" value="5,20,60" />
                <div class="hint">Trading days, max 5 values.</div>
              </div>
              <div>
                <label for="preset">Preset</label>
                <select id="preset" name="preset">
                  <option value="5,20,60">Short + medium</option>
                  <option value="20,60,120">Swing + long</option>
                  <option value="5,10,20,60,120">Full demo</option>
                </select>
              </div>
            </div>

            <label class="check-row">
              <input id="narrative" type="checkbox" checked />
              Include AI narrative when OPENAI_API_KEY is configured
            </label>

            <button id="submitBtn" class="primary" type="submit">Run stock analysis</button>
            <div id="statusBox" class="status"></div>
          </form>

          <div class="mini-grid">
            <div class="mini">
              <div class="value">0</div>
              <div class="caption">API keys exposed to browser</div>
            </div>
            <div class="mini">
              <div class="value">/web</div>
              <div class="caption">Same-origin secure UI proxy</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="workspace">
      <aside class="card sticky">
        <div class="card-inner">
          <h2>Progress</h2>
          <p id="jobMeta">No active job yet.</p>
          <div id="progressList" class="progress-list"></div>
          <p class="footer-note">
            Free Render services can sleep or restart. For production, use the Celery/Redis worker version.
          </p>
        </div>
      </aside>

      <section id="results" class="results">
        <div class="card empty">
          <div class="card-inner">
            <svg width="72" height="72" viewBox="0 0 72 72" fill="none" aria-hidden="true">
              <rect x="8" y="8" width="56" height="56" rx="18" fill="rgba(56,189,248,0.12)" stroke="rgba(56,189,248,0.35)" />
              <path d="M20 46L31 35L39 42L53 24" stroke="#38bdf8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M50 24H53V27" stroke="#22c55e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h2>Results will appear here</h2>
            <p>Start an analysis to see ratings, forecast intervals, chart, risk metrics, and the narrative summary.</p>
          </div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const form = document.getElementById("analysisForm");
    const companyInput = document.getElementById("company");
    const horizonsInput = document.getElementById("horizons");
    const presetInput = document.getElementById("preset");
    const narrativeInput = document.getElementById("narrative");
    const submitBtn = document.getElementById("submitBtn");
    const statusBox = document.getElementById("statusBox");
    const progressList = document.getElementById("progressList");
    const jobMeta = document.getElementById("jobMeta");
    const results = document.getElementById("results");
    const suggestions = document.getElementById("suggestions");

    let activeStream = null;
    let activePoller = null;
    let suggestionTimer = null;

    presetInput.addEventListener("change", () => {
      horizonsInput.value = presetInput.value;
    });

    companyInput.addEventListener("input", () => {
      clearTimeout(suggestionTimer);
      const query = companyInput.value.trim();
      if (query.length < 2) {
        suggestions.innerHTML = "";
        return;
      }
      suggestionTimer = setTimeout(() => fetchSuggestions(query), 280);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        company_name: companyInput.value.trim(),
        horizons: parseHorizons(horizonsInput.value),
        include_ai_narrative: narrativeInput.checked,
      };

      if (!payload.company_name) {
        setStatus("Enter a company name or ticker.", true);
        return;
      }
      if (!payload.horizons.length) {
        setStatus("Enter 1–5 horizons between 1 and 252 trading days.", true);
        return;
      }

      resetRun();
      submitBtn.disabled = true;
      setStatus("Creating analysis job…", false);
      addProgress("queued", "Submitting job to the secure same-origin backend.");

      try {
        const response = await fetch("/web/analyses", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await readJson(response);
        if (!response.ok) throw new Error(data.detail || "Unable to create analysis.");

        setStatus(`Job accepted: ${data.job_id}`, false);
        jobMeta.textContent = `Job ${data.job_id} · ${data.status}`;
        openProgressStream(data.job_id);
        startPolling(data.job_id);
      } catch (error) {
        submitBtn.disabled = false;
        setStatus(error.message || String(error), true);
        addProgress("failed", error.message || String(error));
      }
    });

    function parseHorizons(value) {
      const unique = [...new Set(
        String(value)
          .split(",")
          .map((part) => Number.parseInt(part.trim(), 10))
          .filter((number) => Number.isInteger(number) && number >= 1 && number <= 252)
      )];
      return unique.slice(0, 5).sort((a, b) => a - b);
    }

    async function fetchSuggestions(query) {
      try {
        const response = await fetch(`/web/companies/search?q=${encodeURIComponent(query)}&limit=4`);
        if (!response.ok) return;
        const items = await response.json();
        suggestions.innerHTML = items.map((item) => `
          <button class="suggestion" type="button" data-symbol="${escapeHtml(item.symbol)}" data-name="${escapeHtml(item.name)}">
            ${escapeHtml(item.name)} <small>${escapeHtml(item.symbol)}</small>
          </button>
        `).join("");
        for (const button of suggestions.querySelectorAll(".suggestion")) {
          button.addEventListener("click", () => {
            companyInput.value = button.dataset.name || button.dataset.symbol;
            suggestions.innerHTML = "";
          });
        }
      } catch {
        suggestions.innerHTML = "";
      }
    }

    function openProgressStream(jobId) {
      if (activeStream) activeStream.close();

      activeStream = new EventSource(`/web/analyses/${jobId}/stream`);
      activeStream.addEventListener("progress", (event) => {
        const payload = JSON.parse(event.data);
        addProgress(payload.stage, payload.message);
      });
      activeStream.addEventListener("terminal", (event) => {
        const payload = JSON.parse(event.data);
        addProgress(payload.status, `Job finished with status: ${payload.status}`);
        activeStream.close();
        fetchResult(jobId);
      });
      activeStream.onerror = () => {
        addProgress("stream", "Live stream paused; polling will continue.");
        activeStream.close();
      };
    }

    function startPolling(jobId) {
      clearInterval(activePoller);
      activePoller = setInterval(() => fetchResult(jobId, false), 2600);
    }

    async function fetchResult(jobId, showErrors = true) {
      try {
        const response = await fetch(`/web/analyses/${jobId}`);
        const job = await readJson(response);
        if (!response.ok) throw new Error(job.detail || "Unable to fetch result.");

        jobMeta.textContent = `Job ${job.id} · ${job.status}`;
        if (job.status === "completed") {
          clearInterval(activePoller);
          submitBtn.disabled = false;
          setStatus("Analysis completed.", false);
          renderReport(job.result);
        } else if (job.status === "failed") {
          clearInterval(activePoller);
          submitBtn.disabled = false;
          setStatus(job.error || "Analysis failed.", true);
          addProgress("failed", job.error || "Analysis failed.");
        }
      } catch (error) {
        if (showErrors) setStatus(error.message || String(error), true);
      }
    }

    async function readJson(response) {
      const text = await response.text();
      if (!text) return {};
      try {
        return JSON.parse(text);
      } catch {
        return {detail: text};
      }
    }

    function resetRun() {
      if (activeStream) activeStream.close();
      clearInterval(activePoller);
      progressList.innerHTML = "";
      results.innerHTML = emptyLoadingHtml();
    }

    function setStatus(message, isError) {
      statusBox.style.display = "block";
      statusBox.className = isError ? "status error" : "status";
      statusBox.textContent = message;
    }

    function addProgress(stage, message) {
      const event = document.createElement("div");
      event.className = "event";
      const number = progressList.children.length + 1;
      event.innerHTML = `
        <div class="dot">${number}</div>
        <div class="event-body">
          <b>${escapeHtml(stage)}</b>
          <span>${escapeHtml(message)}</span>
        </div>
      `;
      progressList.prepend(event);
    }

    function emptyLoadingHtml() {
      return `
        <div class="card empty">
          <div class="card-inner">
            <h2>Analysis running…</h2>
            <p>Market data, forecasts, risk, ratings, and narrative synthesis are being prepared.</p>
          </div>
        </div>
      `;
    }

    function renderReport(report) {
      const company = report.company || {};
      const snapshot = report.snapshot || {};
      const narrative = report.narrative || {};
      const ratings = report.ratings || [];
      const forecast = report.forecast || {};
      const risk = report.risk || {};
      const technical = report.technical || {};
      const fundamentals = report.fundamentals || {};
      const sentiment = report.sentiment || {};

      results.innerHTML = `
        <div class="card">
          <div class="card-inner">
            <div class="result-header">
              <div>
                <p class="eyebrow">Final report</p>
                <h2 class="company-title">${escapeHtml(company.name || "Unknown company")}</h2>
                <p>${escapeHtml(snapshot.sector || "Unknown sector")} · ${escapeHtml(snapshot.industry || "Unknown industry")}</p>
              </div>
              <div class="ticker">${escapeHtml(company.symbol || "N/A")}</div>
            </div>
            <p>${escapeHtml(narrative.executive_summary || "No narrative summary returned.")}</p>

            <div class="kpi-grid">
              ${kpi("Last price", formatMoney(snapshot.last_price, company.currency))}
              ${kpi("Daily change", formatPercent(snapshot.daily_change_pct))}
              ${kpi("Risk level", humanize(risk.risk_level))}
              ${kpi("Sentiment", humanize(sentiment.label))}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-inner">
            <h2>Price history</h2>
            <canvas id="priceChart" width="1000" height="360" aria-label="Price history chart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-inner">
            <h2>Horizon ratings</h2>
            <div class="rating-grid">
              ${ratings.map(renderRating).join("") || "<p>No ratings returned.</p>"}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-inner">
            <h2>Forecast intervals</h2>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Horizon</th>
                    <th>Predicted price</th>
                    <th>Predicted return</th>
                    <th>80% low</th>
                    <th>80% high</th>
                  </tr>
                </thead>
                <tbody>
                  ${(forecast.forecasts || []).map((row) => `
                    <tr>
                      <td>${row.horizon_days} days</td>
                      <td>${formatMoney(row.predicted_price, company.currency)}</td>
                      <td>${formatPercent(row.predicted_return_pct)}</td>
                      <td>${formatMoney(row.low_80_price, company.currency)}</td>
                      <td>${formatMoney(row.high_80_price, company.currency)}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
            <p class="footer-note">Model: ${escapeHtml(forecast.model || "unknown")} · Confidence: ${formatPercent((forecast.confidence || 0) * 100)}</p>
          </div>
        </div>

        <div class="columns">
          <div class="card">
            <div class="card-inner">
              <h2>Bull case</h2>
              ${listHtml(narrative.bull_case)}
            </div>
          </div>
          <div class="card">
            <div class="card-inner">
              <h2>Bear case</h2>
              ${listHtml(narrative.bear_case)}
            </div>
          </div>
        </div>

        <div class="columns">
          <div class="card">
            <div class="card-inner">
              <h2>Technical + risk</h2>
              <div class="kpi-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
                ${kpi("Regime", humanize(technical.regime))}
                ${kpi("RSI 14", fixed(technical.rsi_14))}
                ${kpi("Volatility", formatPercent(risk.annualized_volatility_pct))}
                ${kpi("Max drawdown", formatPercent(risk.max_drawdown_pct))}
              </div>
            </div>
          </div>
          <div class="card">
            <div class="card-inner">
              <h2>Fundamentals</h2>
              <div class="kpi-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
                ${kpi("Quality score", fixed(fundamentals.quality_score))}
                ${kpi("Completeness", formatPercent((fundamentals.data_completeness || 0) * 100))}
                ${kpi("Market cap", compactMoney(snapshot.market_cap, company.currency))}
                ${kpi("Sentiment score", fixed(sentiment.overall_score))}
              </div>
            </div>
          </div>
        </div>

        <details>
          <summary>Full JSON report</summary>
          <pre>${escapeHtml(JSON.stringify(report, null, 2))}</pre>
        </details>
      `;

      drawPriceChart(report.price_history || []);
    }

    function renderRating(item) {
      const label = String(item.label || "hold");
      const score = Number(item.score || 0);
      const className = score > 12 ? "good" : score < -12 ? "bad" : "warn";
      return `
        <div class="rating ${className}">
          <div class="bucket">${escapeHtml(humanize(item.bucket))} · ${item.horizon_days}d</div>
          <div class="label">${escapeHtml(humanize(label))}</div>
          <div class="meta">Score ${fixed(score)} · Confidence ${formatPercent((item.confidence || 0) * 100)}</div>
          <div class="meta">Return ${formatPercent(item.predicted_return_pct)}</div>
        </div>
      `;
    }

    function drawPriceChart(history) {
      const canvas = document.getElementById("priceChart");
      if (!canvas || !history.length) return;
      const ctx = canvas.getContext("2d");
      const width = canvas.width;
      const height = canvas.height;
      const pad = 34;
      const values = history.map((item) => Number(item.close)).filter((value) => Number.isFinite(value));
      if (values.length < 2) return;

      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;

      ctx.clearRect(0, 0, width, height);
      const gradient = ctx.createLinearGradient(0, 0, width, height);
      gradient.addColorStop(0, "rgba(56, 189, 248, 0.18)");
      gradient.addColorStop(1, "rgba(34, 197, 94, 0.02)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
      ctx.lineWidth = 1;
      for (let i = 0; i < 5; i++) {
        const y = pad + i * ((height - pad * 2) / 4);
        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(width - pad, y);
        ctx.stroke();
      }

      ctx.beginPath();
      values.forEach((value, index) => {
        const x = pad + index * ((width - pad * 2) / (values.length - 1));
        const y = height - pad - ((value - min) / span) * (height - pad * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.lineTo(width - pad, height - pad);
      ctx.lineTo(pad, height - pad);
      ctx.closePath();
      const area = ctx.createLinearGradient(0, pad, 0, height - pad);
      area.addColorStop(0, "rgba(56, 189, 248, 0.22)");
      area.addColorStop(1, "rgba(56, 189, 248, 0)");
      ctx.fillStyle = area;
      ctx.fill();

      ctx.fillStyle = "#cbd5e1";
      ctx.font = "700 18px Inter, system-ui";
      ctx.fillText(`High ${formatNumber(max)} · Low ${formatNumber(min)}`, pad, 28);
    }

    function kpi(label, value) {
      return `
        <div class="kpi">
          <div class="label">${escapeHtml(label)}</div>
          <div class="num">${escapeHtml(value ?? "N/A")}</div>
        </div>
      `;
    }

    function listHtml(items) {
      if (!Array.isArray(items) || !items.length) return "<p>No items returned.</p>";
      return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
    }

    function humanize(value) {
      if (value === null || value === undefined || value === "") return "N/A";
      return String(value).replaceAll("_", " ");
    }

    function fixed(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number.toFixed(2) : "N/A";
    }

    function formatNumber(value) {
      const number = Number(value);
      if (!Number.isFinite(number)) return "N/A";
      return new Intl.NumberFormat("en-GB", {maximumFractionDigits: 2}).format(number);
    }

    function formatPercent(value) {
      const number = Number(value);
      if (!Number.isFinite(number)) return "N/A";
      const sign = number > 0 ? "+" : "";
      return `${sign}${number.toFixed(2)}%`;
    }

    function formatMoney(value, currency) {
      const number = Number(value);
      if (!Number.isFinite(number)) return "N/A";
      if (!currency) return formatNumber(number);
      try {
        return new Intl.NumberFormat("en-GB", {
          style: "currency",
          currency,
          maximumFractionDigits: 2,
        }).format(number);
      } catch {
        return `${formatNumber(number)} ${currency}`;
      }
    }

    function compactMoney(value, currency) {
      const number = Number(value);
      if (!Number.isFinite(number)) return "N/A";
      if (!currency) return new Intl.NumberFormat("en-GB", {notation: "compact", maximumFractionDigits: 2}).format(number);
      try {
        return new Intl.NumberFormat("en-GB", {
          style: "currency",
          currency,
          notation: "compact",
          maximumFractionDigits: 2,
        }).format(number);
      } catch {
        return `${new Intl.NumberFormat("en-GB", {notation: "compact", maximumFractionDigits: 2}).format(number)} ${currency}`;
      }
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  </script>
</body>
</html>
"""
