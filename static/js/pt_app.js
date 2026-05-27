let allPatients = [];
let activePatientId = null;
let currentPatientId = null;

// ── 리퍼럴 추적 Phase 1 ──────────────────────────────
function buildReferralTracker(s) {
  if (!s.alert_id) return '';
  const sent      = !!s.referral_sent_at;
  const followup  = s.referral_followup_checked;

  if (followup) {
    return `<span style="font-size:11px;color:#22c55e;font-weight:600;align-self:center;">✓ Follow-up Confirmed</span>`;
  }
  if (sent) {
    return `
      <span style="font-size:11px;color:#60a5fa;align-self:center;">
        Sent ${s.referral_sent_at}${s.referral_sent_to_email ? ' → ' + s.referral_sent_to_email : ''}
      </span>
      <button class="pt-letter-btn" onclick="markFollowup(${s.alert_id}, this)"
        style="background:#166534;border-color:#166534;">✓ Follow-up Done</button>`;
  }
  return `
    <button class="pt-letter-btn" onclick="openSendModal(${s.alert_id}, this)"
      style="background:#1e40af;border-color:#1e40af;">📧 Send to Doctor</button>`;
}

function printReferralLetter(alertId) {
  if (!alertId) return;
  window.open(`/pt/api/alerts/${alertId}/print/`, '_blank');
}

function openSendModal(alertId, btn) {
  const email = prompt('Physician email address (leave blank to mark as sent without email):');
  if (email === null) return;  // cancelled
  sendReferral(alertId, email.trim(), btn);
}

async function sendReferral(alertId, toEmail, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  try {
    const resp = await fetch(`/pt/api/alerts/${alertId}/send/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ to_email: toEmail }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.statusText);

    const msg = data.email_sent
      ? (data.delivered ? `✓ Email delivered to ${toEmail}` : `⚠ Send failed — marked as sent manually`)
      : '✓ Marked as sent (no email)';
    alert(msg);
    loadPatientSessions(activePatientId);  // 화면 갱신
  } catch (e) {
    alert('Error: ' + e.message);
    if (btn) { btn.disabled = false; btn.textContent = '📧 Send to Doctor'; }
  }
}

async function markFollowup(alertId, btn) {
  if (!confirm('Confirm that the patient followed up with the physician?')) return;
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  try {
    const resp = await fetch(`/pt/api/alerts/${alertId}/followup/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF },
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.statusText);
    loadPatientSessions(activePatientId);
  } catch (e) {
    alert('Error: ' + e.message);
    if (btn) { btn.disabled = false; btn.textContent = '✓ Follow-up Done'; }
  }
}

// ── 오디오 녹음 + Scribe 전송 ─────────────────────────
let _mediaRecorder = null;
let _audioChunks   = [];

async function toggleRecording() {
  const btn = document.getElementById('mic-btn');
  const recStatus  = document.getElementById('rec-status');
  const scribeStatus = document.getElementById('scribe-status');

  if (_mediaRecorder && _mediaRecorder.state === 'recording') {
    // ── 녹음 중지 ──
    _mediaRecorder.stop();
    btn.textContent = '🎙 Record';
    btn.style.background = '#2d3748';
    recStatus.style.display = 'none';
    return;
  }

  // ── 녹음 시작 ──
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    alert('마이크 권한이 필요합니다: ' + e.message);
    return;
  }

  _audioChunks = [];
  _mediaRecorder = new MediaRecorder(stream);

  _mediaRecorder.ondataavailable = e => { if (e.data.size > 0) _audioChunks.push(e.data); };

  _mediaRecorder.onstop = async () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(_audioChunks, { type: 'audio/webm' });
    scribeStatus.style.display = 'block';
    scribeStatus.textContent = '⏳ Transcribing...';

    const form = new FormData();
    form.append('audio', blob, 'session.webm');

    try {
      const resp = await fetch(URLS.transcribe, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF },
        body: form,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || resp.statusText);

      // S / O 탭에 자동 채우기 (기존 텍스트가 있으면 뒤에 추가)
      const sEl = document.getElementById('inp-S');
      const oEl = document.getElementById('inp-O');
      if (data.S) sEl.value = (sEl.value ? sEl.value + '\n' : '') + data.S;
      if (data.O) oEl.value = (oEl.value ? oEl.value + '\n' : '') + data.O;

      scribeStatus.textContent = `✓ Transcribed (${data.provider}) — S/O panes filled`;
      setTimeout(() => { scribeStatus.style.display = 'none'; }, 4000);
    } catch (e) {
      scribeStatus.textContent = '✗ ' + e.message;
      setTimeout(() => { scribeStatus.style.display = 'none'; }, 6000);
    }
  };

  _mediaRecorder.start();
  btn.textContent = '⏹ Stop';
  btn.style.background = '#742a2a';
  recStatus.style.display = 'inline';
}

// ── S/O/A/P 구조화 입력 + Red Flag 칩 ─────────────────
let _confirmedChips = new Set();
let _activeSoapTab  = 'S';

const _soapChipDefs = {
  S: [
    { id:'RF_011', label:'Night Pain',         alarm:'RED'    },
    { id:'RF_009', label:'Cancer Hx',          alarm:'RED'    },
    { id:'RF_010', label:'Weight Loss',        alarm:'RED'    },
    { id:'RF_013', label:'Fever',              alarm:'RED'    },
    { id:'RF_002', label:'Bladder Dysfx',      alarm:'RED'    },
    { id:'RF_003', label:'Bowel Dysfx',        alarm:'RED'    },
    { id:'RF_001', label:'Saddle Anesthesia',  alarm:'RED'    },
    { id:'RF_018', label:'Sudden Onset',       alarm:'RED'    },
    { id:'RF_022', label:'Night Sweats',       alarm:'YELLOW' },
    { id:'RF_019', label:'Morning Stiffness',  alarm:'YELLOW' },
    { id:'RF_020', label:'Better w/ Exercise', alarm:'YELLOW' },
    { id:'RF_012', label:'No Improvement 6wk', alarm:'YELLOW' },
    { id:'RF_024', label:'Fatigue',            alarm:'YELLOW' },
    { id:'RF_025', label:'Age >50 1st LBP',    alarm:'YELLOW' },
  ],
  O: [
    { id:'RF_004', label:'Bilateral LE Sx',    alarm:'RED'    },
    { id:'RF_005', label:'Progressive Neuro',  alarm:'RED'    },
    { id:'RF_006', label:'Major Trauma',       alarm:'RED'    },
    { id:'RF_008', label:'Point Tender Spine', alarm:'RED'    },
    { id:'RF_016', label:'Pulsating Mass',     alarm:'RED'    },
    { id:'RF_017', label:'Pain @ Rest',        alarm:'RED'    },
    { id:'RF_014', label:'Recent Infection',   alarm:'RED'    },
    { id:'RF_021', label:'Alt. Buttock Pain',  alarm:'YELLOW' },
    { id:'RF_007', label:'Osteoporosis Hx',    alarm:'YELLOW' },
    { id:'RF_015', label:'Immunocompromised',  alarm:'YELLOW' },
    { id:'RF_023', label:'Steroid Use',        alarm:'YELLOW' },
  ],
};

function switchSoapTab(tab) {
  _activeSoapTab = tab;
  ['S','O','A','P'].forEach(t => {
    document.getElementById(`stab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`soap-pane-${t}`).style.display = t === tab ? 'block' : 'none';
  });
}

function toggleChip(rfId, alarmLevel) {
  if (_confirmedChips.has(rfId)) {
    _confirmedChips.delete(rfId);
  } else {
    _confirmedChips.add(rfId);
  }
  // re-render only the section that owns this chip
  ['S','O'].forEach(sec => {
    if (_soapChipDefs[sec].some(c => c.id === rfId)) _renderChipSection(sec);
  });
}

function _renderChipSection(sec) {
  const el = document.getElementById(`chips-${sec}`);
  if (!el) return;
  el.innerHTML = _soapChipDefs[sec].map(c => {
    const on  = _confirmedChips.has(c.id);
    const cls = on ? `rf-chip confirmed-${c.alarm}` : 'rf-chip';
    return `<button id="chip-${c.id}" class="${cls}"
              onclick="toggleChip('${c.id}','${c.alarm}')"
            >${on ? '✓ ' : ''}${c.label}</button>`;
  }).join('');
}

// ── 초기화 ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (APP_CONTEXT.isAuthenticated) {
  document.getElementById('inp-date').value = new Date().toISOString().split('T')[0];
  loadPatients();
  loadAlarmBadge();
  _renderChipSection('S');
  _renderChipSection('O');
  }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeSlidePanel(); closeDocModal(); }
});

document.addEventListener('click', e => {
  if (e.target === document.getElementById('doc-modal-overlay')) closeDocModal();
});

// ── 환자 목록 로드 ───────────────────────────────────
async function loadAlarmBadge() {
  try {
    const r = await fetch('/pt/api/alarms/');
    const d = await r.json();
    const redCount = d.counts.red || 0;
    const badge = document.getElementById('alarm-badge');
    if (redCount > 0) {
      badge.textContent = redCount;
      badge.style.display = 'inline-block';
    }
  } catch(e) {}
}

async function loadPatients() {
  try {
    const r = await fetch('/pt/api/patients/', {headers: {'X-Requested-With': 'XMLHttpRequest'}});
    const d = await r.json();
    allPatients = d.patients || [];
    renderPatientList(allPatients);
  } catch(e) {
    document.getElementById('patient-list').innerHTML =
      '<div style="padding:12px;font-size:12px;color:#94a3b8;">불러오기 실패</div>';
  }
}

function renderPatientList(patients) {
  const el = document.getElementById('patient-list');
  const countEl = document.getElementById('patient-count');
  if (countEl) countEl.textContent = patients.length || '';

  if (!patients.length) {
    el.innerHTML = '<div style="padding:12px;font-size:12px;color:#64748b;">환자 없음</div>';
    return;
  }
  el.innerHTML = patients.map(p => `
    <div class="pt-patient-item${p.patient_id===activePatientId?' active':''}"
         onclick="selectPatient('${esc(p.patient_id)}','${esc(p.patient_name||p.patient_id)}')">
      <span class="pt-alarm-dot ${p.latest_alarm}"></span>
      <div class="pt-patient-info">
        <div class="pt-patient-name">${esc(p.patient_name||p.patient_id)}</div>
        <div class="pt-patient-meta">
          <span style="color:#6366f1;font-weight:600;">${esc(p.patient_id)}</span>
          · ${p.session_count}세션 · ${p.last_session}
        </div>
      </div>
      <span class="pt-patient-alarm-badge ${p.latest_alarm}">${p.latest_alarm === 'NONE' ? '' : p.latest_alarm}</span>
    </div>
  `).join('');
}

function filterPatients(q) {
  const filtered = q
    ? allPatients.filter(p => (p.patient_name+p.patient_id).toLowerCase().includes(q.toLowerCase()))
    : allPatients;
  renderPatientList(filtered);
}

// ── 환자 선택 → 히스토리 ─────────────────────────────
function _showView(name) {
  ['view-new', 'view-history', 'view-alarms'].forEach(id => {
    document.getElementById(id).style.display = id === name ? 'block' : 'none';
  });
  const btn = document.getElementById('menu-alarms');
  btn.style.background = name === 'view-alarms' ? 'rgba(99,102,241,.2)' : 'transparent';
  btn.style.color      = name === 'view-alarms' ? '#a5b4fc' : '#94a3b8';
}

async function selectPatient(pid, pname) {
  activePatientId = pid;
  currentPatientId = pid;
  renderPatientList(allPatients);
  _showView('view-history');
  document.getElementById('history-title').textContent = pname || pid;
  document.getElementById('session-list-items').innerHTML =
    '<div style="padding:24px;text-align:center;font-size:13px;color:#9ca3af;">불러오는 중...</div>';
  document.getElementById('detail-panel').innerHTML =
    '<div class="pt-detail-empty"><div style="font-size:36px;margin-bottom:12px;">⏳</div><div style="font-size:14px;">불러오는 중...</div></div>';

  try {
    const r = await fetch(`/pt/api/patients/${encodeURIComponent(pid)}/sessions/`);
    const d = await r.json();
    renderHistory(d);
  } catch(e) {
    document.getElementById('session-list-items').innerHTML =
      '<div style="color:#dc2626;padding:16px;font-size:13px;">불러오기 실패</div>';
  }
}

let _sessions = [];

function renderHistory(d) {
  _sessions = d.sessions || [];
  _sessions.forEach(s => { if (s.clinical_context) _sessionCtxCache[s.id] = s.clinical_context; });
  _loadSessionOverrides(_sessions);   // 저장된 섹션 오버라이드 복원
  const listEl = document.getElementById('session-list-items');

  if (!_sessions.length) {
    listEl.innerHTML = '<div style="padding:24px;text-align:center;font-size:13px;color:#9ca3af;">세션 없음</div>';
    document.getElementById('detail-panel').innerHTML =
      '<div class="pt-detail-empty"><div style="font-size:36px;margin-bottom:12px;">📋</div><div style="font-size:14px;">세션이 없습니다</div></div>';
    return;
  }

  listEl.innerHTML = _sessions.map((s, i) => `
    <div class="pt-session-row${i===0?' active':''}" id="srow-${s.id}" onclick="showSessionDetail(${i})">
      <div class="pt-session-row-info">
        <div class="pt-session-row-date">${s.session_date}</div>
        <div class="pt-session-row-meta">Risk ${s.critical_score}%${s.triggered_condition ? ' · '+s.triggered_condition : ''}</div>
      </div>
      <span class="pt-session-badge badge-${s.alarm_level}">${alarmLabel(s.alarm_level)}</span>
    </div>
  `).join('');

  // 탭 구조 초기화
  const panel = document.getElementById('detail-panel');
  panel.innerHTML = `
    <div class="detail-tab-bar">
      <button class="detail-tab-btn active" id="dtab-session" onclick="switchDetailTab('session')">📋 Session Detail</button>
      <button class="detail-tab-btn" id="dtab-docs" onclick="switchDetailTab('docs')">📄 Documents</button>
    </div>
    <div id="detail-session-content" style="display:flex;flex-direction:column;gap:16px;"></div>
    <div id="detail-docs-content" style="display:none;"></div>
  `;

  showSessionDetail(0);
  renderDocumentsTab(d.patient_id, d.patient_name);
}

function showSessionDetail(idx) {
  const s = _sessions[idx];
  if (!s) return;

  // 좌측 리스트 active 표시
  _sessions.forEach((_, i) => {
    const row = document.getElementById(`srow-${_sessions[i].id}`);
    if (row) row.classList.toggle('active', i === idx);
  });

  const panel = document.getElementById('detail-session-content') || document.getElementById('detail-panel');
  const alarmColors = {RED:'#dc2626', YELLOW:'#d97706', NONE:'#16a34a'};
  const alarmIcons  = {RED:'🚨', YELLOW:'⚠️', NONE:'✅'};
  let html = '';

  // ── SOAP 카드 ──
  html += `
    <div class="pt-soap-card">
      <div class="pt-soap-card-header">
        <span>${alarmIcons[s.alarm_level]}</span>
        <span>${s.session_date}</span>
        <span class="pt-session-badge badge-${s.alarm_level}" style="margin-left:4px;">${alarmLabel(s.alarm_level)}</span>
        ${s.triggered_condition ? `<span style="font-size:12px;color:#6b7280;margin-left:4px;">${esc(s.triggered_condition)}</span>` : ''}
        <span style="margin-left:auto;font-size:12px;color:#9ca3af;">Risk ${s.critical_score}%</span>
        <button id="soap-compare-btn" onclick="toggleSoapCompare()"
          style="margin-left:8px;padding:3px 9px;border:1px solid #c7d2fe;border-radius:5px;
                 background:transparent;color:#6366f1;font-size:11px;cursor:pointer;
                 transition:background .15s;"
          onmouseover="this.style.background='#eef2ff'"
          onmouseout="this.style.background='transparent'"
          title="원본 / 섹션 제목 비교">⇄ 비교</button>
        <button id="soap-copy-btn" onclick="copySessionSoap(this, ${s.id})"
          style="margin-left:4px;padding:3px 9px;border:1px solid #d1d5db;border-radius:5px;
                 background:transparent;color:#6b7280;font-size:11px;cursor:pointer;
                 transition:background .15s;"
          onmouseover="this.style.background='#f9fafb'"
          onmouseout="this.style.background='transparent'"
          title="SOAP 복사">⎘ 복사</button>
        <button onclick="deleteSession(${s.id}, '${currentPatientId}')"
          style="margin-left:4px;padding:3px 8px;border:1px solid #fca5a5;border-radius:5px;
                 background:transparent;color:#ef4444;font-size:11px;cursor:pointer;
                 transition:background .15s;"
          onmouseover="this.style.background='#fef2f2'"
          onmouseout="this.style.background='transparent'"
          title="이 세션 삭제">🗑 삭제</button>
        <button onclick="openSoapEditor(${s.id})"
          style="margin-left:4px;padding:3px 8px;border:1px solid #c7d2fe;border-radius:5px;
                 background:transparent;color:#6366f1;font-size:11px;cursor:pointer;
                 transition:background .15s;"
          onmouseover="this.style.background='#eef2ff'"
          onmouseout="this.style.background='transparent'"
          title="SOAP 수정 저장">✏ 수정</button>
      </div>
      <div id="soap-body-single" class="pt-soap-body"><div class="soap-display">${formatSoap(s.soap_text, s.id, s.clinical_context)}</div></div>
      <div id="soap-body-compare" class="soap-compare" style="display:none;">
        <div class="soap-compare-col">
          <div class="soap-compare-label">원본 (Raw)</div>
          <div class="soap-display">${esc(s.soap_text)}</div>
        </div>
        <div class="soap-compare-col">
          <div class="soap-compare-label formatted">섹션 제목 추가 (Formatted)</div>
          <div class="soap-display">${formatSoap(s.soap_text, s.id, s.clinical_context)}</div>
        </div>
      </div>
      <div id="soap-editor-${s.id}" style="display:none;padding:12px 14px;border-top:1px solid #f1f5f9;">
        <div style="font-size:11px;color:#6b7280;margin-bottom:6px;">✏ SOAP 수정 — 원본과 수정본이 paired data로 저장됩니다</div>
        <textarea id="soap-edit-ta-${s.id}"
          style="width:100%;height:180px;padding:10px;border:1.5px solid #a5b4fc;border-radius:8px;
                 font-size:12px;font-family:'Courier New',monospace;resize:vertical;box-sizing:border-box;"></textarea>
        <div style="display:flex;gap:8px;margin-top:8px;justify-content:flex-end;">
          <button onclick="closeSoapEditor(${s.id})"
            style="padding:5px 14px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;
                   background:#fff;cursor:pointer;">취소</button>
          <button onclick="saveSoapEdit(${s.id})"
            style="padding:5px 14px;background:#6366f1;color:#fff;border:none;border-radius:6px;
                   font-size:12px;font-weight:600;cursor:pointer;">저장</button>
        </div>
      </div>
    </div>`;

  // ── Detected Indicators 카드 (알람 있을 때만) ──
  if (s.alarm_level !== 'NONE' && s.matched_indicators && s.matched_indicators.length) {
    html += `
      <div class="pt-indicators-card">
        <div class="pt-card-header" style="padding:13px 18px;border-bottom:1px solid #f1f5f9;font-size:13px;font-weight:700;color:#374151;">
          ⚑ Detected Red Flag Indicators
        </div>
        <div style="padding:14px 18px;display:flex;flex-wrap:wrap;gap:8px;">
          ${s.matched_indicators.map(m => `
            <span style="padding:5px 12px;border-radius:99px;font-size:12px;font-weight:600;
              background:${s.alarm_level==='RED'?'#fef2f2':'#fffbeb'};
              color:${s.alarm_level==='RED'?'#dc2626':'#d97706'};
              border:1px solid ${s.alarm_level==='RED'?'#fca5a5':'#fcd34d'};">⚑ ${esc(m)}</span>
          `).join('')}
        </div>
      </div>`;
  }

  panel.innerHTML = html;
}

// ── 슬라이드 패널 ────────────────────────────────────────────
function openSlidePanel(s) {
  const alarmColor = {RED:'#dc2626', YELLOW:'#d97706', NONE:'#16a34a'};
  const alarmBg    = {RED:'#fef2f2', YELLOW:'#fffbeb', NONE:'#f0fdf4'};
  const alarmIcon  = {RED:'🚨', YELLOW:'⚠️', NONE:'✅'};

  // 헤더
  document.getElementById('slide-panel-title').textContent =
    `${s.patient_name || s.patient_id}  ·  ${s.session_date}`;
  const badge = document.getElementById('slide-panel-badge');
  badge.textContent = `${alarmIcon[s.alarm_level]} ${s.alarm_level}`;
  badge.style.cssText += `;background:${alarmBg[s.alarm_level]};color:${alarmColor[s.alarm_level]};border:1px solid ${alarmColor[s.alarm_level]}40;`;

  let html = '';

  // 스코어 바
  html += `
    <div style="display:flex;align-items:center;gap:10px;padding:12px 14px;
                background:${alarmBg[s.alarm_level]};border-radius:10px;border:1px solid ${alarmColor[s.alarm_level]}30;">
      <div style="flex:1;">
        <div style="font-size:11px;color:#6b7280;margin-bottom:5px;">Risk Score</div>
        <div style="height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;">
          <div style="width:${s.critical_score}%;height:100%;background:${alarmColor[s.alarm_level]};border-radius:4px;"></div>
        </div>
      </div>
      <div style="font-size:22px;font-weight:800;color:${alarmColor[s.alarm_level]};min-width:48px;text-align:right;">${s.critical_score}%</div>
    </div>`;

  // 감지 지표
  if (s.matched_indicators && s.matched_indicators.length) {
    html += `
      <div>
        <div style="font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;
                    letter-spacing:.5px;margin-bottom:8px;">⚑ Detected Indicators</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          ${s.matched_indicators.map(m => `
            <span style="font-size:12px;padding:4px 10px;border-radius:99px;font-weight:600;
              background:${alarmBg[s.alarm_level]};color:${alarmColor[s.alarm_level]};
              border:1px solid ${alarmColor[s.alarm_level]}50;">${esc(m)}</span>
          `).join('')}
        </div>
      </div>`;
  }

  // SOAP + Letter 2컬럼
  const borderColor = s.alarm_level === 'RED' ? '#dc2626' : '#d97706';
  html += `<div class="slide-cols" id="slide-cols">`;

  // 좌: SOAP Note
  html += `
    <div class="slide-col" id="slide-left-col" style="flex:1;">
      <div class="slide-col-title">🩺 SOAP Note</div>
      <div class="soap-display" style="flex:1;min-height:0;overflow-y:auto;">${s.soap_text ? formatSoap(s.soap_text, s.id, s.clinical_context) : '<span style="color:#9ca3af;">내용 없음</span>'}</div>
    </div>`;

  // 드래그 핸들
  html += `<div class="slide-divider" id="slide-divider"></div>`;

  // 우: Referral Letter
  html += `
    <div class="slide-col" style="flex:1;">
      <div class="slide-col-title" style="display:flex;align-items:center;justify-content:space-between;">
        <span>📄 Referral Letter</span>
        <div style="display:flex;gap:6px;">
          <button onclick="slidePrintLetter()" style="padding:3px 9px;border:1px solid #d1d5db;border-radius:6px;
                  background:#fff;font-size:11px;cursor:pointer;font-weight:400;">🖨️ Print</button>
          <button id="slide-copy-btn" onclick="slideCopyLetter(this)"
                  style="padding:3px 9px;border:1px solid #6366f1;border-radius:6px;
                  background:#6366f1;color:#fff;font-size:11px;cursor:pointer;">📋 Copy</button>
        </div>
      </div>
      <div id="slide-letter-text" style="background:#fff;border:2px solid ${borderColor};
           color:#1e293b;font-family:'Courier New',monospace;font-size:11.5px;border-radius:8px;
           padding:14px;flex:1;min-height:0;overflow-y:auto;white-space:pre-wrap;
           word-break:break-word;line-height:1.7;">${s.referral_letter ? formatLetter(s.referral_letter) : '<span style="color:#9ca3af;">Letter 없음</span>'}</div>
    </div>`;

  html += `</div>`;

  document.getElementById('slide-panel-body').innerHTML = html;
  setupSlideDivider();
  document.getElementById('slide-panel').classList.add('open');
  document.getElementById('slide-overlay').classList.add('open');
}

// ── Alarm 세션 상세 모달 (doc-modal 재사용) ───────────────────────
let _currentAlertId  = null;
let _pendingDecision = null;

function openAlarmModal(s) {
  _currentAlertId = s.alert_id || null;
  const color  = {RED:'#dc2626', YELLOW:'#d97706'}[s.alarm_level] || '#16a34a';
  const bg     = {RED:'#fef2f2', YELLOW:'#fffbeb'}[s.alarm_level] || '#f0fdf4';
  const icon   = {RED:'🚨', YELLOW:'⚠️'}[s.alarm_level] || '✅';
  const label  = {RED:'RED ALERT', YELLOW:'YELLOW FLAG'}[s.alarm_level] || 'CLEAR';

  // 헤더
  document.getElementById('doc-modal-title').textContent =
    `${s.patient_name || s.patient_id}  ·  ${s.session_date}`;

  // Copy / Print → referral letter 대상
  _docModalCopyText = s.referral_letter || '';
  const copyBtn = document.getElementById('doc-modal-copy-btn');
  if (s.referral_letter) {
    copyBtn.textContent = '📋 Copy Letter';
    copyBtn.style.display = '';
  } else {
    copyBtn.style.display = 'none';
  }

  // 바디 — text-mode 해제 (rich HTML 모드)
  const body = document.getElementById('doc-modal-body');
  body.classList.remove('text-mode');

  let html = '';

  // ── Alarm 배너 ──
  html += `
    <div class="alarm-section" style="display:flex;align-items:center;gap:14px;
              padding:14px 18px;border-radius:10px;
              background:${bg};border:2px solid ${color};">
      <span style="font-size:32px;line-height:1;">${icon}</span>
      <div style="flex:1;min-width:0;">
        <div style="font-size:16px;font-weight:900;color:${color};">${label}</div>
        ${s.triggered_condition
          ? `<div style="font-size:12px;color:#6b7280;margin-top:2px;">
               ${esc(s.triggered_condition.replace(/_/g,' '))}
             </div>` : ''}
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:5px;">Risk Score</div>
        <div style="width:100px;height:7px;background:#e5e7eb;border-radius:4px;
                    overflow:hidden;margin-bottom:4px;">
          <div style="width:${s.critical_score}%;height:100%;
                      background:${color};border-radius:4px;"></div>
        </div>
        <div style="font-size:20px;font-weight:800;color:${color};">${s.critical_score}%</div>
      </div>
    </div>`;

  // ── 임상 결정 패널 ──
  if (_currentAlertId) {
    html += `
      <div class="alarm-section" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;">
        <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:10px;">📋 임상 결정</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;" id="alarm-decision-btns">
          <button onclick="submitAlarmDecision('ADOPTED')"
            style="padding:6px 14px;background:#dcfce7;color:#16a34a;border:1.5px solid #86efac;
                   border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">✅ 채택</button>
          <button onclick="submitAlarmDecision('MODIFIED')"
            style="padding:6px 14px;background:#eff6ff;color:#2563eb;border:1.5px solid #93c5fd;
                   border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">✏ 수정 후 채택</button>
          <button onclick="submitAlarmDecision('REJECTED')"
            style="padding:6px 14px;background:#fff1f2;color:#e11d48;border:1.5px solid #fda4af;
                   border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">❌ 기각</button>
        </div>
        <div id="alarm-decision-reason" style="display:none;margin-top:10px;">
          <textarea id="alarm-decision-text" placeholder="사유 입력 (선택사항)"
            style="width:100%;height:60px;padding:8px;border:1px solid #d1d5db;border-radius:6px;
                   font-size:12px;resize:none;box-sizing:border-box;"></textarea>
          <div style="display:flex;justify-content:flex-end;margin-top:6px;">
            <button onclick="confirmAlarmDecision()"
              style="padding:5px 14px;background:#6366f1;color:#fff;border:none;border-radius:6px;
                     font-size:12px;font-weight:600;cursor:pointer;">확인</button>
          </div>
        </div>
      </div>`;
  }

  // ── Detected Indicators ──
  if (s.matched_indicators && s.matched_indicators.length) {
    html += `
      <div class="alarm-section">
        <div class="alarm-section-label">⚑ Detected Red Flag Indicators</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          ${s.matched_indicators.map(m => `
            <span style="padding:5px 12px;border-radius:99px;font-size:12px;font-weight:600;
                         background:${bg};color:${color};border:1px solid ${color}50;">
              ⚑ ${esc(m)}
            </span>`).join('')}
        </div>
      </div>`;
  }

  // ── SOAP Note ──
  html += `
    <div class="alarm-section">
      <div class="alarm-section-label">🩺 SOAP Note</div>
      <div class="soap-display">${s.soap_text ? formatSoap(s.soap_text, s.id, s.clinical_context)
        : '<span style="color:#9ca3af;">내용 없음</span>'}</div>
    </div>`;

  // ── Referral Letter ──
  if (s.alarm_level === 'RED') {
    html += `<div class="alarm-section" id="referral-section-${s.id}">
      <div class="alarm-section-label">📄 Physician Referral Letter</div>`;
    if (s.referral_letter) {
      html += `<div class="alarm-letter-box" style="border:2px solid ${color};">
          ${formatLetter(s.referral_letter)}
        </div>`;
    } else {
      html += `<button class="btn-generate-referral" onclick="generateReferralFromWeb(${s.alert_id}, ${s.id})"
        style="margin-top:6px;padding:8px 16px;background:#fff;color:#dc2626;
               border:1.5px solid #dc2626;border-radius:6px;font-size:13px;
               font-weight:600;cursor:pointer;">
        📄 Generate Referral Letter
      </button>
      <div id="referral-letter-${s.id}" style="margin-top:8px;"></div>`;
    }
    html += `</div>`;
  }

  body.innerHTML = html;
  document.getElementById('doc-modal-overlay').classList.add('open');
}

async function generateReferralFromWeb(alertId, sessionId) {
  const btn = document.querySelector(`#referral-section-${sessionId} button`);
  if (btn) { btn.textContent = 'Generating…'; btn.disabled = true; }
  try {
    const res = await fetch(`/pt/api/alerts/${alertId}/generate/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF },
    });
    const data = await res.json();
    if (data.template) {
      // _sessions 캐시 업데이트
      const s = _sessions.find(s => s.id === sessionId);
      if (s) s.referral_letter = data.referral_letter;

      if (data.ai && FEATURES.ab_comparison) {
        // A/B 비교 모달
        openDocModalAB(data.template, data.ai, '📄 Physician Referral Letter', 'referral', activePatientId);
      } else {
        // AI 실패 fallback — 기존 박스 렌더링
        const box = document.getElementById(`referral-letter-${sessionId}`);
        if (box) {
          if (btn) btn.style.display = 'none';
          box.innerHTML = `<div class="alarm-letter-box" style="border:2px solid #dc2626;">${formatLetter(data.referral_letter)}</div>`;
        }
      }
    }
  } catch(e) {
    if (btn) { btn.textContent = '📄 Generate Referral Letter'; btn.disabled = false; }
  }
}

function closeSlidePanel() {
  document.getElementById('slide-panel').classList.remove('open');
  document.getElementById('slide-overlay').classList.remove('open');
}

function slideCopyLetter(btn) {
  const text = document.getElementById('slide-letter-text')?.innerText || '';
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✅ Copied!';
    setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
  });
}

function slidePrintLetter() {
  const text = document.getElementById('slide-letter-text')?.innerText || '';
  const w = window.open('', '_blank');
  w.document.write(`<pre style="font-family:monospace;font-size:13px;padding:40px;">${text}</pre>`);
  w.document.close(); w.print();
}

// ── 탭 전환 ──────────────────────────────────────────────────────
function switchDetailTab(tab) {
  const s = document.getElementById('detail-session-content');
  const d = document.getElementById('detail-docs-content');
  const ts = document.getElementById('dtab-session');
  const td = document.getElementById('dtab-docs');
  if (!s || !d) return;
  s.style.display  = tab === 'session' ? 'flex' : 'none';
  d.style.display  = tab === 'docs'    ? 'block' : 'none';
  ts.classList.toggle('active', tab === 'session');
  td.classList.toggle('active', tab === 'docs');
}

// ── 문서 탭 렌더 ─────────────────────────────────────────────────
function renderDocumentsTab(patientId, patientName) {
  const el = document.getElementById('detail-docs-content');
  if (!el) return;

  const redCount    = _sessions.filter(s => s.alarm_level === 'RED').length;
  const yellowCount = _sessions.filter(s => s.alarm_level === 'YELLOW').length;
  const scores      = _sessions.map(s => s.critical_score);
  const trend       = _computeClientTrend(scores);
  // _sessions은 최신순이므로 oldest = 마지막, newest = 첫 번째
  const oldest      = _sessions[_sessions.length - 1];
  const newest      = _sessions[0];
  const alertParts  = [];
  if (redCount)    alertParts.push(`${redCount} RED`);
  if (yellowCount) alertParts.push(`${yellowCount} YELLOW`);

  // ── 간략 컨텍스트 바 ──
  const ctxHtml = `
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                padding:10px 16px;margin-bottom:16px;
                display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;">
      <span style="font-size:12px;color:#374151;">
        <strong>${_sessions.length}</strong> session${_sessions.length>1?'s':''}
      </span>
      <span style="color:#d1d5db;font-size:12px;">·</span>
      <span style="font-size:12px;color:#6b7280;">${oldest?.session_date} – ${newest?.session_date}</span>
      <span style="color:#d1d5db;font-size:12px;">·</span>
      <span style="font-size:12px;font-weight:600;
                   color:${trend.includes('↑')?'#dc2626':trend.includes('↓')?'#16a34a':'#374151'};">
        ${esc(trend)}
      </span>
      ${alertParts.length ? `
        <span style="color:#d1d5db;font-size:12px;">·</span>
        <span style="font-size:12px;color:#6b7280;">${alertParts.join(' · ')}</span>` : ''}
    </div>`;

  // ── Physician Referral Letter (최신 것) ──
  const letterSessions = _sessions.filter(s => s.referral_letter);
  let referralHtml = '';
  if (letterSessions.length > 0) {
    const latest     = letterSessions[0];
    const latestIdx  = _sessions.indexOf(latest);
    const isRed      = latest.alarm_level === 'RED';
    const borderClr  = isRed ? '#dc2626' : '#d97706';
    const bgClr      = isRed ? '#fef2f2' : '#fffbeb';
    referralHtml = `
      <div style="border:2px solid ${borderClr};border-radius:10px;
                  overflow:hidden;margin-bottom:16px;">
        <div style="background:${bgClr};padding:12px 16px;
                    display:flex;align-items:center;justify-content:space-between;gap:12px;">
          <div style="display:flex;align-items:center;gap:10px;min-width:0;">
            <span style="font-size:20px;flex-shrink:0;">📄</span>
            <div style="min-width:0;">
              <div style="font-size:13px;font-weight:700;color:${borderClr};">
                Physician Referral Letter
              </div>
              <div style="font-size:11px;color:#6b7280;">
                Latest: ${latest.session_date}${letterSessions.length > 1
                  ? ' &nbsp;·&nbsp; ' + letterSessions.length + ' letters total' : ''}
              </div>
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;">
            <button class="pt-letter-btn"
                    onclick="printReferralLetter(${latest.alert_id})">🖨️ Print / PDF</button>
            <button class="pt-letter-btn pt-letter-btn-primary"
                    style="${!isRed?'background:#d97706;border-color:#d97706;':''}"
                    onclick="viewReferralInModal(${latestIdx})">📋 View & Copy</button>
            ${latest.alert_id ? buildReferralTracker(latest) : ''}
          </div>
        </div>
      </div>`;
  }

  // ── 5개 문서 카드 ──
  const docTypes = [
    { type:'medical_necessity',   icon:'🏥', title:'Medical Necessity',        desc:'보험사 선승인 / 의학적 필요성 증빙 레터' },
    { type:'legal_defense',       icon:'⚖️', title:'Standard of Care Defense', desc:'소송 방어용 스크리닝 수행 감사 트레일' },
    { type:'clinical_chronology', icon:'📅', title:'Clinical Chronology',      desc:'전체 세션 시계열 기록 (법적 참고문서)' },
    { type:'insurance_appeal',    icon:'📩', title:'Insurance Appeal',         desc:'보험 청구 거절 이의신청 레터' },
    { type:'functional_report',   icon:'📊', title:'Functional Report',        desc:'Medicare/보험용 기능제한 보고서' },
  ];

  const cardsHtml = `<div class="doc-cards-grid">` + docTypes.map(dt => `
    <div class="doc-card">
      <div class="doc-card-icon">${dt.icon}</div>
      <div class="doc-card-title">${dt.title}</div>
      <div class="doc-card-desc">${dt.desc}</div>
      <button class="doc-generate-btn" id="doc-btn-${dt.type}"
              onclick="generateDoc('${esc(patientId)}','${dt.type}',this)">
        Generate
      </button>
    </div>`).join('') + `</div>`;

  el.innerHTML = ctxHtml + referralHtml + cardsHtml;
}

async function viewReferralInModal(idx) {
  const s = _sessions[idx];
  if (!s || !s.referral_letter) return;

  if (s.alert_id) {
    try {
      const res = await fetch(`/pt/api/alerts/${s.alert_id}/generate/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF },
      });
      const data = await res.json();
      if (data.ai && FEATURES.ab_comparison) {
        openDocModalAB(data.template, data.ai, '📄 Physician Referral Letter', 'referral', activePatientId);
        return;
      }
    } catch(e) {
      // AI 실패 시 단일 모달 fallback
    }
  }
  openDocModal(s.referral_letter, '📄 Physician Referral Letter', 'referral', activePatientId);
}

function _computeClientTrend(scores) {
  if (scores.length < 2) return 'New patient';
  const recent = scores.slice(-3);
  const delta  = recent[recent.length-1] - recent[0];
  if (delta > 15)  return 'Escalating ↑';
  if (delta < -15) return 'Improving ↓';
  return 'Stable →';
}

async function generateDoc(patientId, docType, btnEl) {
  const orig = btnEl.innerHTML;
  btnEl.disabled = true;
  btnEl.innerHTML = '<span class="pt-spinner" style="border-color:rgba(99,102,241,.3);border-top-color:#6366f1;"></span>Generating...';

  try {
    const r = await fetch(`/pt/api/patients/${encodeURIComponent(patientId)}/generate-doc/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:    JSON.stringify({ doc_type: docType }),
    });
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || 'Server error');

    if (d.ai && FEATURES.ab_comparison) {
      openDocModalAB(d.template, d.ai, d.title, docType, patientId);
    } else {
      openDocModal((d.template || d).content || d.template?.content, d.title, docType, patientId);
    }
  } catch(e) {
    alert('문서 생성 실패: ' + e.message);
  } finally {
    btnEl.disabled = false;
    btnEl.innerHTML = orig;
  }
}

let _docModalCopyText   = '';
let _currentDocType     = '';
let _currentDocPatientId = '';

function openDocModal(docText, title, docType, patientId) {
  _docModalCopyText    = docText;
  _currentDocType      = docType || '';
  _currentDocPatientId = patientId || '';
  document.getElementById('doc-modal-title').textContent = title || 'Document';
  const body = document.getElementById('doc-modal-body');
  body.style.padding = '';
  body.style.overflow = '';
  body.style.display = '';
  body.style.flexDirection = '';
  const modal = body.closest('.doc-modal');
  if (modal) modal.style.maxWidth = '';
  body.classList.add('text-mode');
  body.innerHTML = formatLetter(docText);
  const copyBtn = document.getElementById('doc-modal-copy-btn');
  copyBtn.textContent = '📋 Copy';
  copyBtn.style.display = '';
  const editBtn = document.getElementById('doc-modal-edit-btn');
  if (editBtn) {
    editBtn.style.display   = _currentDocType ? '' : 'none';
    editBtn.textContent     = '✏ 수정';
    editBtn.dataset.editing = '0';
  }
  const sendBtn = document.getElementById('doc-modal-send-btn');
  if (sendBtn) sendBtn.style.display = _currentDocPatientId ? '' : 'none';
  document.getElementById('doc-modal-overlay').classList.add('open');
}

function openDocModalAB(tmpl, ai, title, docType, patientId) {
  _docModalCopyText    = tmpl.content;
  _currentDocType      = docType || '';
  _currentDocPatientId = patientId || '';
  document.getElementById('doc-modal-title').textContent = (title || 'Document') + ' — 버전 비교';
  const copyBtn = document.getElementById('doc-modal-copy-btn');
  copyBtn.style.display = 'none';
  const editBtn = document.getElementById('doc-modal-edit-btn');
  if (editBtn) editBtn.style.display = 'none';
  const sendBtn2 = document.getElementById('doc-modal-send-btn');
  if (sendBtn2) sendBtn2.style.display = 'none';

  const body = document.getElementById('doc-modal-body');
  body.classList.remove('text-mode');
  body.style.padding = '0';
  body.style.overflow = 'hidden';
  body.style.display = 'flex';
  body.style.flexDirection = 'column';
  // A/B 비교는 더 넓은 모달이 필요
  const modal = body.closest('.doc-modal');
  if (modal) modal.style.maxWidth = '1100px';
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;flex:1;min-height:0;">
      <div style="border-right:1px solid #e2e8f0;display:flex;flex-direction:column;min-height:0;">
        <div style="padding:8px 14px;background:#f1f5f9;border-bottom:1px solid #e2e8f0;
                    display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
          <span style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">
            Template
          </span>
          <button id="choose-tmpl-btn" onclick="chooseDocVersion(${tmpl.id},'template',this)"
            style="padding:4px 12px;font-size:11px;font-weight:600;border:none;border-radius:5px;
                   cursor:pointer;background:#e0e7ff;color:#4338ca;">
            Use this
          </button>
        </div>
        <div style="flex:1;min-height:0;overflow-y:auto;padding:14px;font-family:'Courier New',monospace;
                    font-size:11.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;">
          ${esc(tmpl.content)}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;min-height:0;">
        <div style="padding:8px 14px;background:#f0fdf4;border-bottom:1px solid #e2e8f0;
                    display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
          <span style="font-size:11px;font-weight:700;color:#16a34a;text-transform:uppercase;letter-spacing:.05em;">
            ✨ AI
          </span>
          <button id="choose-ai-btn" onclick="chooseDocVersion(${ai.id},'ai',this)"
            style="padding:4px 12px;font-size:11px;font-weight:600;border:none;border-radius:5px;
                   cursor:pointer;background:#dcfce7;color:#15803d;">
            Use this
          </button>
        </div>
        <div style="flex:1;min-height:0;overflow-y:auto;padding:14px;font-family:'Courier New',monospace;
                    font-size:11.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;">
          ${esc(ai.content)}
        </div>
      </div>
    </div>`;
  document.getElementById('doc-modal-overlay').classList.add('open');
}

async function chooseDocVersion(docId, version, btn) {
  btn.disabled = true;
  btn.textContent = '저장 중…';

  // 선택된 컬럼의 content div 텍스트 미리 확보
  const contentDiv = btn.closest('[style*="flex-direction:column"]').querySelector('[style*="overflow-y:auto"]');
  const chosenText = contentDiv ? contentDiv.textContent.trim() : '';

  try {
    const r = await fetch(`/pt/api/docs/${docId}/choose/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
    });
    const d = await r.json();
    if (!d.ok) throw new Error('Failed');

    // 선택 완료 → 단일 문서 편집 모달로 전환 (기존 수정 플로우 재사용)
    const title = document.getElementById('doc-modal-title').textContent.replace(' — 버전 비교', '');
    openDocModal(chosenText, title, _currentDocType, _currentDocPatientId);
  } catch(e) {
    btn.textContent = 'Use this';
    btn.disabled = false;
    alert('선택 저장 실패: ' + e.message);
  }
}

function closeDocModal() {
  document.getElementById('doc-modal-overlay').classList.remove('open');
}

function copyDocModal(btn) {
  navigator.clipboard.writeText(_docModalCopyText).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✅ Copied!';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
}

function printDocModal() {
  const title = document.getElementById('doc-modal-title')?.textContent || 'Document';
  const w = window.open('', '_blank');
  w.document.write(
    `<!DOCTYPE html><html><head><title>${esc(title)}</title>`
    + `<style>body{font-family:'Courier New',monospace;font-size:13px;line-height:1.9;`
    + `padding:48px;color:#111;white-space:pre-wrap;}@media print{body{padding:24px;}}</style>`
    + `</head><body>${esc(_docModalCopyText)}</body></html>`
  );
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 300);
}

// ── Alarm 현황 ───────────────────────────────────────────────
let alarmData = null;

async function showAlarms() {
  _showView('view-alarms');

  document.getElementById('alarm-list').innerHTML =
    '<div style="padding:40px;text-align:center;color:#9ca3af;font-size:14px;">불러오는 중...</div>';

  try {
    const r = await fetch('/pt/api/alarms/');
    alarmData = await r.json();
    renderAlarmDashboard(alarmData);
  } catch(e) {
    document.getElementById('alarm-list').innerHTML =
      '<div style="padding:40px;text-align:center;color:#ef4444;">불러오기 실패</div>';
  }
}

function renderAlarmDashboard(d) {
  const total = (d.counts.red || 0) + (d.counts.yellow || 0);

  // 요약 카드
  const cards = [
    { label:'RED Alert', count: d.counts.red,    bg:'#fef2f2', border:'#fca5a5', color:'#dc2626', icon:'🚨' },
    { label:'YELLOW Flag', count: d.counts.yellow, bg:'#fffbeb', border:'#fcd34d', color:'#d97706', icon:'⚠️' },
    { label:'전체 알람', count: total,             bg:'#f8fafc', border:'#e2e8f0', color:'#475569', icon:'📊' },
  ];
  document.getElementById('alarm-summary-cards').innerHTML = cards.map(c => `
    <div style="background:${c.bg};border:1px solid ${c.border};border-radius:12px;padding:18px 20px;">
      <div style="font-size:24px;margin-bottom:6px;">${c.icon}</div>
      <div style="font-size:28px;font-weight:800;color:${c.color};line-height:1;">${c.count}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">${c.label}</div>
    </div>`).join('');

  filterAlarmView('ALL');
}

function filterAlarmView(level) {
  // 탭 스타일
  ['ALL','RED','YELLOW'].forEach(l => {
    const t = document.getElementById(`tab-${l}`);
    if (l === level) {
      t.style.background = '#6366f1'; t.style.color = '#fff'; t.style.borderColor = '#6366f1';
    } else {
      t.style.background = '#fff'; t.style.color = '#374151'; t.style.borderColor = '#d1d5db';
    }
  });

  if (!alarmData) return;
  const rows = level === 'RED' ? alarmData.red
             : level === 'YELLOW' ? alarmData.yellow
             : [...alarmData.red, ...alarmData.yellow];

  if (!rows.length) {
    document.getElementById('alarm-list').innerHTML =
      `<div style="padding:48px;text-align:center;color:#9ca3af;font-size:14px;">해당 알람이 없습니다</div>`;
    return;
  }

  // 데이터를 전역 배열에 저장 후 인덱스로 참조
  window._alarmRows = rows;

  const html = rows.map((s, i) => {
    const bg     = s.alarm_level === 'RED' ? '#fef2f2' : '#fffbeb';
    const border = s.alarm_level === 'RED' ? '#fca5a5' : '#fcd34d';
    const color  = s.alarm_level === 'RED' ? '#dc2626' : '#d97706';
    const icon   = s.alarm_level === 'RED' ? '🚨' : '⚠️';
    const indicators = (s.matched_indicators || []).map(m =>
      `<span style="font-size:11px;background:#fff;border:1px solid #e5e7eb;border-radius:4px;
                    padding:2px 7px;color:#374151;">${esc(m)}</span>`
    ).join('');

    return `
      <div data-alarm-idx="${i}"
           style="background:${bg};border:1px solid ${border};border-radius:12px;
                  padding:16px 20px;margin-bottom:12px;cursor:pointer;transition:box-shadow .15s;"
           onmouseover="this.style.boxShadow='0 4px 16px rgba(0,0,0,.1)'"
           onmouseout="this.style.boxShadow='none'">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <span style="font-size:18px;">${icon}</span>
          <div>
            <div style="font-size:14px;font-weight:700;color:#1e293b;">
              ${esc(s.patient_name||s.patient_id)}
              <span style="font-size:12px;font-weight:400;color:#64748b;margin-left:6px;">${esc(s.patient_id)}</span>
            </div>
            <div style="font-size:12px;color:#64748b;">${s.session_date}</div>
          </div>
          <div style="margin-left:auto;text-align:right;">
            <div style="font-size:13px;font-weight:700;color:${color};">${s.alarm_level}</div>
            <div style="font-size:12px;color:#94a3b8;">${esc(s.triggered_condition||'')}</div>
          </div>
          <div style="text-align:right;min-width:52px;">
            <div style="font-size:20px;font-weight:800;color:${color};">${s.critical_score}%</div>
            <div style="font-size:10px;color:#94a3b8;">risk score</div>
          </div>
        </div>
        ${indicators ? `<div style="display:flex;flex-wrap:wrap;gap:5px;">${indicators}</div>` : ''}
      </div>`;
  }).join('');

  document.getElementById('alarm-list').innerHTML = html;

  // 이벤트 위임으로 클릭 처리
  document.getElementById('alarm-list').onclick = e => {
    const card = e.target.closest('[data-alarm-idx]');
    if (card) openAlarmModal(window._alarmRows[+card.dataset.alarmIdx]);
  };
}

async function deleteSession(sessionId, patientId) {
  if (!confirm('이 세션을 삭제하시겠습니까?')) return;

  const r = await fetch(`/pt/api/sessions/${sessionId}/delete/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': CSRF },
  });
  const d = await r.json();
  if (!r.ok) { alert('삭제 실패: ' + (d.error || r.status)); return; }

  if (d.remaining === 0) {
    // 환자 세션이 모두 삭제됨 → 사이드바에서 제거 후 새 세션 뷰로
    allPatients = allPatients.filter(p => p.patient_id !== patientId);
    renderPatientList(allPatients);
    showNewSession();
  } else {
    // 나머지 세션 다시 로드
    await selectPatient(patientId, document.getElementById('history-title').textContent);
  }
}


// ── 새 세션 폼 ───────────────────────────────────────
async function generatePatientId() {
  const btn = document.querySelector('button[onclick="generatePatientId()"]');
  const orig = btn.textContent;
  btn.textContent = '...'; btn.disabled = true;
  try {
    const r = await fetch('/pt/api/generate-patient-id/');
    const d = await r.json();
    document.getElementById('inp-id').value = d.patient_id;
  } catch(e) {
    alert('ID 생성 실패');
  } finally {
    btn.textContent = orig; btn.disabled = false;
  }
}

function showNewSession() {
  activePatientId = null;
  renderPatientList(allPatients);
  _showView('view-new');
  document.getElementById('inp-name').value = '';
  document.getElementById('inp-id').value = '';
  document.getElementById('inp-date').value = new Date().toISOString().split('T')[0];
  ['S','O','A','P'].forEach(t => { const el = document.getElementById(`inp-${t}`); if (el) el.value = ''; });
  _confirmedChips.clear();
  _renderChipSection('S');
  _renderChipSection('O');
  switchSoapTab('S');
  resetResult();
}

function addSessionForPatient() {
  const pname = document.getElementById('history-title').textContent;
  _showView('view-new');
  document.getElementById('inp-name').value = pname !== activePatientId ? pname : '';
  document.getElementById('inp-id').value = activePatientId || '';
  document.getElementById('inp-date').value = new Date().toISOString().split('T')[0];
  ['S','O','A','P'].forEach(t => { const el = document.getElementById(`inp-${t}`); if (el) el.value = ''; });
  _confirmedChips.clear();
  _renderChipSection('S');
  _renderChipSection('O');
  switchSoapTab('S');
  resetResult();
}

// ── SOAP 분석 & 저장 ─────────────────────────────────
async function analyzeAndSave() {
  const sText = (document.getElementById('inp-S')?.value || '').trim();
  const oText = (document.getElementById('inp-O')?.value || '').trim();
  const aText = (document.getElementById('inp-A')?.value || '').trim();
  const pText = (document.getElementById('inp-P')?.value || '').trim();
  const confirmedIds = [..._confirmedChips];

  const parts = [];
  if (sText) parts.push('S: ' + sText);
  if (oText) parts.push('O: ' + oText);
  if (aText) parts.push('A: ' + aText);
  if (pText) parts.push('P: ' + pText);
  const soap = parts.join('\n');

  if (!soap && confirmedIds.length === 0) {
    alert('SOAP note를 입력하거나 Red Flag 항목을 선택하세요.');
    return;
  }

  const name = document.getElementById('inp-name').value.trim();
  const pid  = document.getElementById('inp-id').value.trim() || (name ? name.replace(/\s+/g,'_') : 'ANON');
  const date = document.getElementById('inp-date').value;

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="pt-spinner"></span>분석 중...';

  try {
    const r = await fetch('/pt/api/save/', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRFToken':CSRF},
      body: JSON.stringify({soap_text:soap, patient_id:pid, patient_name:name, session_date:date, confirmed_rf_ids:confirmedIds})
    });
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || 'Server error');
    renderResult(d);
    await loadPatients();
    // 저장 후 사이드바에서 해당 환자 활성화
    activePatientId = pid;
    renderPatientList(allPatients);
  } catch(e) {
    document.getElementById('result-content').innerHTML =
      `<div style="color:#dc2626;font-size:13px;">오류: ${esc(e.message)}</div>`;
    document.getElementById('result-content').style.display = 'block';
    document.getElementById('result-empty').style.display = 'none';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🚨 Analyze Red Flags &amp; Save';
    _confirmedChips.clear();
    _renderChipSection('S');
    _renderChipSection('O');
  }
}

function renderResult(d) {
  const colors = {RED:'#dc2626',YELLOW:'#d97706',NONE:'#16a34a'};
  const icons  = {RED:'🚨',YELLOW:'⚠️',NONE:'✅'};
  const labels = {RED:'RED ALERT — 즉시 조치 필요',YELLOW:'YELLOW FLAG — 주의 관찰',NONE:'Red Flag 없음'};
  let html = '';

  // 알람 배너
  html += `<div class="pt-alarm-banner ${d.alarm}">
    <div class="pt-alarm-icon">${icons[d.alarm]}</div>
    <div>
      <div class="pt-alarm-level">${labels[d.alarm]}</div>
      ${d.condition ? `<div class="pt-alarm-cond">${d.condition.replace(/_/g,' ')}</div>` : ''}
    </div>
  </div>`;

  // 스코어 바
  const fillColor = colors[d.alarm] || '#6b7280';
  html += `<div class="pt-score-row">
    <span class="pt-score-label">Risk score</span>
    <div class="pt-score-bar"><div class="pt-score-fill" style="width:${d.score}%;background:${fillColor};"></div></div>
    <span class="pt-score-val">${d.score}%</span>
  </div>`;

  // 멀티 컨디션 목록
  const active = (d.conditions || []).filter(c => c.alarm !== 'NONE');
  if (active.length) {
    html += `<div class="pt-section-title">감지된 Red Flag 조건 (${active.length}개)</div>`;
    active.forEach(c => {
      const bg  = c.alarm === 'RED' ? '#fef2f2' : '#fffbeb';
      const bdr = c.alarm === 'RED' ? '#fca5a5' : '#fcd34d';
      html += `<div style="border:1px solid ${bdr};border-radius:8px;padding:10px 12px;margin-bottom:8px;background:${bg};">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
          <span style="font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px;background:${colors[c.alarm]};color:#fff;">${c.alarm}</span>
          <strong style="font-size:13px;color:#1e293b;">${esc(c.condition.replace(/_/g,' '))}</strong>
          <span style="margin-left:auto;font-size:11px;color:#6b7280;">${(c.score*100).toFixed(0)}%</span>
        </div>
        ${c.trigger ? `<div style="font-size:11px;color:#dc2626;margin-bottom:4px;">trigger: ${esc(c.trigger)}</div>` : ''}
        <div style="display:flex;flex-wrap:wrap;gap:4px;">
          ${(c.matched||[]).map(m => `<span style="font-size:11px;background:#fff;border:1px solid #e5e7eb;border-radius:4px;padding:2px 6px;color:#374151;">${esc(m)}</span>`).join('')}
        </div>
      </div>`;
    });
  }

  // VPPS 추출 증상 (원시 hits)
  if (d.vpps_hits && d.vpps_hits.length) {
    html += `<div class="pt-section-title">VPPS 추출 증상 (${d.vpps_hits.length}개)</div>
    <div class="pt-hit-list">`;
    d.vpps_hits.forEach(h => {
      html += `<div class="pt-hit-item ${h.alarm_level}">
        <span>${h.alarm_level==='RED'?'🔴':'🟡'}</span>
        <span style="font-size:12px;">${esc(h.label)}</span>
        <span style="margin-left:auto;font-size:10px;color:#9ca3af;">${(h.weight*100).toFixed(0)}%</span>
      </div>`;
    });
    html += '</div>';
  }

  // 환자 컨텍스트
  if (d.patient_context && d.patient_context.session_count > 1) {
    html += `<div class="pt-section-title">환자 이력 (${d.patient_context.session_count}세션)</div>
    <div style="background:#f8fafc;border-radius:7px;padding:9px 11px;font-size:12px;color:#374151;margin-bottom:12px;">${esc(d.patient_context.summary)}</div>`;
  }

  // 리퍼럴 레터
  if (d.referral_letter) {
    html += `<div class="pt-section-title">📄 Physician Referral Letter</div>
    <div class="pt-referral" id="referral-text">${esc(d.referral_letter)}</div>
    <button class="pt-copy-btn" onclick="copyReferral()">📋 Copy Letter</button>`;
  }

  const content = document.getElementById('result-content');
  content.innerHTML = html;
  content.style.display = 'block';
  document.getElementById('result-empty').style.display = 'none';
  content.scrollIntoView({behavior:'smooth',block:'nearest'});
}

function resetResult() {
  document.getElementById('result-content').style.display = 'none';
  document.getElementById('result-content').innerHTML = '';
  document.getElementById('result-empty').style.display = 'block';
}

// ── 유틸 ────────────────────────────────────────────
function alarmLabel(a) {
  return {RED:'🚨 RED',YELLOW:'⚠️ YELLOW',NONE:'✅ NONE'}[a] || a;
}

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function copySessionSoap(btn, sessionId) {
  const sess = _sessions.find(s => s.id === sessionId);
  const formattedHtml = formatSoap(sess?.soap_text, sess?.id, sess?.clinical_context);
  const tmp = document.createElement('div');
  tmp.innerHTML = formattedHtml;
  const soapText = tmp.innerText || sess?.soap_text || '';
  navigator.clipboard.writeText(soapText).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓ 복사됨';
    btn.style.color  = '#16a34a';
    btn.style.border = '1px solid #bbf7d0';
    setTimeout(() => {
      btn.textContent = '⎘ 복사';
      btn.style.color  = '#6b7280';
      btn.style.border = '1px solid #d1d5db';
    }, 2000);
  }).catch(() => {
    btn.textContent = '❌ 실패';
    setTimeout(() => { btn.textContent = '⎘ 복사'; }, 2000);
  });
}

function toggleSoapCompare() {
  const single  = document.getElementById('soap-body-single');
  const compare = document.getElementById('soap-body-compare');
  const btn     = document.getElementById('soap-compare-btn');
  if (!single || !compare) return;
  const isCompare = compare.style.display !== 'none';
  single.style.display  = isCompare ? '' : 'none';
  compare.style.display = isCompare ? 'none' : 'grid';
  btn.textContent       = isCompare ? '⇄ 비교' : '✕ 비교 닫기';
  btn.style.background  = isCompare ? 'transparent' : '#eef2ff';
}

async function runReseed() {
  if (!confirm('전체 세션을 삭제하고 실습 데이터(16개 + Margaret 10회)를 재적재합니다. 계속할까요?')) return;
  const btn = document.getElementById('reseed-btn');
  btn.textContent = '⏳ Seeding...';
  btn.disabled = true;
  try {
    const r = await fetch('/pt/api/admin/reseed/', {
      method: 'POST',
      headers: {'X-CSRFToken': CSRF},
    });
    const d = await r.json();
    if (!r.ok || !d.ok) {
      btn.textContent = '❌ Error';
      btn.title = JSON.stringify(d);
      btn.disabled = false;
      return;
    }
    const errNote = d.errors && d.errors.length ? ` (${d.errors.length} err)` : '';
    btn.textContent = `✅ ${d.seeded} seeded${errNote}`;
    setTimeout(() => { btn.textContent = '🌱 Clear & Reseed All'; btn.disabled = false; }, 3000);
    // 뷰 완전 초기화 후 환자 목록 리로드
    activePatientId  = null;
    currentPatientId = null;
    _sessions        = [];
    _showView('view-new');
    await loadPatients();
  } catch(e) {
    btn.textContent = '❌ ' + e.message;
    btn.disabled = false;
  }
}

async function runBackfill() {
  const btn = document.getElementById('rescore-btn');
  btn.textContent = '⏳ Running...';
  btn.disabled = true;
  try {
    const r = await fetch('/pt/api/backfill-rescore/', {
      method: 'POST',
      headers: {'X-CSRFToken': CSRF},
    });
    const d = await r.json();
    if (!r.ok || !d.ok) {
      btn.textContent = '❌ Error';
      btn.title = JSON.stringify(d);
      btn.disabled = false;
      return;
    }
    btn.textContent = `✅ ${d.changed}/${d.total} updated`;
    setTimeout(() => { btn.textContent = '🔄 Re-score All'; btn.disabled = false; }, 3000);
    if (d.changed > 0) {
      activePatientId  = null;
      currentPatientId = null;
      _sessions        = [];
      _showView('view-new');
      await loadPatients();
    }
  } catch(e) {
    btn.textContent = '❌ ' + e.message;
    btn.disabled = false;
  }
}

async function copyReferral() {
  const text = document.getElementById('referral-text')?.innerText || '';
  await navigator.clipboard.writeText(text);
  const btn = event.target;
  btn.textContent = '✅ Copied!';
  setTimeout(() => { btn.textContent = '📋 Copy Letter'; }, 2000);
}

// ── SOAP 포맷팅 ───────────────────────────────────────────────
function _soapTitle(label) {
  return `<span class="soap-section-title">${label}</span>`;
}

// ── Path A: clinical_context (AI 분류) → 섹션 제목 + 추출값 ──────
function _renderFromCtx(ctx) {
  const rows = (vals) => {
    const items = Array.isArray(vals) ? vals : (vals ? [String(vals)] : []);
    return items.filter(Boolean).map(v =>
      `<span style="display:block;">${esc(String(v))}</span>`
    ).join('');
  };

  const S = [
    ctx.chief_complaint,
    ctx.onset_duration,
    ctx.vas_score ? `Pain score: ${ctx.vas_score}` : null,
    ...(ctx.comorbidities || []),
  ].filter(Boolean);

  const O = [
    ...(ctx.mmt_findings         || []),
    ...(ctx.rom_findings          || []),
    ...(ctx.neurological_findings || []),
    ...(ctx.special_tests         || []),
  ];

  const A = [
    ctx.primary_diagnosis,
    ...(ctx.red_flag_findings     || []),
    ...(ctx.functional_limitations|| []),
  ].filter(Boolean);

  const P = [
    ...(ctx.treatment_performed   || []),
    ...(ctx.medications           || []),
    ...(ctx.precautions           || []),
  ];

  const Other = ctx.other_findings || [];

  let html = '';
  if (S.length) html += _soapTitle('Subjective') + rows(S);
  if (O.length) html += _soapTitle('Objective')  + rows(O);
  if (A.length) html += _soapTitle('Assessment') + rows(A);
  if (P.length) html += _soapTitle('Plan')       + rows(P);
  if (Other.length) html += _soapTitle('Other')  + rows(Other);
  return html;
}

// ── Path B: 키워드 감지 → 섹션 제목 삽입 ─────────────────────────
const _KEYWORD_SECTION = [
  { re: /^(Patient|Chief\s*complaint?|CC|Onset|History|PMH|HPI|Additional|Prior|Previous|Mechanism|MOI|Aggravat|Easing|Reliev|Exacerbat|Social\s*history|Occupation|Work\s*history|Complaint|Symptom|Duration|Sleep|Bowel|Bladder|Medication|Drug|Allerg|Report)/i,
    sec: 'Subjective' },
  { re: /^(Objective|Observation|Inspection|Measurements?|MMT|ROM|AROM|PROM|RROM|Posture|Gait|Palpation|SLR|Strength|Neurolog|Neuro|Special\s*test|Sensation|Reflex|DTR|Edema|Swelling|Vital|Functional\s*mobility)/i,
    sec: 'Objective'  },
  { re: /^(Diagnosis|Assessment|Clinical\s*impression|Progress|Response|Prognosis|Problem|Intervention|Functional\s*status)/i,
    sec: 'Assessment' },
  { re: /^(LTG|STG|Goal|Plan|Precaution|HEP|Home\s*exercise|Follow.?up|Frequency|Education|Discharge|Return|Next\s*visit|Treatment\s*plan|Rehab)/i,
    sec: 'Plan'       },
];

function _sectionOf(t) {
  for (const { re, sec } of _KEYWORD_SECTION) {
    if (re.test(t)) return sec;
  }
  return null;
}

// Level 1: 알려진 키워드가 줄 중간에 나타나면 앞에 줄바꿈 삽입
function _normalizeSoapLines(text) {
  const kw = [
    'Patient','Chief\\s+complaint?','CC','Onset','History','PMH','HPI','Additional',
    'Prior','Previous','Mechanism','MOI','Aggravat','Easing','Reliev','Exacerbat',
    'Social\\s+history','Occupation','Work\\s+history','Complaint','Symptom','Duration',
    'Sleep','Bowel','Bladder','Medication','Drug','Allerg','Report',
    'Objective','Observation','Inspection','Measurements?','MMT',
    'ROM','AROM','PROM','RROM','Posture','Gait','Palpation','SLR','Strength',
    'Neurolog','Neuro','Special\\s+test','Sensation','Reflex','DTR','Edema','Vital',
    'Functional\\s+mobility',
    'Diagnosis','Assessment','Clinical\\s+impression','Progress','Response',
    'Prognosis','Problem','Intervention','Functional\\s+status',
    'LTG','STG','Goal','Plan','Precaution','HEP','Home\\s+exercise',
    'Follow.?up','Frequency','Education','Discharge','Return','Next\\s+visit',
    'Treatment\\s+plan','Rehab',
  ].join('|');
  return text.replace(
    new RegExp(`([^\\n])[ \\t]+((?:${kw})\\s*:)`, 'gi'),
    '$1\n$2'
  );
}

// Level 2: sessionId별 사용자 섹션 오버라이드 저장
const _sectionOverrides = {};  // key: `${sessionId}_${lineIdx}`

function _renderFromKeywords(rawText, sessionId) {
  const normalized = _normalizeSoapLines(rawText);
  let html = '';
  let cur  = null;
  const seenSections = new Set();   // 이미 타이틀을 출력한 섹션
  let lineIdx = 0;

  for (const line of normalized.split('\n')) {
    const t = line.trim();
    if (!t) { lineIdx++; continue; }

    const detectedSec = _sectionOf(t);

    if (detectedSec) {
      // 오버라이드 확인 — 사용자가 이 줄의 섹션을 변경했을 수 있음
      const key         = `${sessionId}_${lineIdx}`;
      const overrideSec = sessionId != null ? _sectionOverrides[key] : null;
      const effectiveSec = overrideSec || detectedSec;

      if (effectiveSec !== cur) {
        // 이미 출력된 섹션이면 타이틀 중복 삽입 금지
        if (!seenSections.has(effectiveSec)) {
          html += _soapTitle(effectiveSec);
          seenSections.add(effectiveSec);
        }
        cur = effectiveSec;
      }

      const colon = t.indexOf(':');
      let lineContent = '';
      if (colon > 0) {
        const label = t.slice(0, colon).trim();
        const rest  = esc(t.slice(colon + 1).trim());
        lineContent = `<strong style="color:#374151;">${esc(label)}:</strong>${rest ? ' ' + rest : ''}`;
      } else {
        lineContent = esc(t);
      }

      if (sessionId != null) {
        const badge = effectiveSec[0];
        const cls   = overrideSec ? ' overridden' : '';
        html += `<span class="soap-line">` +
                `<button class="soap-pick-btn${cls}" onclick="showSectionPick(event,'${sessionId}',${lineIdx},'${effectiveSec}')" title="섹션 변경">${badge}</button>` +
                `${lineContent}</span>\n`;
      } else {
        html += lineContent + '\n';
      }
    } else {
      // 키워드 없는 라인 — 오버라이드 또는 상속 섹션 사용
      const key         = `${sessionId}_${lineIdx}`;
      const overrideSec = sessionId != null ? _sectionOverrides[key] : null;
      const effectiveSec = overrideSec || cur;

      if (overrideSec && overrideSec !== cur) {
        if (!seenSections.has(overrideSec)) {
          html += _soapTitle(overrideSec);
          seenSections.add(overrideSec);
        }
        cur = overrideSec;
      }

      if (sessionId != null) {
        const badge = effectiveSec ? effectiveSec[0] : '?';
        const cls   = overrideSec ? ' overridden' : '';
        html += `<span class="soap-line">` +
                `<button class="soap-pick-btn${cls}" onclick="showSectionPick(event,'${sessionId}',${lineIdx},'${effectiveSec||''}')" title="섹션 변경">${badge}${overrideSec ? '' : '?'}</button>` +
                `${esc(t)}</span>\n`;
      } else {
        html += esc(t) + '\n';
      }
    }
    lineIdx++;
  }
  return html;
}

// 섹션 picker 표시
function showSectionPick(evt, sessionId, lineIdx, currentSec) {
  evt.stopPropagation();
  const popupId = 'soap-picker-popup';
  const existing = document.getElementById(popupId);
  if (existing) {
    const isSame = existing.dataset.for === `${sessionId}_${lineIdx}`;
    existing.remove();
    if (isSame) return;
  }
  const sections = ['Subjective','Objective','Assessment','Plan'];
  const popup = document.createElement('span');
  popup.id = popupId;
  popup.dataset.for = `${sessionId}_${lineIdx}`;
  popup.className = 'soap-picker-popup';
  popup.innerHTML = sections.map(s =>
    `<button class="soap-pick-opt${s===currentSec?' active':''}" ` +
    `onclick="applySectionPick('${sessionId}',${lineIdx},'${s}')">${s[0]}</button>`
  ).join('');
  evt.currentTarget.insertAdjacentElement('afterend', popup);
}

// 외부 클릭 시 picker 닫기
document.addEventListener('click', () => document.getElementById('soap-picker-popup')?.remove());

// 섹션 선택 적용 + 자동 저장
function applySectionPick(sessionId, lineIdx, sec) {
  _sectionOverrides[`${sessionId}_${lineIdx}`] = sec;
  document.getElementById('soap-picker-popup')?.remove();
  _refreshSoapDisplay(sessionId);
  _saveSessionOverrides(sessionId);
}

// 오버라이드 서버 저장
async function _saveSessionOverrides(sessionId) {
  const prefix   = `${sessionId}_`;
  const overrides = {};
  for (const [key, sec] of Object.entries(_sectionOverrides)) {
    if (key.startsWith(prefix)) {
      overrides[key.slice(prefix.length)] = sec;
    }
  }
  try {
    await fetch(`/pt/api/sessions/${sessionId}/overrides/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ overrides }),
    });
  } catch(e) {
    console.warn('Section overrides save failed:', e);
  }
}

// 세션 로드 시 저장된 오버라이드 복원
function _loadSessionOverrides(sessions) {
  for (const s of sessions) {
    const saved = (s.clinical_context || {}).soap_section_overrides || {};
    for (const [lineIdx, sec] of Object.entries(saved)) {
      _sectionOverrides[`${s.id}_${lineIdx}`] = sec;
    }
  }
}

// SOAP 표시 영역만 재렌더링
function _refreshSoapDisplay(sessionId) {
  const s = _sessions.find(x => String(x.id) === String(sessionId));
  if (!s) return;
  const formatted = formatSoap(s.soap_text, s.id, s.clinical_context);
  const single = document.getElementById('soap-body-single');
  if (single && single.style.display !== 'none') {
    single.querySelector('.soap-display').innerHTML = formatted;
  }
  const compareRight = document.querySelector('#soap-body-compare .soap-compare-col:last-child .soap-display');
  if (compareRight) compareRight.innerHTML = formatted;
}

// ── 진입점 ────────────────────────────────────────────────────────
function formatSoap(rawText, sessionId, clinicalCtx) {
  if (!rawText) return '<span style="color:#9ca3af;">내용 없음</span>';
  // Path B 고정: 항상 라인별 원문 + pick 버튼 렌더링.
  // clinical_context(AI 분류)는 문서 생성·스코어링에서만 사용.
  // 라인별 섹션 오버라이드 = AI 분류 vs 치료사 교정 paired data.
  return _renderFromKeywords(rawText, sessionId ?? null);
}

function _hasCtxContent(ctx) {
  return !!(
    ctx.chief_complaint || ctx.primary_diagnosis ||
    (ctx.rom_findings      && ctx.rom_findings.length)      ||
    (ctx.mmt_findings      && ctx.mmt_findings.length)      ||
    (ctx.special_tests     && ctx.special_tests.length)     ||
    (ctx.treatment_performed && ctx.treatment_performed.length) ||
    (ctx.goals_stg         && ctx.goals_stg.length)         ||
    (ctx.other_findings    && ctx.other_findings.length)
  );
}

const _sessionCtxCache = {};

// ── Letter 포맷팅 ─────────────────────────────────────────────
function formatLetter(rawText) {
  if (!rawText) return '<span style="color:#9ca3af;">Letter 없음</span>';

  return rawText.split('\n').map(line => {
    const t = line.trim();

    // 빈 줄
    if (!t) return '';

    // ===== 구분선 → 얇은 실선
    if (/^={4,}$/.test(t)) {
      return `<span style="display:block;border-top:1px solid #e2e8f0;margin:6px 0;font-size:0;"></span>`;
    }
    // ----- 구분선 → 더 연한 실선
    if (/^-{4,}$/.test(t)) {
      return `<span style="display:block;border-top:1px dashed #e2e8f0;margin:4px 0;font-size:0;"></span>`;
    }

    // [RED] / [YELLOW] / [GREEN] 배지 처리
    const colored = t
      .replace(/\[RED\]/g,    `<span style="background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:4px;font-weight:800;font-size:11px;">[RED]</span>`)
      .replace(/\[YELLOW\]/g, `<span style="background:#fef3c7;color:#b45309;padding:1px 6px;border-radius:4px;font-weight:800;font-size:11px;">[YELLOW]</span>`)
      .replace(/\[GREEN\]/g,  `<span style="background:#dcfce7;color:#15803d;padding:1px 6px;border-radius:4px;font-weight:800;font-size:11px;">[GREEN]</span>`);

    // Urgency: EMERGENCY / WARNING 강조
    if (/^Urgency:/i.test(t)) {
      const isEmergency = /EMERGENCY/i.test(t);
      const bg    = isEmergency ? '#fef2f2' : '#fffbeb';
      const color = isEmergency ? '#dc2626'  : '#b45309';
      return `<span style="display:inline-block;padding:3px 8px;border-radius:5px;background:${bg};`
           + `border:1px solid ${color}40;font-weight:700;color:${color};">${colored}</span>`;
    }

    // ALL CAPS 헤딩 (OVERALL ALERT LEVEL, IDENTIFIED CONDITIONS 등)
    if (/[A-Z]/.test(t) && !/[a-z]/.test(t) && t.length >= 4 && !/^\[/.test(t)) {
      return `<strong style="display:inline-block;margin-top:4px;font-size:12px;font-weight:800;`
           + `color:#111827;letter-spacing:.3px;">${colored}</strong>`;
    }

    // Key: value 라벨
    const m = t.match(/^([A-Za-z][^:]{0,28}):\s*(.*)$/);
    if (m) {
      const val = m[2]
        .replace(/\[RED\]/g,    `<span style="background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:4px;font-weight:800;font-size:11px;">[RED]</span>`)
        .replace(/\[YELLOW\]/g, `<span style="background:#fef3c7;color:#b45309;padding:1px 6px;border-radius:4px;font-weight:800;font-size:11px;">[YELLOW]</span>`);
      return `<strong style="font-weight:700;color:#374151;">${esc(m[1])}:</strong> <span style="color:#1e293b;">${val}</span>`;
    }

    // bullet (•)
    if (/^[•·\-]\s/.test(t)) {
      return `<span style="color:#374151;padding-left:6px;display:inline-block;">${colored}</span>`;
    }

    return `<span style="color:#1e293b;">${colored}</span>`;
  }).join('\n');
}

// ── 슬라이드 패널 드래그 핸들 ─────────────────────────────────
let _slideDrag = null;

function setupSlideDivider() {
  const divider = document.getElementById('slide-divider');
  const leftCol = document.getElementById('slide-left-col');
  const cols    = document.getElementById('slide-cols');
  if (!divider || !leftCol || !cols) return;
  divider.addEventListener('mousedown', e => {
    e.preventDefault();
    divider.classList.add('dragging');
    _slideDrag = { divider, leftCol, cols,
                   startX: e.clientX,
                   startW: leftCol.getBoundingClientRect().width };
  });
}

document.addEventListener('mousemove', e => {
  if (!_slideDrag) return;
  const { leftCol, cols, startX, startW } = _slideDrag;
  const dx     = e.clientX - startX;
  const totalW = cols.getBoundingClientRect().width;
  const newW   = Math.max(150, Math.min(totalW - 150, startW + dx));
  leftCol.style.flex  = 'none';
  leftCol.style.width = newW + 'px';
  e.preventDefault();
});

document.addEventListener('mouseup', () => {
  if (!_slideDrag) return;
  _slideDrag.divider.classList.remove('dragging');
  _slideDrag = null;
});

// ── Phase 7: Audit Loop ──────────────────────────────────────────────

// SOAP 편집
function openSoapEditor(sessionId) {
  const s = _sessions.find(x => String(x.id) === String(sessionId));
  if (!s) return;
  const panel = document.getElementById(`soap-editor-${sessionId}`);
  const ta    = document.getElementById(`soap-edit-ta-${sessionId}`);
  if (!panel || !ta) return;
  ta.value = s.soap_text || '';
  panel.style.display = 'block';
  ta.focus();
}

function closeSoapEditor(sessionId) {
  const panel = document.getElementById(`soap-editor-${sessionId}`);
  if (panel) panel.style.display = 'none';
}

async function saveSoapEdit(sessionId) {
  const ta = document.getElementById(`soap-edit-ta-${sessionId}`);
  if (!ta) return;
  const edited = ta.value.trim();
  if (!edited) return;
  const saveBtn = ta.closest('div[id^="soap-editor"]')?.querySelector('button:last-child');
  if (saveBtn) { saveBtn.textContent = '저장 중…'; saveBtn.disabled = true; }
  try {
    const r = await fetch(`/pt/api/sessions/${sessionId}/soap-edit/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:    JSON.stringify({ edited_soap: edited }),
    });
    const d = await r.json();
    if (d.ok) {
      closeSoapEditor(sessionId);
      if (saveBtn) { saveBtn.textContent = '✅ 저장됨'; saveBtn.disabled = false; setTimeout(() => saveBtn.textContent = '저장', 2000); }
    }
  } catch(e) {
    alert('저장 실패: ' + e.message);
    if (saveBtn) { saveBtn.textContent = '저장'; saveBtn.disabled = false; }
  }
}

// Alarm 결정
async function submitAlarmDecision(decision) {
  _pendingDecision = decision;
  const reasonEl = document.getElementById('alarm-decision-reason');
  if (reasonEl) reasonEl.style.display = 'block';
}

async function confirmAlarmDecision() {
  if (!_currentAlertId || !_pendingDecision) return;
  const reason  = (document.getElementById('alarm-decision-text')?.value || '').trim();
  const confirmBtn = document.querySelector('#alarm-decision-reason button');
  if (confirmBtn) { confirmBtn.textContent = '저장 중…'; confirmBtn.disabled = true; }
  try {
    const r = await fetch(`/pt/api/alerts/${_currentAlertId}/decision/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:    JSON.stringify({ decision: _pendingDecision, reason }),
    });
    const d = await r.json();
    if (d.ok) {
      const labels = { ADOPTED:'✅ 채택됨', REJECTED:'❌ 기각됨', MODIFIED:'✏ 수정 후 채택됨' };
      const btnsEl   = document.getElementById('alarm-decision-btns');
      const reasonEl = document.getElementById('alarm-decision-reason');
      if (btnsEl) btnsEl.innerHTML = `<span style="font-size:13px;font-weight:700;color:#16a34a;">${labels[_pendingDecision] || '저장됨'}</span>`;
      if (reasonEl) reasonEl.style.display = 'none';
      _pendingDecision = null;
    }
  } catch(e) {
    alert('저장 실패: ' + e.message);
    if (confirmBtn) { confirmBtn.textContent = '확인'; confirmBtn.disabled = false; }
  }
}

// 문서 편집
function toggleDocEdit(btn) {
  const body = document.getElementById('doc-modal-body');
  if (!body) return;

  if (btn.dataset.editing === '1') {
    // 편집 모드 → 읽기 모드 (저장 없이 취소)
    body.style.cssText = '';
    body.classList.add('text-mode');
    body.innerHTML = formatLetter(_docModalCopyText);
    btn.textContent = '✏ 수정';
    btn.dataset.editing = '0';
  } else {
    // 읽기 모드 → 편집 모드
    body.classList.remove('text-mode');
    body.style.cssText = 'flex:1;min-height:0;display:flex;flex-direction:column;padding:0;overflow:hidden;';
    const ta = document.createElement('textarea');
    ta.id = 'doc-edit-ta';
    ta.value = _docModalCopyText;
    ta.style.cssText = 'flex:1;min-height:calc(65vh - 110px);width:100%;padding:16px 20px;' +
                       'border:none;outline:none;' +
                       'font-size:12px;font-family:"Courier New",monospace;resize:none;box-sizing:border-box;';
    body.innerHTML = '';
    body.appendChild(ta);

    const saveBar = document.createElement('div');
    saveBar.style.cssText = 'padding:10px 16px;display:flex;justify-content:flex-end;gap:8px;' +
                            'border-top:1px solid #e2e8f0;background:#f8fafc;flex-shrink:0;';
    saveBar.innerHTML = `<button onclick="saveDocEdit()"
      style="padding:6px 16px;background:#6366f1;color:#fff;border:none;border-radius:6px;
             font-size:12px;font-weight:600;cursor:pointer;">수정본 저장</button>`;
    body.appendChild(saveBar);

    btn.textContent = '취소';
    btn.dataset.editing = '1';
    ta.focus();
  }
}

async function saveDocEdit() {
  const ta = document.getElementById('doc-edit-ta');
  if (!ta || !_currentDocType || !_currentDocPatientId) return;
  const edited = ta.value.trim();
  if (!edited) return;
  const saveBtn = document.querySelector('#doc-modal-body button');
  if (saveBtn) { saveBtn.textContent = '저장 중…'; saveBtn.disabled = true; }
  try {
    const r = await fetch(
      `/pt/api/patients/${encodeURIComponent(_currentDocPatientId)}/doc/${encodeURIComponent(_currentDocType)}/edit/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:    JSON.stringify({ original_doc: _docModalCopyText, edited_doc: edited }),
    });
    const d = await r.json();
    if (d.ok) {
      _docModalCopyText = edited;
      const editBtn = document.getElementById('doc-modal-edit-btn');
      if (editBtn) { editBtn.dataset.editing = '0'; editBtn.textContent = '✏ 수정'; }
      const body = document.getElementById('doc-modal-body');
      body.style.cssText = '';
      body.classList.add('text-mode');
      body.innerHTML = formatLetter(edited);
      if (saveBtn) { saveBtn.textContent = '✅ 저장됨'; setTimeout(() => saveBtn.disabled = false, 1500); }
    }
  } catch(e) {
    alert('저장 실패: ' + e.message);
    if (saveBtn) { saveBtn.textContent = '수정본 저장'; saveBtn.disabled = false; }
  }
}


// ── Email 발송 ────────────────────────────────────────────────────────────────

let _emailContacts = [];   // 현재 환자의 저장된 수신자

async function openEmailModal() {
  _emailContacts = [];
  const overlay = document.getElementById('email-modal-overlay');
  document.getElementById('email-send-status').textContent = '';
  document.getElementById('email-add-name').value  = '';
  document.getElementById('email-add-email').value = '';
  document.getElementById('email-add-org').value   = '';
  overlay.classList.add('open');

  if (_currentDocPatientId) {
    try {
      const r = await fetch(`/pt/api/patients/${encodeURIComponent(_currentDocPatientId)}/contacts/`);
      const d = await r.json();
      _emailContacts = d.contacts || [];
    } catch(_) {}
  }
  renderEmailContacts();
}

function closeEmailModal() {
  document.getElementById('email-modal-overlay').classList.remove('open');
}

const _ROLE_LABEL = { physician:'Physician', lawyer:'Lawyer', insurance:'Insurance', other:'Other' };

function renderEmailContacts() {
  const el = document.getElementById('email-contact-list');
  if (!_emailContacts.length) {
    el.innerHTML = '<p style="font-size:12px;color:#9ca3af;margin:0 0 8px;">저장된 수신자 없음. 아래에서 추가하세요.</p>';
    return;
  }
  el.innerHTML = _emailContacts.map(c => `
    <div class="email-contact-item">
      <input type="checkbox" id="ec-${c.id}" value="${c.id}" checked>
      <span class="email-contact-role ${c.role}">${_ROLE_LABEL[c.role] || c.role}</span>
      <div class="email-contact-info">
        <div class="email-contact-name">${esc(c.name)}${c.organization ? ' · ' + esc(c.organization) : ''}</div>
        <div class="email-contact-email">${esc(c.email)}</div>
      </div>
      <button class="email-contact-del" onclick="deleteEmailContact(${c.id})" title="삭제">✕</button>
    </div>`).join('');
}

async function addEmailContact() {
  const role  = document.getElementById('email-add-role').value;
  const name  = document.getElementById('email-add-name').value.trim();
  const email = document.getElementById('email-add-email').value.trim();
  const org   = document.getElementById('email-add-org').value.trim();
  if (!name || !email) { alert('이름과 이메일은 필수입니다.'); return; }
  const r = await fetch(`/pt/api/patients/${encodeURIComponent(_currentDocPatientId)}/contacts/`, {
    method: 'POST',
    headers: {'Content-Type':'application/json','X-CSRFToken':CSRF},
    body: JSON.stringify({role, name, email, organization: org}),
  });
  const d = await r.json();
  if (d.ok) {
    _emailContacts = _emailContacts.filter(c => c.role !== role);
    _emailContacts.push({id: d.id, role, name, email, organization: org});
    document.getElementById('email-add-name').value  = '';
    document.getElementById('email-add-email').value = '';
    document.getElementById('email-add-org').value   = '';
    renderEmailContacts();
  }
}

async function deleteEmailContact(contactId) {
  await fetch(`/pt/api/contacts/${contactId}/delete/`, {
    method: 'DELETE', headers: {'X-CSRFToken': CSRF},
  });
  _emailContacts = _emailContacts.filter(c => c.id !== contactId);
  renderEmailContacts();
}

async function sendDocumentEmail() {
  const checked = [...document.querySelectorAll('#email-contact-list input[type=checkbox]:checked')]
    .map(cb => _emailContacts.find(c => c.id == cb.value))
    .filter(Boolean);
  if (!checked.length) { alert('수신자를 선택하세요.'); return; }

  const btn    = document.getElementById('email-send-btn');
  const status = document.getElementById('email-send-status');
  btn.disabled = true;
  btn.textContent = '발송 중…';
  status.textContent = '';

  const title = document.getElementById('doc-modal-title')?.textContent || 'Document';

  try {
    const r = await fetch('/pt/api/docs/send-email/', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRFToken':CSRF},
      body: JSON.stringify({
        patient_id: _currentDocPatientId,
        doc_type:   _currentDocType,
        doc_title:  title,
        content:    _docModalCopyText,
        recipients: checked.map(c => ({id:c.id, name:c.name, email:c.email, role:c.role})),
      }),
    });
    const d = await r.json();
    if (d.ok) {
      const names = d.sent_to.map(s => s.name || s.email).join(', ');
      status.style.color = '#16a34a';
      status.textContent = `✓ 발송 완료: ${names}`;
      btn.textContent = '✉ 발송';
      btn.disabled = false;
      if (d.failed?.length) {
        status.textContent += ` (실패: ${d.failed.map(f=>f.email).join(', ')})`;
        status.style.color = '#b45309';
      }
    } else {
      status.style.color = '#dc2626';
      status.textContent = `오류: ${d.error || '발송 실패'}`;
      btn.textContent = '✉ 발송';
      btn.disabled = false;
    }
  } catch(e) {
    status.style.color = '#dc2626';
    status.textContent = `네트워크 오류: ${e.message}`;
    btn.textContent = '✉ 발송';
    btn.disabled = false;
  }
}
