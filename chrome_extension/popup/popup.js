/**
 * Sage Pontus — PT Red Flag Alert
 * popup.js: 로그인 → SOAP 입력 → 분석 → 결과 표시
 */

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

// ── 상태 ───────────────────────────────────────────────────────────
let state = { token: null, username: null, serverUrl: DEFAULT_SERVER };

// ── DOM 참조 ────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── 초기화 ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  const stored = await chrome.storage.local.get(["token", "username", "serverUrl"]);
  state.token     = stored.token     || null;
  state.username  = stored.username  || null;
  state.serverUrl = stored.serverUrl || DEFAULT_SERVER;

  $("server-url-input").value = state.serverUrl;

  if (state.token) {
    showAnalyzeScreen();
  } else {
    showScreen("login");
  }

  bindEvents();
});

// ── 화면 전환 ────────────────────────────────────────────────────────
function showScreen(name) {
  ["login", "analyze", "result"].forEach(s => {
    $(`screen-${s}`).classList.toggle("hidden", s !== name);
  });
}

function showAnalyzeScreen() {
  $("top-username").textContent       = state.username || "";
  $("top-username-result").textContent = state.username || "";
  showScreen("analyze");
}

// ── 이벤트 바인딩 ───────────────────────────────────────────────────
function bindEvents() {
  // 로그인
  $("btn-login").addEventListener("click", handleLogin);
  $("login-password").addEventListener("keydown", e => {
    if (e.key === "Enter") handleLogin();
  });

  // 설정 패널 토글
  $("btn-show-settings").addEventListener("click", () => {
    $("settings-panel").classList.toggle("hidden");
  });
  $("btn-save-settings").addEventListener("click", async () => {
    const url = $("server-url-input").value.trim().replace(/\/$/, "");
    if (url) {
      state.serverUrl = url;
      await chrome.storage.local.set({ serverUrl: url });
      $("settings-panel").classList.add("hidden");
    }
  });

  // 로그아웃
  $("btn-logout").addEventListener("click", handleLogout);

  // 붙여넣기
  $("btn-paste").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      $("soap-text").value = text;
    } catch {
      $("soap-text").focus();
      document.execCommand("paste");
    }
  });

  // 지우기
  $("btn-clear").addEventListener("click", () => {
    $("soap-text").value   = "";
    $("patient-id").value  = "";
  });

  // 분석
  $("btn-analyze").addEventListener("click", handleAnalyze);

  // 돌아가기
  $("btn-back").addEventListener("click", showAnalyzeScreen);

  // 리퍼럴 레터 생성
  $("btn-referral").addEventListener("click", handleGenerateReferral);

  // 레터 복사
  $("btn-copy-referral").addEventListener("click", () => {
    const text = $("referral-letter").textContent;
    navigator.clipboard.writeText(text).then(() => {
      $("btn-copy-referral").textContent = "✅ Copied!";
      setTimeout(() => { $("btn-copy-referral").textContent = "📋 Copy letter"; }, 2000);
    });
  });
}

// ── 로그인 ──────────────────────────────────────────────────────────
async function handleLogin() {
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
    showAnalyzeScreen();

  } catch (err) {
    showError(errEl, err.message || "Login failed. Check server URL.");
  } finally {
    $("btn-login").textContent = "Sign In";
    $("btn-login").disabled    = false;
  }
}

// ── 로그아웃 ─────────────────────────────────────────────────────────
async function handleLogout() {
  state.token    = null;
  state.username = null;
  await chrome.storage.local.remove(["token", "username"]);
  showScreen("login");
}

// ── 분석 ────────────────────────────────────────────────────────────
async function handleAnalyze() {
  const soapText  = $("soap-text").value.trim();
  const patientId = $("patient-id").value.trim() || generatePatientId();

  if (!soapText) {
    $("soap-text").focus();
    return;
  }

  $("btn-analyze").disabled    = true;
  $("analyze-loading").classList.remove("hidden");
  $("btn-row")?.classList.add("hidden");

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
        generate_referral: false,  // 결과 화면에서 버튼으로 요청
      }),
    });

    if (res.status === 401) {
      // 토큰 만료 → 로그인으로
      await handleLogout();
      return;
    }

    if (!res.ok) throw new Error(`Server error: ${res.status}`);

    const data = await res.json();
    renderResult(data, soapText, patientId);

  } catch (err) {
    alert("Analysis failed: " + err.message);
  } finally {
    $("btn-analyze").disabled    = false;
    $("analyze-loading").classList.add("hidden");
    $("btn-row")?.classList.remove("hidden");
  }
}

// ── 결과 렌더링 ──────────────────────────────────────────────────────
function renderResult(data, soapText, patientId) {
  const alarm  = data.alarm || "NONE";
  const cfg    = ALARM_CONFIG[alarm] || ALARM_CONFIG.NONE;
  const condLabel = CONDITION_LABELS[data.condition] || data.condition || "";

  // 배너
  const banner = $("alarm-banner");
  banner.className = `alarm-banner ${cfg.cssClass}`;
  $("alarm-icon").textContent       = cfg.icon;
  $("alarm-level-text").textContent = cfg.text;
  $("alarm-condition").textContent  = condLabel;

  // 트리거
  if (data.trigger) {
    $("trigger-row").classList.remove("hidden");
    $("trigger-text").textContent = data.trigger;
  } else {
    $("trigger-row").classList.add("hidden");
  }

  // 매칭 지표
  const matchedSection = $("matched-section");
  const matchedList    = $("matched-list");
  matchedList.innerHTML = "";
  if (data.matched?.length) {
    matchedSection.classList.remove("hidden");
    data.matched.forEach(label => {
      const li = document.createElement("li");
      li.textContent = label;
      matchedList.appendChild(li);
    });
  } else {
    matchedSection.classList.add("hidden");
  }

  // 이전 세션 컨텍스트
  const ctx = data.patient_context;
  if (ctx?.session_count > 0) {
    $("context-section").classList.remove("hidden");
    $("context-text").textContent = ctx.summary || "";
  } else {
    $("context-section").classList.add("hidden");
  }

  // 리퍼럴 섹션 — RED만 표시
  const referralSection = $("referral-section");
  if (alarm === "RED") {
    referralSection.classList.remove("hidden");
    $("referral-letter").classList.add("hidden");
    $("btn-copy-referral").classList.add("hidden");
    // 현재 분석 데이터를 버튼에 저장
    $("btn-referral").dataset.alertId   = data.alert_id || "";
    $("btn-referral").dataset.patientId = patientId;
    $("btn-referral").dataset.soapText  = soapText;
  } else {
    referralSection.classList.add("hidden");
  }

  // 점수 바
  const score     = data.score || 0;
  const scoreBar  = $("score-bar");
  const scoreColors = { RED: "#dc2626", YELLOW: "#d97706", NONE: "#16a34a" };
  scoreBar.style.width      = `${Math.round(score * 100)}%`;
  scoreBar.style.background = scoreColors[alarm] || "#6b7280";
  $("score-value").textContent = `${Math.round(score * 100)}%`;

  showScreen("result");
}

// ── 리퍼럴 레터 생성 ─────────────────────────────────────────────────
async function handleGenerateReferral() {
  const btn     = $("btn-referral");
  const alertId = btn.dataset.alertId;

  if (!alertId) return;

  btn.textContent = "Generating…";
  btn.disabled    = true;

  try {
    const res = await fetch(`${state.serverUrl}/api/pt/alerts/${alertId}/referral/`, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Token ${state.token}`,
      },
    });

    if (!res.ok) throw new Error("Failed to generate letter");

    const data   = await res.json();
    const letter = data.referral_letter || "";

    if (letter) {
      $("referral-letter").textContent = letter;
      $("referral-letter").classList.remove("hidden");
      $("btn-copy-referral").classList.remove("hidden");
      btn.textContent = "📄 Referral Letter Generated";
    }
  } catch (err) {
    btn.textContent = "📄 Generate Referral Letter";
    alert("Failed: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

// ── 유틸 ────────────────────────────────────────────────────────────
function generatePatientId() {
  const now = new Date();
  return `PT-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,"0")}${String(now.getDate()).padStart(2,"0")}-${Math.floor(Math.random()*10000).toString().padStart(4,"0")}`;
}

function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}
