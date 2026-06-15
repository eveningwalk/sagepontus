"""
PT Documentation Generator — Multi-session History Based
보험 증빙 및 법률 증빙 문서 생성 (환자 전체 세션 이력 + AI 임상 컨텍스트 기반)
"""

from __future__ import annotations

from datetime import date
from typing import Any


DOC_TITLES = {
    "medical_necessity":   "Medical Necessity Letter",
    "legal_defense":       "Standard of Care Defense Documentation",
    "clinical_chronology": "Clinical Session Chronology",
    "insurance_appeal":    "Insurance Appeal Letter",
    "functional_report":   "Functional Limitation Report",
}


def generate_document(
    doc_type: str,
    sessions: list,
    patient_ctx: dict[str, Any],
    therapist_name: str,
    patient_id: str,
    clinic_name: str = "",
    clinical_context: dict | None = None,
) -> str:
    generators = {
        "medical_necessity":   _medical_necessity,
        "legal_defense":       _legal_defense,
        "clinical_chronology": _clinical_chronology,
        "insurance_appeal":    _insurance_appeal,
        "functional_report":   _functional_report,
    }
    fn = generators.get(doc_type)
    if not fn:
        raise ValueError(f"Unknown doc_type: {doc_type}")
    ctx = clinical_context or {}
    return fn(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx)


# ── clinical_context 헬퍼 ──────────────────────────────────────────

def _as_str(val, sep: str = ", ") -> str:
    """list/tuple → 쉼표 구분 문자열, 이미 str이면 그대로."""
    if isinstance(val, (list, tuple)):
        return sep.join(str(v) for v in val if v)
    return str(val) if val else ""


def _patient_profile(ctx: dict) -> str:
    """patient_age + sex + diagnosis → 환자 설명 문자열."""
    parts = []
    if ctx.get("patient_age") and ctx.get("patient_sex"):
        sex = "male" if str(ctx["patient_sex"]).upper().startswith("M") else "female"
        parts.append(f"{ctx['patient_age']}-year-old {sex}")
    elif ctx.get("patient_age"):
        parts.append(f"{ctx['patient_age']}-year-old patient")
    if ctx.get("primary_diagnosis"):
        parts.append(f"with {_as_str(ctx['primary_diagnosis'])}")
    if ctx.get("comorbidities"):
        co = _as_str(ctx["comorbidities"])
        parts.append(f"(comorbidities: {co})")
    return " ".join(parts) if parts else "Patient with musculoskeletal dysfunction"


def _objective_findings_block(ctx: dict) -> str:
    """MMT, ROM, neurological, special tests → 문서용 들여쓰기 블록."""
    lines = []
    if ctx.get("vas_score"):
        lines.append(f"  Pain (VAS):              {ctx['vas_score']}")
    if ctx.get("mmt_findings"):
        lines.append("  Manual Muscle Testing:")
        for m in ctx["mmt_findings"]:
            lines.append(f"    • {m}")
    if ctx.get("rom_findings"):
        lines.append("  Range of Motion / Biomechanics:")
        for r in ctx["rom_findings"]:
            lines.append(f"    • {r}")
    if ctx.get("neurological_findings"):
        lines.append("  Neurological Screen:")
        for n in ctx["neurological_findings"]:
            lines.append(f"    • {n}")
    if ctx.get("special_tests"):
        lines.append("  Special Tests:")
        for t in ctx["special_tests"]:
            lines.append(f"    • {t}")
    return "\n".join(lines) if lines else "  (See session SOAP documentation)"


def _functional_lims_block(ctx: dict) -> str:
    lims = ctx.get("functional_limitations", [])
    if not lims:
        return "  Activity limitations requiring skilled therapeutic intervention"
    return "\n".join(f"  • {l}" for l in lims)


def _red_flag_block(ctx: dict) -> str:
    findings = ctx.get("red_flag_findings", [])
    return "\n".join(f"    • {f}" for f in findings) if findings else ""


def _precautions_block(ctx: dict) -> str:
    precs = ctx.get("precautions", [])
    return "\n".join(f"  • {p}" for p in precs) if precs else ""


def _goals_block(ctx: dict) -> str:
    """STG/LTG → 문서용 들여쓰기 블록. 데이터 없으면 빈 문자열."""
    lines = []
    stg = ctx.get("goals_stg") or []
    ltg = ctx.get("goals_ltg") or []
    if stg:
        lines.append("  Short-Term Goals (STG):")
        for g in stg:
            lines.append(f"    • {g}")
    if ltg:
        lines.append("  Long-Term Goals (LTG):")
        for g in ltg:
            lines.append(f"    • {g}")
    return "\n".join(lines)


# ── 공통 헬퍼 ─────────────────────────────────────────────────────

def _header(title: str, therapist_name: str, patient_id: str, clinic_name: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    clinic_line = f"{clinic_name}\n" if clinic_name else ""
    sep = "=" * 80
    return (
        f"{sep}\n"
        f"{title}\n"
        f"{sep}\n"
        f"Date:      {today}\n"
        f"From:      {therapist_name}, PT\n"
        f"{clinic_line}"
        f"Patient:   {patient_id} (anonymous ID — PHI withheld per HIPAA)\n"
        f"{sep}"
    )


def _session_stats(sessions: list) -> dict:
    n      = len(sessions)
    red    = [s for s in sessions if s.alarm_level == "RED"]
    yellow = [s for s in sessions if s.alarm_level == "YELLOW"]
    conds  = list({s.triggered_condition for s in sessions if s.triggered_condition})
    scores = [s.critical_score for s in sessions]
    first  = sessions[0].session_date.strftime("%B %d, %Y") if sessions else "N/A"
    last   = sessions[-1].session_date.strftime("%B %d, %Y") if sessions else "N/A"

    peak  = max(scores) if scores else 0.0
    trend = "N/A"
    if len(scores) >= 2:
        recent = scores[-3:]
        delta  = recent[-1] - recent[0]
        if delta > 0.15:
            trend = "Escalating (increasing risk)"
        elif delta < -0.15:
            trend = "Improving (decreasing risk)"
        else:
            trend = "Stable"

    return {
        "n": n, "red": red, "yellow": yellow, "conditions": conds,
        "scores": scores, "peak": peak, "trend": trend,
        "first": first, "last": last,
    }


# ── 1. Medical Necessity Letter ───────────────────────────────────

def _medical_necessity(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx) -> str:
    st = _session_stats(sessions)

    # Use initial session's clinical context for "at initial evaluation" sections.
    # ctx is the most recent session's data — wrong baseline for multi-session patients.
    init_ctx = (sessions[0].clinical_context or {}) if sessions else {}
    _init = init_ctx if any(
        init_ctx.get(k) for k in ("primary_diagnosis", "vas_score", "mmt_findings", "chief_complaint")
    ) else ctx

    patient_desc = _patient_profile(_init)
    cond_str = (
        _as_str(_init.get("primary_diagnosis"))
        or ", ".join(c.replace("_", " ").title() for c in st["conditions"])
        or "Musculoskeletal dysfunction"
    )

    obj_block  = _objective_findings_block(_init)
    func_block = _functional_lims_block(ctx)
    prec_block = _precautions_block(ctx)

    flags_note = ""
    if st["red"] or st["yellow"]:
        flags_note = (
            f"\nRED FLAG EVENTS:\n"
            f"  During the treatment episode, {len(st['red'])} RED and "
            f"{len(st['yellow'])} YELLOW alert(s) were detected via standardized\n"
            f"  Red Flag screening. Appropriate physician referrals were initiated\n"
            f"  as documented in the accompanying referral letters.\n"
        )

    score_rows = "\n".join(
        f"  {s.session_date}  |  Risk {s.critical_score*100:.0f}%  |  {s.alarm_level}"
        + (f"  |  {s.triggered_condition.replace('_',' ').title()}" if s.triggered_condition else "")
        for s in sessions
    )

    co = _init.get("comorbidities") or ctx.get("comorbidities")
    comorbidity_line = f"\n  Comorbidities:      {', '.join(co)}" if co else ""

    chief = (_as_str(_init.get('chief_complaint'))
             or _as_str(ctx.get('chief_complaint'))
             or 'Musculoskeletal pain and functional limitation')
    onset = (_as_str(_init.get('onset_duration'))
             or _as_str(ctx.get('onset_duration'))
             or 'As documented in initial evaluation')

    return (
        _header("PHYSICAL THERAPY — MEDICAL NECESSITY LETTER", therapist_name, patient_id, clinic_name)
        + f"""

To Whom It May Concern,

I am writing to document the medical necessity of physical therapy services
provided to the above-referenced patient.

PATIENT PROFILE:
  {patient_desc}{comorbidity_line}
  Chief Complaint:    {chief}
  Onset / Duration:   {onset}

TREATMENT SUMMARY:
  Total Sessions:     {st['n']}
  Episode of Care:    {st['first']}  to  {st['last']}
  Primary Condition:  {cond_str}
  Risk Score Trend:   {st['trend']}
  Peak Risk Score:    {st['peak']*100:.0f}%
{flags_note}
OBJECTIVE FINDINGS AT INITIAL EVALUATION:
{obj_block}

FUNCTIONAL LIMITATIONS:
{func_block}
{(chr(10) + "PRECAUTIONS:" + chr(10) + prec_block) if prec_block else ""}
SESSION RISK PROFILE:
{score_rows}

CLINICAL JUSTIFICATION:
  This patient — {patient_desc} — presented with functional deficits
  requiring skilled physical therapy intervention including therapeutic exercise,
  neuromuscular re-education, and functional retraining.

  All sessions were conducted with standardized Red Flag screening per the
  Goodman & Snyder Differential Diagnosis framework and APTA Clinical Practice
  Guidelines, ensuring patient safety and evidence-based care delivery.

TREATMENT GOALS:
{_goals_block(ctx) or "  (Refer to session SOAP documentation for goal details)"}

MEDICAL NECESSITY CRITERIA MET:
  1. Patient presents with a condition requiring skilled PT expertise
  2. Objective measurements document functional deficits (see findings above)
  3. Treatment goals are functional and measurable (see above)
  4. Red Flag screening performed at every session — safety maintained

I certify that the services provided were medically necessary and performed
in accordance with accepted standards of clinical practice.

Respectfully,
{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )


# ── 2. Standard of Care Defense ──────────────────────────────────

def _legal_defense(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx) -> str:
    st  = _session_stats(sessions)
    sep = "-" * 80

    rf_specific = _red_flag_block(ctx)
    neuro_block = ""
    if ctx.get("neurological_findings"):
        neuro_block = "\n  Neurological Findings Documented:\n" + "\n".join(
            f"    • {n}" for n in ctx["neurological_findings"]
        )

    session_records = []
    for i, s in enumerate(sessions, 1):
        alert      = s.alerts.order_by("-created_at").first()
        indicators = alert.matched_indicators if alert else []
        ind_str    = (
            "\n".join(f"    • {m}" for m in indicators)
            if indicators else "    • Screening negative — no red flags identified"
        )
        action = "No action required — screening negative"
        if s.alarm_level == "RED":
            action = "Physician referral initiated (see accompanying referral letter)"
        elif s.alarm_level == "YELLOW":
            action = "Yellow flag documented — patient placed on enhanced monitoring protocol"

        # session-level clinical context
        s_ctx = s.clinical_context or {}
        obj_note = ""
        if s_ctx.get("mmt_findings") or s_ctx.get("neurological_findings"):
            obj_items = s_ctx.get("mmt_findings", []) + s_ctx.get("neurological_findings", [])
            obj_note  = "\n  Objective Findings:\n" + "\n".join(f"    • {x}" for x in obj_items)

        session_records.append(
            f"  Session {i:02d}  |  {s.session_date}  |  Alarm: {s.alarm_level}  |  "
            f"Risk Score: {s.critical_score*100:.0f}%\n"
            f"  Conditions Screened (Goodman & Snyder, 7 body systems):\n"
            + (f"  Triggered: {s.triggered_condition.replace('_',' ').title()}\n" if s.triggered_condition else "")
            + f"  Findings:\n{ind_str}\n"
            + obj_note
            + f"\n  Action Taken: {action}"
        )
    records_str = f"\n{sep}\n".join(session_records)

    return (
        _header(
            "PHYSICAL THERAPY — STANDARD OF CARE DEFENSE DOCUMENTATION\n"
            "CLINICAL RED FLAG SCREENING AUDIT TRAIL",
            therapist_name, patient_id, clinic_name,
        )
        + f"""

LEGAL NOTICE:
  This document constitutes an official audit trail certifying that Red Flag
  screening was performed at every physical therapy session in accordance with:
    - Goodman & Snyder: Differential Diagnosis for Physical Therapists (5th ed.)
    - APTA Clinical Practice Guidelines
    - American Physical Therapy Association Code of Ethics
    - Applicable State PT Practice Act requirements

PATIENT CLINICAL PROFILE:
  {_patient_profile(ctx)}
  Chief Complaint:  {_as_str(ctx.get('chief_complaint')) or 'Musculoskeletal dysfunction'}
{neuro_block}
{("  Objective Red Flag Signs Documented:\n" + rf_specific) if rf_specific else ""}

SCREENING COMPLIANCE SUMMARY:
  Total Sessions Screened:      {st['n']}
  RED Alerts with Referrals:    {len(st['red'])}
  YELLOW Flags Monitored:       {len(st['yellow'])}
  Screening Compliance Rate:    100%
  Episode Duration:             {st['first']} to {st['last']}
  Screening Tool:               Sage Pontus VPPA (Vertical Prompt Propagation Architecture)
                                based on Goodman & Snyder Differential Diagnosis

DETAILED SESSION SCREENING RECORD:
{sep}
{records_str}
{sep}

CERTIFICATION:
  I, {therapist_name}, PT, certify that standardized Red Flag screening was
  conducted at every session listed above. All identified Red Flags were
  escalated with appropriate urgency per evidence-based guidelines. No sessions
  were conducted without screening. This document is an accurate representation
  of the clinical decision-making process throughout this episode of care.

{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )


# ── 3. Clinical Session Chronology ───────────────────────────────

def _clinical_chronology(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx) -> str:
    st  = _session_stats(sessions)
    sep = "-" * 80

    entries = []
    for i, s in enumerate(sessions, 1):
        alert      = s.alerts.order_by("-created_at").first()
        indicators = alert.matched_indicators if alert else []
        ind_str    = (
            "    Findings:   " + " | ".join(indicators)
            if indicators else "    Findings:   No red flags detected"
        )
        # per-session clinical data
        s_ctx = s.clinical_context or {}
        vas_line = f"\n    VAS:         {s_ctx['vas_score']}" if s_ctx.get("vas_score") else ""

        entries.append(
            f"  [{s.session_date}]  Session {i} of {st['n']}\n"
            f"    Alarm Level: {s.alarm_level}  |  Risk Score: {s.critical_score*100:.0f}%"
            + (f"\n    Condition:   {s.triggered_condition.replace('_',' ').title()}" if s.triggered_condition else "")
            + vas_line
            + f"\n{ind_str}"
            + ("\n    Action:      Physician referral letter generated" if s.alarm_level == "RED" else "")
            + ("\n    Action:      Placed on enhanced monitoring" if s.alarm_level == "YELLOW" else "")
        )
    entries_str = f"\n{sep}\n".join(entries)
    score_seq   = " → ".join(f"{s.critical_score*100:.0f}%" for s in sessions)

    return (
        _header(
            "PHYSICAL THERAPY — CLINICAL SESSION CHRONOLOGY\n"
            "Legal Reference Document",
            therapist_name, patient_id, clinic_name,
        )
        + f"""

PATIENT PROFILE:
  {_patient_profile(ctx)}
  Chief Complaint:  {_as_str(ctx.get('chief_complaint')) or 'Musculoskeletal dysfunction'}

EPISODE SUMMARY:
  Episode Duration:  {st['first']}  to  {st['last']}
  Total Sessions:    {st['n']}
  Overall Trend:     {st['trend']}
  Peak Risk Score:   {st['peak']*100:.0f}%
  RED Alerts:        {len(st['red'])}
  YELLOW Flags:      {len(st['yellow'])}
  Conditions Noted:  {', '.join(c.replace('_',' ').title() for c in st['conditions']) or 'None'}

RISK SCORE TRAJECTORY:
  {score_seq}

CHRONOLOGICAL SESSION RECORD:
{sep}
{entries_str}
{sep}

This chronology was generated from the Sage Pontus PT Red Flag Screening
System and reflects the documented clinical record for this patient episode.

{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )


# ── 4. Insurance Appeal Letter ────────────────────────────────────

def _insurance_appeal(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx) -> str:
    st = _session_stats(sessions)

    # Use initial session's clinical context for baseline measurements (Bug #1 fix)
    init_ctx = (sessions[0].clinical_context or {}) if sessions else {}
    _init = init_ctx if any(
        init_ctx.get(k) for k in ("primary_diagnosis", "vas_score", "mmt_findings", "chief_complaint")
    ) else ctx

    cond_str = (
        _as_str(_init.get("primary_diagnosis"))
        or ", ".join(c.replace("_", " ").title() for c in st["conditions"])
        or "Musculoskeletal dysfunction"
    )

    # Baseline objective measurements from initial evaluation
    quantified_lines = []
    if _init.get("vas_score"):
        quantified_lines.append(f"  • Pain Level (VAS): {_init['vas_score']} — documented functional pain interference")
    if _init.get("mmt_findings"):
        for m in _init["mmt_findings"]:
            quantified_lines.append(f"  • Strength Deficit: {m}")
    if _init.get("rom_findings"):
        for r in _init["rom_findings"]:
            quantified_lines.append(f"  • ROM Finding: {r}")
    if _init.get("neurological_findings"):
        for n in _init["neurological_findings"]:
            quantified_lines.append(f"  • Neurological: {n}")
    if ctx.get("functional_limitations"):
        for l in ctx["functional_limitations"]:
            quantified_lines.append(f"  • Functional Limit: {l}")

    quantified_str = "\n".join(quantified_lines) if quantified_lines else \
        "  (Refer to session SOAP documentation for objective measurements)"

    # Bug #2: only reference "VAS, MMT, ROM data above" when that data actually exists
    has_obj_data = bool(quantified_lines and any(
        _init.get(k) for k in ("vas_score", "mmt_findings", "rom_findings")
    ))
    grounds_1 = (
        "  1. Objective measurements document measurable deficits requiring skilled PT\n"
        "     (VAS, MMT, ROM data above — see initial evaluation findings)."
        if has_obj_data else
        "  1. Patient presents with functional deficits requiring skilled physical therapy\n"
        "     evaluation and treatment, as documented in session SOAP notes."
    )

    evidence_lines = "\n".join(
        f"  • Session {s.session_date}: Risk Score {s.critical_score*100:.0f}%  [{s.alarm_level}]"
        + (f" — {s.triggered_condition.replace('_',' ').title()} flagged" if s.triggered_condition else "")
        for s in sessions
    )

    co = _init.get("comorbidities") or ctx.get("comorbidities")
    comorbidity_note = f"\n  Comorbidities:      {', '.join(co)}" if co else ""

    chief = (_as_str(_init.get('chief_complaint'))
             or _as_str(ctx.get('chief_complaint'))
             or 'Musculoskeletal pain and dysfunction')

    return (
        _header("PHYSICAL THERAPY — INSURANCE APPEAL LETTER", therapist_name, patient_id, clinic_name)
        + f"""

Re:    Formal Appeal — Denial of Physical Therapy Services
From:  {therapist_name}, PT  |  {clinic_name}

To the Appeals Review Board,

I am formally appealing the denial of physical therapy services provided to
the above-referenced patient. The following evidence demonstrates that all
services rendered were medically necessary and clinically justified.

PATIENT PROFILE:
  {_patient_profile(_init)}
  Chief Complaint:    {chief}{comorbidity_note}

TREATMENT DOCUMENTATION:
  Episode of Care:    {st['first']} to {st['last']}
  Total Sessions:     {st['n']}
  Clinical Condition: {cond_str}
  Risk Trend:         {st['trend']}
  Peak Risk Score:    {st['peak']*100:.0f}%

OBJECTIVE MEASUREMENTS SUPPORTING MEDICAL NECESSITY:
{quantified_str}

CLINICAL EVIDENCE FOR MEDICAL NECESSITY (SESSION-BY-SESSION):
{evidence_lines}

APPLICABLE CLINICAL GUIDELINES:
  • APTA Clinical Practice Guidelines — Musculoskeletal Care
  • Goodman & Snyder: Differential Diagnosis for Physical Therapists (5th ed.)
  • CMS Medicare Benefit Policy Manual, Chapter 15 — Skilled Physical Therapy criteria

GROUNDS FOR APPEAL:
{grounds_1}
  2. All services were delivered by a licensed physical therapist in accordance
     with accepted clinical practice standards.
  3. Standardized Red Flag screening was performed at every session — a level
     of clinical oversight exceeding standard PT documentation requirements.
  4. The clinical risk data demonstrates ongoing medical necessity across the
     full episode of care (see risk trajectory above).

SUPPORTING DOCUMENTATION AVAILABLE:
  • Session SOAP notes for all {st['n']} visits
  • Red Flag screening records (Sage Pontus audit trail)
  • Physician referral letters (where applicable)
  • Clinical chronology of full episode of care

I respectfully request a full reconsideration of this claim based on the
clinical evidence presented above.

Respectfully,
{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )


# ── 5. Functional Limitation Report ──────────────────────────────

def _functional_report(sessions, patient_ctx, therapist_name, patient_id, clinic_name, ctx) -> str:
    st      = _session_stats(sessions)
    latest  = sessions[-1]
    initial = sessions[0]

    # Per-session clinical context for initial vs current
    init_ctx   = initial.clinical_context or {}
    latest_ctx = latest.clinical_context or {}

    trend_clinical = {
        "Escalating (increasing risk)": "Patient functional status has declined. Continued skilled PT essential to prevent further deterioration and manage escalating risk indicators.",
        "Improving (decreasing risk)":  "Patient demonstrates measurable functional improvement. Continued PT indicated to consolidate gains and achieve discharge goals.",
        "Stable":                       "Patient functional status is stable. Continued PT indicated to maintain current level and progress toward functional goals.",
        "N/A":                          "Insufficient session data for trend analysis.",
    }.get(st["trend"], "Clinical reassessment recommended.")

    score_rows = "\n".join(
        f"  {s.session_date}  |  Risk {s.critical_score*100:.0f}%  |  {s.alarm_level}"
        for s in sessions
    )

    # Initial objective findings
    init_obj = _objective_findings_block(init_ctx) if init_ctx else _objective_findings_block(ctx)

    # Functional limitations (prefer latest session context)
    func_lims = (latest_ctx.get("functional_limitations") or ctx.get("functional_limitations") or [])
    func_block = "\n".join(f"    • {l}" for l in func_lims) if func_lims else \
        "    • Activity limitations documented in SOAP notes"

    # Precautions
    precs = (latest_ctx.get("precautions") or ctx.get("precautions") or [])
    prec_block = "\n".join(f"    • {p}" for p in precs) if precs else ""

    severity = "Moderate-to-Severe" if st["peak"] >= 0.5 else "Mild-to-Moderate"

    return (
        _header(
            "PHYSICAL THERAPY — FUNCTIONAL LIMITATION REPORT\n"
            "CMS Functional Reporting / Insurance Documentation",
            therapist_name, patient_id, clinic_name,
        )
        + f"""

PATIENT PROFILE:
  {_patient_profile(ctx)}
  Chief Complaint:  {_as_str(ctx.get('chief_complaint')) or 'Musculoskeletal dysfunction'}
  Comorbidities:    {', '.join(ctx['comorbidities']) if ctx.get('comorbidities') else 'None documented'}

REPORTING PERIOD:
  Initial Assessment:    {st['first']}
  Most Recent Session:   {st['last']}
  Total Sessions:        {st['n']}

BASELINE OBJECTIVE FINDINGS (Initial Evaluation):
{init_obj}

CURRENT FUNCTIONAL STATUS:
  Initial Risk Score (Session 1):  {initial.critical_score*100:.0f}%  [{initial.alarm_level}]
  Current Risk Score (Latest):     {latest.critical_score*100:.0f}%  [{latest.alarm_level}]
  Peak Risk Score (Episode):       {st['peak']*100:.0f}%
  Functional Trend:                {st['trend']}

RISK ASSESSMENT HISTORY:
{score_rows}

FUNCTIONAL LIMITATIONS IDENTIFIED:
  Severity: {severity} functional limitation

  Documented Limitations:
{func_block}
{(chr(10) + "  Precautions / Safety Concerns:" + chr(10) + prec_block) if prec_block else ""}

CLINICAL RATIONALE FOR CONTINUED / COMPLETED SERVICES:
  {trend_clinical}

TREATMENT GOALS:
{_goals_block(ctx) or "  Short-Term:  Reduce risk score below 0.25; resolve acute functional deficits\n  Long-Term:   Return to prior level of function; independent home program"}
  Safety:      Complete Red Flag clearance; physician follow-up as indicated

SKILLED CARE REQUIREMENT:
  The clinical complexity of this case — including Red Flag screening,
  multi-system risk assessment, and individualized therapeutic progression —
  requires skilled physical therapy oversight.

{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )
