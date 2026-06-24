/**
 * Sage Pontus — PT Red Flag Alert
 * content.js: 드래그 가능한 플로팅 패널 (Shadow DOM 격리)
 * toolbar 클릭 → background.js → TOGGLE_PANEL 메시지 → 패널 토글
 */
(function () {
if (window.SAGE_PONTUS_INITIALIZED) return;
window.SAGE_PONTUS_INITIALIZED = true;

// ── 상수 ───────────────────────────────────────────────────────────
const DEFAULT_SERVER = "https://sagepontus-284182376290.us-east4.run.app";

const CONDITION_LABELS = {
  cauda_equina: "Cauda Equina Syndrome",
  fracture:     "Spinal Fracture",
  malignancy:   "Spinal Malignancy",
  infection:    "Spinal Infection",
  vascular:     "Abdominal Aortic Aneurysm",
  inflammatory: "Inflammatory Spondyloarthropathy",
};

const ALARM_CONFIG = {
  RED:    { icon: "🚨", cssClass: "red",    text: "RED ALERT — Immediate Action Required" },
  YELLOW: { icon: "⚠️",  cssClass: "yellow", text: "YELLOW FLAG — Physician Notification" },
  NONE:   { icon: "✅",  cssClass: "none",   text: "No Red Flags Detected" },
};

// ── CSS (Shadow DOM 안에 주입) ──────────────────────────────────────
const PANEL_CSS = `
* { box-sizing: border-box; margin: 0; padding: 0; }

#sp-panel {
  position: fixed;
  top: 80px;
  right: 20px;
  width: 380px;
  max-height: 90vh;
  background: #f8f9fc;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.22), 0 2px 8px rgba(0,0,0,0.12);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px;
  color: #1a1a2e;
  z-index: 2147483647;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 드래그 핸들 */
#sp-drag-handle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #1a1a2e;
  color: #fff;
  cursor: move;
  user-select: none;
  border-radius: 12px 12px 0 0;
  flex-shrink: 0;
}
#sp-drag-title { font-size: 13px; font-weight: 700; letter-spacing: 0.3px; }
#sp-close {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}
#sp-close:hover { color: #fff; }

/* 스크롤 영역 */
#sp-body {
  overflow-y: auto;
  flex: 1;
}

.screen { padding: 16px; }
.hidden { display: none !important; }

/* Logo */
.logo-row { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.logo-icon  { font-size: 28px; }
.logo-title { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.logo-sub   { font-size: 11px; color: #6b7280; }

/* Form */
.form-group       { margin-bottom: 12px; }
.form-group label { display: block; font-size: 11px; font-weight: 600;
                    color: #6b7280; text-transform: uppercase;
                    letter-spacing: 0.5px; margin-bottom: 4px; }
.hint { font-weight: 400; text-transform: none; color: #9ca3af; }

input[type="text"],
input[type="password"],
textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  outline: none;
  transition: border-color 0.15s;
  resize: vertical;
  font-family: inherit;
}
input:focus, textarea:focus { border-color: #4f46e5; }
textarea { font-family: "Menlo","Consolas",monospace; font-size: 12px; line-height: 1.5; }

/* Buttons */
.btn {
  padding: 8px 14px;
  border-radius: 6px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.btn:active { transform: scale(0.97); }
.btn-primary { background: #4f46e5; color: #fff; flex: 1; }
.btn-primary:hover { background: #4338ca; }
.btn-ghost  { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-ghost:hover  { background: #e5e7eb; }
.btn-danger-outline { background: #fff; color: #dc2626; border: 1.5px solid #dc2626; width: 100%; margin-top: 4px; }
.btn-danger-outline:hover { background: #fef2f2; }
.btn-link { background: none; border: none; color: #6b7280; font-size: 12px; cursor: pointer; padding: 2px 4px; }
.btn-link:hover { color: #4f46e5; }
.btn-link.small { font-size: 11px; }
.btn-row { display: flex; gap: 6px; margin-top: 4px; }

/* Top bar */
.top-bar { display: flex; justify-content: space-between; align-items: center;
           margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb; }
.top-title   { font-weight: 700; font-size: 14px; color: #1a1a2e; }
.top-actions { display: flex; align-items: center; gap: 6px; }
.top-user    { font-size: 11px; color: #6b7280; }

/* Loading */
.loading { display: flex; align-items: center; gap: 10px; justify-content: center;
           padding: 16px; color: #6b7280; font-size: 13px; }
.spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb;
           border-top-color: #4f46e5; border-radius: 50%;
           animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Alarm banner */
.alarm-banner { display: flex; align-items: center; gap: 12px; padding: 14px;
                border-radius: 10px; margin-bottom: 12px; }
.alarm-banner.red    { background: #fef2f2; border: 2px solid #dc2626; }
.alarm-banner.yellow { background: #fffbeb; border: 2px solid #d97706; }
.alarm-banner.none   { background: #f0fdf4; border: 2px solid #16a34a; }
.alarm-icon       { font-size: 32px; line-height: 1; }
.alarm-level-text { font-size: 17px; font-weight: 800; }
.alarm-banner.red    .alarm-level-text { color: #dc2626; }
.alarm-banner.yellow .alarm-level-text { color: #d97706; }
.alarm-banner.none   .alarm-level-text { color: #16a34a; }
.alarm-condition  { font-size: 12px; color: #6b7280; margin-top: 2px; }

/* Trigger row */
.trigger-row { display: flex; align-items: flex-start; gap: 6px; padding: 8px 10px;
               background: #fef2f2; border-radius: 6px; margin-bottom: 10px; font-size: 12px; }
.trigger-label { color: #9ca3af; white-space: nowrap; }
.trigger-text  { color: #dc2626; font-weight: 600; }

/* Sections */
.section       { margin-bottom: 12px; }
.section-title { font-size: 11px; font-weight: 700; color: #6b7280;
                 text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.matched-list  { list-style: none; display: flex; flex-direction: column; gap: 4px; }
.matched-list li { padding: 6px 10px; background: #fff; border: 1px solid #e5e7eb;
                   border-radius: 6px; font-size: 12px; color: #374151;
                   display: flex; align-items: center; gap: 6px; }
.matched-list li::before { content: "⚑"; color: #f59e0b; font-size: 10px; }
.context-text { font-size: 12px; color: #374151; line-height: 1.5; padding: 8px 10px;
                background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; }

/* Referral */
.referral-letter { margin-top: 10px; padding: 10px; background: #fff;
                   border: 1px solid #d1d5db; border-radius: 6px;
                   font-family: monospace; font-size: 11px; line-height: 1.5;
                   white-space: pre-wrap; max-height: 200px; overflow-y: auto; color: #1f2937; }

/* Score bar */
.score-row { display: flex; align-items: center; gap: 8px; margin-top: 10px;
             padding-top: 10px; border-top: 1px solid #e5e7eb; }
.score-label   { font-size: 11px; color: #9ca3af; white-space: nowrap; }
.score-bar-wrap { flex: 1; height: 6px; background: #e5e7eb; border-radius: 99px; overflow: hidden; }
.score-bar     { height: 100%; border-radius: 99px; transition: width 0.5s ease; }
.score-value   { font-size: 12px; font-weight: 700; color: #374151; white-space: nowrap; }

/* Misc */
.error-msg { background: #fef2f2; color: #dc2626; font-size: 12px; padding: 8px 10px;
             border-radius: 6px; margin-bottom: 10px; border: 1px solid #fecaca; }
.settings-row { text-align: center; margin-top: 14px; }
`;

// ── HTML ────────────────────────────────────────────────────────────
const PANEL_HTML = `
<div id="sp-panel">
  <div id="sp-drag-handle">
    <span id="sp-drag-title">🛡 Sage Pontus</span>
    <button id="sp-close">✕</button>
  </div>
  <div id="sp-body">

    <!-- 로그인 화면 -->
    <div id="screen-login" class="screen">
      <div class="logo-row">
        <span class="logo-icon">🛡</span>
        <div>
          <div class="logo-title">Sage Pontus</div>
          <div class="logo-sub">PT Red Flag Alert</div>
        </div>
      </div>
      <div class="form-group">
        <label>Username</label>
        <input type="text" id="login-username" placeholder="your username" autocomplete="username" />
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" id="login-password" placeholder="••••••••" autocomplete="current-password" />
      </div>
      <div id="login-error" class="error-msg hidden"></div>
      <button id="btn-login" class="btn btn-primary">Sign In</button>
      <div class="settings-row">
        <button id="btn-show-settings" class="btn-link">⚙ Server settings</button>
      </div>
      <div id="settings-panel" class="hidden">
        <div style="font-size:11px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:.5px; margin-bottom:8px;">Select Server</div>
        <div style="display:flex; flex-direction:column; gap:6px;">
          <button id="srv-production" class="srv-option"
            data-url="https://sagepontus-284182376290.us-east4.run.app"
            style="text-align:left; padding:10px 12px; border-radius:8px; border:2px solid #e5e7eb; background:#f9fafb; cursor:pointer; font-size:12px;">
            <div style="font-weight:700; color:#1a1a2e; margin-bottom:2px;">Production</div>
            <div style="color:#6b7280; font-size:11px;">sagepontus.run.app</div>
          </button>
          <button id="srv-local" class="srv-option"
            data-url="http://localhost:8000"
            style="text-align:left; padding:10px 12px; border-radius:8px; border:2px solid #e5e7eb; background:#f9fafb; cursor:pointer; font-size:12px;">
            <div style="font-weight:700; color:#1a1a2e; margin-bottom:2px;">Local</div>
            <div style="color:#6b7280; font-size:11px;">localhost:8000</div>
          </button>
        </div>
      </div>
    </div>

    <!-- 분석 화면 -->
    <div id="screen-analyze" class="screen hidden">
      <div class="top-bar">
        <span class="top-title">🛡 PT Red Flag</span>
        <div class="top-actions">
          <span id="top-username" class="top-user"></span>
          <button id="btn-logout" class="btn-link small">Sign out</button>
        </div>
      </div>
      <div class="form-group">
        <label>Patient ID <span class="hint">(anonymous)</span></label>
        <input type="text" id="patient-id" placeholder="e.g. PT-2024-001" />
      </div>
      <div class="form-group">
        <label>SOAP Note <span class="hint">— paste from EMR</span></label>
        <textarea id="soap-text" rows="9"
          placeholder="Paste the full SOAP note here...

S: Patient reports...
O: ROM, strength...
A: Assessment...
P: Plan..."></textarea>
      </div>
      <div id="btn-row" class="btn-row">
        <button id="btn-paste" class="btn btn-ghost">📋 Paste</button>
        <button id="btn-clear" class="btn btn-ghost">✕ Clear</button>
        <button id="btn-analyze" class="btn btn-primary">Analyze Red Flags →</button>
      </div>
      <div id="analyze-loading" class="loading hidden">
        <div class="spinner"></div>
        <span>Analyzing…</span>
      </div>
    </div>

    <!-- 결과 화면 -->
    <div id="screen-result" class="screen hidden">
      <div class="top-bar">
        <button id="btn-back" class="btn-link">← New analysis</button>
        <span id="top-username-result" class="top-user"></span>
      </div>
      <div id="alarm-banner" class="alarm-banner">
        <div id="alarm-icon" class="alarm-icon"></div>
        <div>
          <div id="alarm-level-text" class="alarm-level-text"></div>
          <div id="alarm-condition" class="alarm-condition"></div>
        </div>
      </div>
      <div id="trigger-row" class="trigger-row hidden">
        <span class="trigger-label">Primary trigger:</span>
        <span id="trigger-text" class="trigger-text"></span>
      </div>
      <div id="matched-section" class="section hidden">
        <div class="section-title">Detected indicators</div>
        <ul id="matched-list" class="matched-list"></ul>
      </div>
      <div id="context-section" class="section hidden">
        <div class="section-title">Patient history</div>
        <div id="context-text" class="context-text"></div>
      </div>
      <div id="referral-section" class="section hidden">
        <!-- RED: single generate button -->
        <button id="btn-referral" class="btn btn-danger-outline hidden">
          📄 Generate Referral Letter
        </button>
        <!-- YELLOW: two action buttons -->
        <div id="yellow-actions" class="btn-row hidden">
          <button id="btn-monitor" class="btn btn-ghost" style="flex:1; border-color:#d97706; color:#92400e;">
            🔔 Flag for Monitoring
          </button>
          <button id="btn-escalate" class="btn" style="flex:1; background:#dc2626; color:#fff;">
            📄 Escalate to Referral
          </button>
        </div>
        <div id="yellow-status" class="hidden" style="font-size:12px; color:#92400e; background:#fefce8; border:1px solid #fde047; border-radius:6px; padding:8px 10px; margin-top:4px;"></div>
        <div id="referral-letter" class="referral-letter hidden"></div>
        <button id="btn-copy-referral" class="btn btn-ghost hidden">📋 Copy letter</button>
      </div>
      <div class="score-row">
        <span class="score-label">Risk score</span>
        <div class="score-bar-wrap">
          <div id="score-bar" class="score-bar"></div>
        </div>
        <span id="score-value" class="score-value"></span>
      </div>
    </div>

  </div><!-- /sp-body -->
</div><!-- /sp-panel -->
`;

// ── 패널 생성 ────────────────────────────────────────────────────────
let shadowRoot = null;
let panelVisible = false;

function createPanel() {
  if (document.getElementById("sp-host")) return;

  const host = document.createElement("div");
  host.id = "sp-host";
  host.style.cssText = "all: initial; position: fixed; z-index: 2147483647;";
  document.body.appendChild(host);

  shadowRoot = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = PANEL_CSS;
  shadowRoot.appendChild(style);

  const wrapper = document.createElement("div");
  wrapper.innerHTML = PANEL_HTML;
  shadowRoot.appendChild(wrapper);

  initDrag(shadowRoot);
  initLogic(shadowRoot);
  restorePosition(shadowRoot);
}

// ── 드래그 ──────────────────────────────────────────────────────────
function initDrag(root) {
  const panel  = root.getElementById("sp-panel");
  const handle = root.getElementById("sp-drag-handle");

  let dragging = false, offX = 0, offY = 0;

  handle.addEventListener("mousedown", (e) => {
    if (e.target.id === "sp-close") return;
    dragging = true;
    offX = e.clientX - panel.getBoundingClientRect().left;
    offY = e.clientY - panel.getBoundingClientRect().top;
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const x = Math.max(0, Math.min(e.clientX - offX, window.innerWidth  - panel.offsetWidth));
    const y = Math.max(0, Math.min(e.clientY - offY, window.innerHeight - panel.offsetHeight));
    panel.style.left  = x + "px";
    panel.style.top   = y + "px";
    panel.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    chrome.storage.local.set({
      spPanelLeft: panel.style.left,
      spPanelTop:  panel.style.top,
    });
  });
}

// ── 위치 복원 ────────────────────────────────────────────────────────
async function restorePosition(root) {
  const { spPanelLeft, spPanelTop } = await chrome.storage.local.get(["spPanelLeft", "spPanelTop"]);
  const panel = root.getElementById("sp-panel");
  if (spPanelLeft && spPanelTop) {
    panel.style.left  = spPanelLeft;
    panel.style.top   = spPanelTop;
    panel.style.right = "auto";
  }
}

// ── 앱 로직 ─────────────────────────────────────────────────────────
let state = { token: null, username: null, serverUrl: DEFAULT_SERVER };

function initLogic(root) {
  const $ = id => root.getElementById(id);

  chrome.storage.local.get(["token", "username", "serverUrl"]).then(stored => {
    state.token     = stored.token     || null;
    state.username  = stored.username  || null;
    state.serverUrl = stored.serverUrl || DEFAULT_SERVER;

    if (state.token) {
      showAnalyzeScreen($);
    } else {
      showScreen($, "login");
    }
  });

  $("sp-close").addEventListener("click", hidePanel);

  $("btn-login").addEventListener("click", () => handleLogin($));
  $("login-password").addEventListener("keydown", e => {
    if (e.key === "Enter") handleLogin($);
  });

  $("btn-show-settings").addEventListener("click", () => {
    const panel = $("settings-panel");
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) highlightActiveServer($);
  });

  ["srv-production", "srv-local"].forEach(id => {
    $(id).addEventListener("click", async () => {
      const url = $(id).dataset.url;
      state.serverUrl = url;
      await chrome.storage.local.set({ serverUrl: url });
      highlightActiveServer($);
      $("settings-panel").classList.add("hidden");
    });
  });

  $("btn-logout").addEventListener("click", () => handleLogout($));

  $("btn-paste").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      $("soap-text").value = text;
    } catch {
      $("soap-text").focus();
      document.execCommand("paste");
    }
  });

  $("btn-clear").addEventListener("click", () => {
    $("soap-text").value  = "";
    $("patient-id").value = "";
  });

  $("btn-analyze").addEventListener("click", () => handleAnalyze($));
  $("btn-back").addEventListener("click", () => showAnalyzeScreen($));
  $("btn-referral").addEventListener("click", () => handleAlarmAction($, "referral"));
  $("btn-monitor").addEventListener("click",  () => handleAlarmAction($, "monitor"));
  $("btn-escalate").addEventListener("click", () => handleAlarmAction($, "referral"));

  $("btn-copy-referral").addEventListener("click", () => {
    const text = $("referral-letter").textContent;
    navigator.clipboard.writeText(text).then(() => {
      $("btn-copy-referral").textContent = "✅ Copied!";
      setTimeout(() => { $("btn-copy-referral").textContent = "📋 Copy letter"; }, 2000);
    });
  });
}

// ── 화면 전환 ────────────────────────────────────────────────────────
function showScreen($, name) {
  ["login", "analyze", "result"].forEach(s => {
    $(`screen-${s}`).classList.toggle("hidden", s !== name);
  });
}

function showAnalyzeScreen($) {
  $("top-username").textContent        = state.username || "";
  $("top-username-result").textContent = state.username || "";
  showScreen($, "analyze");
}

// ── 로그인 ──────────────────────────────────────────────────────────
async function handleLogin($) {
  const username = $("login-username").value.trim();
  const password = $("login-password").value;
  const errEl    = $("login-error");

  if (!username || !password) {
    showError(errEl, "Please enter username and password.");
    return;
  }

  $("btn-login").textContent = "Signing in…";
  $("btn-login").disabled    = true;
  errEl.classList.add("hidden");

  try {
    const res = await fetch(`${state.serverUrl}/api/auth/token/`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.non_field_errors?.[0] || "Invalid credentials.");
    }

    const { token } = await res.json();
    state.token    = token;
    state.username = username;
    await chrome.storage.local.set({ token, username });
    showAnalyzeScreen($);

  } catch (err) {
    showError(errEl, err.message || "Login failed. Check server URL.");
  } finally {
    $("btn-login").textContent = "Sign In";
    $("btn-login").disabled    = false;
  }
}

// ── 로그아웃 ─────────────────────────────────────────────────────────
async function handleLogout($) {
  state.token    = null;
  state.username = null;
  await chrome.storage.local.remove(["token", "username"]);
  showScreen($, "login");
}

// ── 분석 ────────────────────────────────────────────────────────────
async function handleAnalyze($) {
  const soapText  = $("soap-text").value.trim();
  const patientId = $("patient-id").value.trim() || generatePatientId();

  if (!soapText) {
    $("soap-text").focus();
    return;
  }

  $("btn-analyze").disabled = true;
  $("analyze-loading").classList.remove("hidden");
  $("btn-row").classList.add("hidden");

  try {
    const res = await fetch(`${state.serverUrl}/api/pt/analyze/`, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Token ${state.token}`,
      },
      body: JSON.stringify({
        patient_id: patientId,
        soap_text:  soapText,
        generate_referral: false,
      }),
    });

    if (res.status === 401) {
      await handleLogout($);
      return;
    }

    if (!res.ok) throw new Error(`Server error: ${res.status}`);

    const data = await res.json();
    renderResult($, data, soapText, patientId);

  } catch (err) {
    alert("Analysis failed: " + err.message);
  } finally {
    $("btn-analyze").disabled = false;
    $("analyze-loading").classList.add("hidden");
    $("btn-row").classList.remove("hidden");
  }
}

// ── 결과 렌더링 ──────────────────────────────────────────────────────
function renderResult($, data, soapText, patientId) {
  const alarm     = data.alarm || "NONE";
  const cfg       = ALARM_CONFIG[alarm] || ALARM_CONFIG.NONE;
  const condLabel = CONDITION_LABELS[data.condition] || data.condition || "";

  const banner = $("alarm-banner");
  banner.className = `alarm-banner ${cfg.cssClass}`;
  $("alarm-icon").textContent       = cfg.icon;
  $("alarm-level-text").textContent = cfg.text;
  $("alarm-condition").textContent  = condLabel;

  if (data.trigger) {
    $("trigger-row").classList.remove("hidden");
    $("trigger-text").textContent = data.trigger;
  } else {
    $("trigger-row").classList.add("hidden");
  }

  const matchedList = $("matched-list");
  matchedList.innerHTML = "";
  if (data.matched?.length) {
    $("matched-section").classList.remove("hidden");
    data.matched.forEach(label => {
      const li = document.createElement("li");
      li.textContent = label;
      matchedList.appendChild(li);
    });
  } else {
    $("matched-section").classList.add("hidden");
  }

  const ctx = data.patient_context;
  if (ctx?.session_count > 0) {
    $("context-section").classList.remove("hidden");
    $("context-text").textContent = ctx.summary || "";
  } else {
    $("context-section").classList.add("hidden");
  }

  // reset action area
  $("btn-referral").classList.add("hidden");
  $("yellow-actions").classList.add("hidden");
  $("yellow-status").classList.add("hidden");
  $("referral-letter").classList.add("hidden");
  $("btn-copy-referral").classList.add("hidden");

  if (alarm === "RED" || alarm === "YELLOW") {
    $("referral-section").classList.remove("hidden");
    $("referral-section").dataset.alertId = data.alert_id || "";
    if (alarm === "RED") {
      $("btn-referral").classList.remove("hidden");
    } else {
      $("yellow-actions").classList.remove("hidden");
    }
  } else {
    $("referral-section").classList.add("hidden");
  }

  const score       = data.score || 0;
  const scoreColors = { RED: "#dc2626", YELLOW: "#d97706", NONE: "#16a34a" };
  $("score-bar").style.width      = `${Math.round(score * 100)}%`;
  $("score-bar").style.background = scoreColors[alarm] || "#6b7280";
  $("score-value").textContent    = `${Math.round(score * 100)}%`;

  showScreen($, "result");
}

// ── 알람 액션 (referral / monitor) ───────────────────────────────────
async function handleAlarmAction($, action) {
  const alertId = $("referral-section").dataset.alertId;
  if (!alertId) return;

  const btnReferral = $("btn-referral");
  const btnMonitor  = $("btn-monitor");
  const btnEscalate = $("btn-escalate");

  [btnReferral, btnMonitor, btnEscalate].forEach(b => {
    if (b) { b.disabled = true; b.style.opacity = ".6"; }
  });

  try {
    const res = await fetch(`${state.serverUrl}/api/pt/alerts/${alertId}/action/`, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Token ${state.token}`,
      },
      body: JSON.stringify({ action }),
    });

    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    if (action === "monitor") {
      $("yellow-actions").classList.add("hidden");
      const status = $("yellow-status");
      status.textContent = "✓ Flagged for monitoring — escalate to referral if condition worsens.";
      status.classList.remove("hidden");
      // keep escalate available via status area re-render
      const escalateBtn = document.createElement("button");
      escalateBtn.className = "btn";
      escalateBtn.style.cssText = "background:#dc2626;color:#fff;width:100%;margin-top:8px;";
      escalateBtn.textContent = "📄 Escalate to Referral";
      escalateBtn.addEventListener("click", () => handleAlarmAction($, "referral"));
      status.after(escalateBtn);
    } else {
      const letter = data.referral_letter || "";
      $("yellow-actions").classList.add("hidden");
      $("yellow-status").classList.add("hidden");
      if (btnReferral) btnReferral.classList.add("hidden");
      $("referral-letter").textContent = letter;
      $("referral-letter").classList.remove("hidden");
      $("btn-copy-referral").classList.remove("hidden");
    }
  } catch (err) {
    [btnReferral, btnMonitor, btnEscalate].forEach(b => {
      if (b) { b.disabled = false; b.style.opacity = "1"; }
    });
    alert("Failed: " + err.message);
  }
}

// ── 패널 표시/숨김 ───────────────────────────────────────────────────
function showPanel() {
  if (!document.getElementById("sp-host")) {
    createPanel();
  }
  const panel = shadowRoot.getElementById("sp-panel");
  panel.style.display = "flex";
  panelVisible = true;
}

function hidePanel() {
  if (!shadowRoot) return;
  const panel = shadowRoot.getElementById("sp-panel");
  panel.style.display = "none";
  panelVisible = false;
}

// ── 메시지 수신 (background.js → toggle) ────────────────────────────
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type !== "TOGGLE_PANEL") return;
  if (panelVisible) {
    hidePanel();
  } else {
    showPanel();
  }
});

// ── 유틸 ────────────────────────────────────────────────────────────
function generatePatientId() {
  const now = new Date();
  return `PT-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,"0")}${String(now.getDate()).padStart(2,"0")}-${Math.floor(Math.random()*10000).toString().padStart(4,"0")}`;
}

function highlightActiveServer($) {
  ["srv-production", "srv-local"].forEach(id => {
    const btn = $(id);
    if (!btn) return;
    const active = btn.dataset.url === state.serverUrl;
    btn.style.borderColor = active ? "#4f46e5" : "#e5e7eb";
    btn.style.background  = active ? "#eef2ff" : "#f9fafb";
  });
}

function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}

})();
