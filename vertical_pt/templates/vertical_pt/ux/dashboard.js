// 환자 데이터 및 임시 메모리 스토어
let currentSoapTab = 'S';
const soapNotesStore = { S: '', O: '', A: '', P: '' };
const mockPatients = [
  { name: 'Jordan Miller', id: 'FC-260518-001', date: '2026-05-23', alarm: 'RED', meta: 'Progressive neuro deficit' },
  { name: 'Avery Chen', id: 'FC-260515-042', date: '2026-05-20', alarm: 'YELLOW', meta: 'Night pain, physician checkup' },
  { name: 'Morgan Davis', id: 'FC-260510-011', date: '2026-05-18', alarm: 'GREEN', meta: 'Continue PT, documented' }
];

document.addEventListener('DOMContentLoaded', () => {
  renderPatientList(mockPatients);
  setCurrentDate();
  bindSoapInput();
  updateDraftState();
  setActiveView('new');
  showApp();
});

function showLanding() {
  const landing = document.getElementById('landing-page');
  const app = document.getElementById('app-shell');
  if (landing) landing.style.display = 'block';
  if (app) app.style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showApp() {
  const landing = document.getElementById('landing-page');
  const app = document.getElementById('app-shell');
  if (landing) landing.style.display = 'none';
  if (app) app.style.display = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showLandingSection(sectionName) {
  showLanding();
  requestAnimationFrame(() => {
    const target = document.getElementById(`landing-${sectionName}`);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

// 환자 목록 사이드바 주입 및 검색 필터링
function renderPatientList(patients) {
  const listContainer = document.getElementById('patient-list');
  const countBadge = document.getElementById('patient-count');
  if(!listContainer) return;

  countBadge.textContent = patients.length;
  if (!patients.length) {
    listContainer.innerHTML = '<div class="pt-empty-sidebar">No matching patients.</div>';
    return;
  }
  listContainer.innerHTML = patients.map(p => `
    <div class="pt-patient-item" onclick="selectPatient('${p.id}')">
      <div class="pt-alarm-dot ${p.alarm}"></div>
      <div style="flex:1; min-width:0;">
        <div class="pt-user-name" style="color:#e2e8f0;">${p.name} (${p.id})</div>
        <div class="pt-user-meta">${p.date} · ${p.meta}</div>
      </div>
    </div>
  `).join('');
}

function filterPatients(query) {
  const q = query.trim().toLowerCase();
  const filtered = mockPatients.filter(p =>
    p.name.toLowerCase().includes(q) ||
    p.id.toLowerCase().includes(q) ||
    p.meta.toLowerCase().includes(q)
  );
  renderPatientList(filtered);
}

function selectPatient(patientId) {
  const patient = mockPatients.find(p => p.id === patientId);
  if (!patient) return;

  setActiveView('new');
  document.getElementById('inp-name').value = patient.name;
  document.getElementById('inp-id').value = patient.id;
  document.getElementById('inp-date').value = patient.date;
  document.querySelectorAll('.pt-patient-item').forEach(item => item.classList.remove('active'));
  const items = Array.from(document.querySelectorAll('.pt-patient-item'));
  const selected = items.find(item => item.textContent.includes(patient.id));
  if (selected) selected.classList.add('active');

  document.getElementById('draft-status').textContent = 'Patient loaded';
  document.getElementById('draft-status').className = 'pt-status-pill success';
}

function showNewSession() {
  setActiveView('new');
  document.getElementById('soapForm').reset();
  Object.keys(soapNotesStore).forEach(key => { soapNotesStore[key] = ''; });
  document.querySelectorAll('.rf-chip.active').forEach(chip => chip.classList.remove('active'));
  document.querySelectorAll('.pt-patient-item.active').forEach(item => item.classList.remove('active'));
  switchSoapTab('S');
  setCurrentDate();
  document.getElementById('result-placeholder').style.display = 'block';
  document.getElementById('result-placeholder').innerHTML = `
    <div class="pt-empty">
      <div class="pt-empty-icon">Protocol</div>
      <div class="pt-empty-title">Ready to classify this visit</div>
      <div class="pt-empty-text">FlagChart will return the care escalation level, clinical rationale, and documentation packet for referral, insurance, and legal defensibility.</div>
    </div>
  `;
  document.getElementById('result-content').style.display = 'none';
  const resultStatus = document.getElementById('result-status');
  if (resultStatus) {
    resultStatus.textContent = 'Ready';
    resultStatus.className = 'pt-status-pill neutral';
  }
  updateDraftState();
}

function showAlarms() {
  setActiveView('alarms');
}

function showDocs() {
  setActiveView('docs');
}

function showProtocolGuide() {
  setActiveView('protocol');
}

function setActiveView(viewName) {
  const views = {
    new: 'view-new',
    alarms: 'view-alarms',
    docs: 'view-docs',
    protocol: 'view-protocol'
  };

  Object.entries(views).forEach(([key, id]) => {
    const el = document.getElementById(id);
    if (el) el.style.display = key === viewName ? 'block' : 'none';
  });

  document.querySelectorAll('.pt-menu-btn, .pt-new-btn').forEach(btn => btn.classList.remove('active'));
  const activeMap = {
    new: 'menu-new',
    alarms: 'menu-alarms',
    docs: 'menu-docs',
    protocol: 'menu-protocol'
  };
  const activeBtn = document.getElementById(activeMap[viewName]);
  if (activeBtn) activeBtn.classList.add('active');
}

function previewDoc(type) {
  const preview = document.getElementById('doc-preview');
  const templates = {
    referral: `PHYSICIAN REFERRAL LETTER\n\nPatient: Jordan Miller\nFlag status: RED FLAG\n\nClinical concern:\nProgressive neurological findings were identified during PT screening. Findings meet FlagChart's immediate medical referral threshold.\n\nRequested action:\nPlease evaluate for appropriate medical workup and advise whether PT may continue, pause, or modify plan of care.\n\nAttached support:\nSOAP findings, flag indicators, patient education, and PT communication log.`,
    insurance: `MEDICAL NECESSITY RATIONALE\n\nFlag status: YELLOW FLAG\n\nThe plan of care remains medically necessary because skilled PT is required to monitor symptom behavior, document response to intervention, and coordinate medical checkup when indicated.\n\nPayer support:\nObjective findings, patient-reported limitations, clinical screening results, and follow-up plan are documented for review.`,
    audit: `LEGAL AUDIT TRAIL\n\nScreening timestamp: Today\nClinician: Maya Lee, DPT\nProtocol reviewed: Red / Yellow / Green flag screen\n\nDocumentation checkpoints:\n- Flag classification recorded\n- Patient education documented\n- Referral or checkup recommendation captured\n- Follow-up plan retained in chart`
  };

  if (preview) preview.textContent = templates[type] || templates.referral;
}

function runReseed() {
  showNewSession();
  renderPatientList(mockPatients);
}

function runBackfill() {
  showAlarms();
}

function bindSoapInput() {
  const tx = document.getElementById('soap-content');
  if (!tx) return;
  tx.addEventListener('input', () => {
    soapNotesStore[currentSoapTab] = tx.value;
    updateDraftState();
  });
}

function updateDraftState() {
  const tx = document.getElementById('soap-content');
  const draft = document.getElementById('draft-status');
  const counter = document.getElementById('soap-counter');
  if (tx) soapNotesStore[currentSoapTab] = tx.value;

  Object.entries(soapNotesStore).forEach(([tab, value]) => {
    const btn = document.getElementById(`stab-${tab}`);
    if (btn) btn.classList.toggle('has-text', value.trim().length > 0);
  });

  const totalChars = Object.values(soapNotesStore).reduce((sum, value) => sum + value.trim().length, 0);
  if (counter) counter.textContent = `${(soapNotesStore[currentSoapTab] || '').length} chars`;
  if (draft) {
    draft.textContent = totalChars > 0 ? 'In progress' : 'Draft';
    draft.className = `pt-status-pill${totalChars > 0 ? ' warn' : ''}`;
  }
}

// SOAP 탭 데이터 동적 동기화
function switchSoapTab(tab) {
  // 현재 입력값 메모리에 캐싱
  const tx = document.getElementById('soap-content');
  soapNotesStore[currentSoapTab] = tx.value;

  // 활성 탭 인디케이터 변경
  document.querySelectorAll('.soap-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`stab-${tab}`).classList.add('active');

  // 새로운 탭 데이터 덮어쓰기
  currentSoapTab = tab;
  tx.value = soapNotesStore[tab];
  const helperCopy = {
    S: 'S: Capture patient-reported symptoms, history, and functional impact.',
    O: 'O: Record objective tests, vitals, neuro screen, ROM, strength, and observation.',
    A: 'A: Document clinical interpretation, differential concerns, and flag rationale.',
    P: 'P: Capture treatment plan, referral plan, patient education, and follow-up.'
  };
  const placeholders = {
    S: 'Chief complaint, symptom behavior, onset, aggravating/easing factors, medical history...',
    O: 'ROM, strength, sensation, reflexes, special tests, vitals, gait, and functional measures...',
    A: 'Clinical impression, differential concerns, medical necessity, and flag interpretation...',
    P: 'Plan of care, education, HEP, referral plan, communication, and follow-up...'
  };
  tx.placeholder = placeholders[tab];
  document.getElementById('soap-helper').textContent = helperCopy[tab];
  updateDraftState();
}

// 위험 신호 인터랙티브 칩 제어
function toggleChip(chipElement) {
  chipElement.classList.toggle('active');
  updateDraftState();
}

// 환자 ID 날짜 기반 난수 생성기
function generatePatientId() {
  const now = new Date();
  const yy = String(now.getFullYear()).slice(-2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const rand = Math.floor(1000 + Math.random() * 9000);
  document.getElementById('inp-id').value = `FC-${yy}${mm}${dd}-${rand}`;
  updateDraftState();
}

function setCurrentDate() {
  const dateInput = document.getElementById('inp-date');
  if(dateInput) dateInput.value = new Date().toISOString().substring(0, 10);
}

// 분석 처리 핸들러 (Mocking 파이프라인)
function handleAnalyze(event) {
  event.preventDefault();
  const btn = document.getElementById('analyze-btn');
  const spinner = document.getElementById('btn-spinner');
  const alertBox = document.getElementById('form-alert');
  const resultStatus = document.getElementById('result-status');
  const tx = document.getElementById('soap-content');
  soapNotesStore[currentSoapTab] = tx.value;
  const combinedSoap = Object.values(soapNotesStore).join('\n').trim();
  const activeChips = document.querySelectorAll('.rf-chip.active');

  if (!combinedSoap && activeChips.length === 0) {
    alertBox.textContent = 'Enter SOAP content or select at least one clinical flag indicator.';
    alertBox.classList.add('show');
    tx.focus();
    return;
  }

  alertBox.classList.remove('show');
  
  btn.disabled = true;
  spinner.style.display = 'inline-block';
  if (resultStatus) {
    resultStatus.textContent = 'Analyzing';
    resultStatus.className = 'pt-status-pill warn';
  }

  // AI 분석 엔진 작동 딜레이 시뮬레이션
  setTimeout(() => {
    btn.disabled = false;
    spinner.style.display = 'none';

    // 결과 창 마운트 및 플레이스홀더 전환
    document.getElementById('result-placeholder').style.display = 'none';
    const content = document.getElementById('result-content');
    content.style.display = 'block';

    // Mock protocol branch: red overrides yellow; no selected flags returns green.
    const banner = document.getElementById('res-banner');
    const scoreFill = document.getElementById('res-score-bar');
    const scorePct = document.getElementById('res-score-pct');
    const hitsContainer = document.getElementById('res-hits');
    const letterBox = document.getElementById('res-letter');
    const hasRed = Array.from(activeChips).some(c => c.dataset.level === 'RED');
    const hasYellow = Array.from(activeChips).some(c => c.dataset.level === 'YELLOW');

    if(hasRed) {
      banner.className = 'pt-alarm-banner RED';
      document.getElementById('res-icon').textContent = 'RED';
      document.getElementById('res-level').textContent = 'RED FLAG — Immediate medical referral';
      document.getElementById('res-cond').textContent = 'Medical screening threshold met. Do not delay referral.';
      scoreFill.style.width = '88%';
      scoreFill.style.background = '#dc2626';
      scorePct.textContent = '88%';
      
      hitsContainer.innerHTML = Array.from(activeChips).map(c => `
        <div class="pt-hit-item">Detected indicator: ${c.textContent.replace('✓ ', '')}</div>
      `).join('');

      letterBox.textContent = `PHYSICIAN REFERRAL SUMMARY\n\nFlagChart protocol classification: RED FLAG\n\nReason for escalation:\nThe patient presented with clinical findings that meet the immediate medical referral threshold for PT screening. Continued conservative care should be deferred until medical review is completed.\n\nRecommended action:\nUrgent physician evaluation and appropriate diagnostic workup.\n\nINSURANCE / LEGAL DOCUMENTATION\nMedical necessity for referral is supported by documented red flag indicators, objective clinical screening, patient-reported symptoms, and PT clinical judgment. This note should be retained with the visit record and referral communication log.`;
      if (resultStatus) {
        resultStatus.textContent = 'Action required';
        resultStatus.className = 'pt-status-pill warn';
      }
    } else if (hasYellow) {
      banner.className = 'pt-alarm-banner YELLOW';
      document.getElementById('res-icon').textContent = 'YELLOW';
      document.getElementById('res-level').textContent = 'YELLOW FLAG — Physician checkup recommended';
      document.getElementById('res-cond').textContent = 'Continue caution, document rationale, coordinate follow-up.';
      scoreFill.style.width = '54%';
      scoreFill.style.background = '#d97706';
      scorePct.textContent = '54%';

      hitsContainer.innerHTML = Array.from(activeChips).map(c => `
        <div class="pt-hit-item" style="background:#fffbeb;border-color:#fde68a;color:#92400e;">Detected indicator: ${c.textContent.replace('✓ ', '')}</div>
      `).join('');

      letterBox.textContent = `PHYSICIAN CHECKUP NOTICE\n\nFlagChart protocol classification: YELLOW FLAG\n\nReason for escalation:\nThe patient does not currently meet the urgent referral threshold, but selected findings warrant physician checkup, monitoring, and clear documentation.\n\nRecommended action:\nNotify the referring provider or advise medical checkup based on clinic policy. Continue PT only with documented clinical reasoning, patient education, and monitoring plan.\n\nINSURANCE / LEGAL DOCUMENTATION\nYellow flag rationale, patient communication, provider notification, and follow-up plan are documented to support clinical decision-making and payer review.`;
      if (resultStatus) {
        resultStatus.textContent = 'Checkup advised';
        resultStatus.className = 'pt-status-pill warn';
      }
    } else {
      banner.className = 'pt-alarm-banner GREEN';
      document.getElementById('res-icon').textContent = 'GREEN';
      document.getElementById('res-level').textContent = 'GREEN FLAG — Continue PT';
      document.getElementById('res-cond').textContent = 'No current medical referral trigger identified in this mock screen.';
      scoreFill.style.width = '12%';
      scoreFill.style.background = '#16a34a';
      scorePct.textContent = '12%';
      hitsContainer.innerHTML = '<div class="pt-hit-item" style="background:#f0fdf4; border-color:#bbf7d0; color:#16a34a;">No selected indicators triggered red or yellow protocol thresholds.</div>';
      letterBox.textContent = `PT CONTINUATION NOTE\n\nFlagChart protocol classification: GREEN FLAG\n\nClinical disposition:\nContinue conservative physical therapy with routine monitoring. Re-screen if symptoms change, new systemic symptoms appear, or functional status declines.\n\nINSURANCE / LEGAL DOCUMENTATION\nCurrent plan of care is supported by documented screening, absence of selected escalation indicators, and continued monitoring instructions.`;
      if (resultStatus) {
        resultStatus.textContent = 'Complete';
        resultStatus.className = 'pt-status-pill success';
      }
    }
  }, 1200);
}

// 클립보드 복사 유틸리티
function copyReferralText(event) {
  const text = document.getElementById('res-letter').innerText;
  navigator.clipboard.writeText(text).then(() => {
    const originalText = event.target.textContent;
    event.target.textContent = 'Copied';
    setTimeout(() => { event.target.textContent = originalText; }, 2000);
  });
}
