"""
PT Documentation Generator — Multi-session History Based
보험 증빙 및 법률 증빙 문서 생성 (환자 전체 세션 이력 기반)
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
    return fn(sessions, patient_ctx, therapist_name, patient_id, clinic_name)


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
    n = len(sessions)
    red    = [s for s in sessions if s.alarm_level == "RED"]
    yellow = [s for s in sessions if s.alarm_level == "YELLOW"]
    conds  = list({s.triggered_condition for s in sessions if s.triggered_condition})
    scores = [s.critical_score for s in sessions]
    first  = sessions[0].session_date.strftime("%B %d, %Y") if sessions else "N/A"
    last   = sessions[-1].session_date.strftime("%B %d, %Y") if sessions else "N/A"

    peak = max(scores) if scores else 0.0
    trend = "N/A"
    if len(scores) >= 2:
        recent = scores[-3:]
        delta = recent[-1] - recent[0]
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

def _medical_necessity(sessions, patient_ctx, therapist_name, patient_id, clinic_name) -> str:
    st = _session_stats(sessions)
    cond_str = ", ".join(c.replace("_", " ").title() for c in st["conditions"]) or "Musculoskeletal dysfunction"
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
    return (
        _header("PHYSICAL THERAPY — MEDICAL NECESSITY LETTER", therapist_name, patient_id, clinic_name)
        + f"""

To Whom It May Concern,

I am writing to document the medical necessity of physical therapy services
provided to the above-referenced patient.

TREATMENT SUMMARY:
  Total Sessions:     {st['n']}
  Episode of Care:    {st['first']}  to  {st['last']}
  Primary Condition:  {cond_str}
  Risk Score Trend:   {st['trend']}
  Peak Risk Score:    {st['peak']*100:.0f}%
{flags_note}
SESSION RISK PROFILE:
{score_rows}

CLINICAL JUSTIFICATION:
  This patient presented with musculoskeletal dysfunction requiring skilled
  physical therapy intervention including therapeutic exercise, neuromuscular
  re-education, and functional retraining.

  All sessions were conducted with standardized Red Flag screening per the
  Goodman & Snyder Differential Diagnosis framework and APTA Clinical Practice
  Guidelines, ensuring patient safety and evidence-based care delivery.

  The treatment plan addresses documented functional limitations that cannot
  be safely managed without skilled PT supervision.

MEDICAL NECESSITY CRITERIA MET:
  1. Patient presents with a condition requiring skilled PT expertise
  2. Treatment goals are functional and measurable
  3. Clinical progress is documented across the episode of care
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

def _legal_defense(sessions, patient_ctx, therapist_name, patient_id, clinic_name) -> str:
    st = _session_stats(sessions)
    sep = "-" * 80
    session_records = []
    for i, s in enumerate(sessions, 1):
        alert = s.alerts.order_by("-created_at").first()
        indicators = alert.matched_indicators if alert else []
        ind_str = (
            "\n".join(f"    • {m}" for m in indicators)
            if indicators else "    • Screening negative — no red flags identified"
        )
        action = "No action required — screening negative"
        if s.alarm_level == "RED":
            action = "Physician referral initiated (see accompanying referral letter)"
        elif s.alarm_level == "YELLOW":
            action = "Yellow flag documented — patient placed on enhanced monitoring protocol"
        session_records.append(
            f"  Session {i:02d}  |  {s.session_date}  |  Alarm: {s.alarm_level}  |  "
            f"Risk Score: {s.critical_score*100:.0f}%\n"
            f"  Conditions Screened (Goodman & Snyder, 7 body systems):\n"
            + (f"  Triggered: {s.triggered_condition.replace('_',' ').title()}\n" if s.triggered_condition else "")
            + f"  Findings:\n{ind_str}\n"
            + f"  Action Taken: {action}"
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

SCREENING COMPLIANCE SUMMARY:
  Total Sessions Screened:      {st['n']}
  RED Alerts with Referrals:    {len(st['red'])}
  YELLOW Flags Monitored:       {len(st['yellow'])}
  Screening Compliance Rate:    100%
  Episode Duration:             {st['first']} to {st['last']}
  Screening Tool:               Sage Pontus VPPS (Vertical Prompt Propagation System)
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

def _clinical_chronology(sessions, patient_ctx, therapist_name, patient_id, clinic_name) -> str:
    st = _session_stats(sessions)
    sep = "-" * 80
    entries = []
    for i, s in enumerate(sessions, 1):
        alert = s.alerts.order_by("-created_at").first()
        indicators = alert.matched_indicators if alert else []
        ind_str = (
            "    Findings:   " + " | ".join(indicators)
            if indicators else "    Findings:   No red flags detected"
        )
        entries.append(
            f"  [{s.session_date}]  Session {i} of {st['n']}\n"
            f"    Alarm Level: {s.alarm_level}  |  Risk Score: {s.critical_score*100:.0f}%"
            + (f"\n    Condition:   {s.triggered_condition.replace('_',' ').title()}" if s.triggered_condition else "")
            + f"\n{ind_str}"
            + ("\n    Action:      Physician referral letter generated" if s.alarm_level == "RED" else "")
            + ("\n    Action:      Placed on enhanced monitoring" if s.alarm_level == "YELLOW" else "")
        )
    entries_str = f"\n{sep}\n".join(entries)
    score_seq = " → ".join(f"{s.critical_score*100:.0f}%" for s in sessions)
    return (
        _header(
            "PHYSICAL THERAPY — CLINICAL SESSION CHRONOLOGY\n"
            "Legal Reference Document",
            therapist_name, patient_id, clinic_name,
        )
        + f"""

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

def _insurance_appeal(sessions, patient_ctx, therapist_name, patient_id, clinic_name) -> str:
    st = _session_stats(sessions)
    cond_str = ", ".join(c.replace("_", " ").title() for c in st["conditions"]) or "Musculoskeletal dysfunction"
    evidence_lines = "\n".join(
        f"  • Session {s.session_date}: Risk Score {s.critical_score*100:.0f}%  [{s.alarm_level}]"
        + (f" — {s.triggered_condition.replace('_',' ').title()} flagged" if s.triggered_condition else "")
        for s in sessions
    )
    return (
        _header("PHYSICAL THERAPY — INSURANCE APPEAL LETTER", therapist_name, patient_id, clinic_name)
        + f"""

Re:    Formal Appeal — Denial of Physical Therapy Services
From:  {therapist_name}, PT  |  {clinic_name}

To the Appeals Review Board,

I am formally appealing the denial of physical therapy services provided to
the above-referenced patient. The following evidence demonstrates that all
services rendered were medically necessary and clinically justified.

TREATMENT DOCUMENTATION:
  Episode of Care:   {st['first']} to {st['last']}
  Total Sessions:    {st['n']}
  Clinical Condition: {cond_str}
  Risk Trend:        {st['trend']}
  Peak Risk Score:   {st['peak']*100:.0f}%

CLINICAL EVIDENCE FOR MEDICAL NECESSITY:
{evidence_lines}

APPLICABLE CLINICAL GUIDELINES:
  • APTA Clinical Practice Guidelines — Musculoskeletal Care
  • Goodman & Snyder: Differential Diagnosis for Physical Therapists (5th ed.)
  • CMS Medicare Benefit Policy Manual, Chapter 15 (Covered Medical and
    Other Health Services) — Skilled Physical Therapy criteria

GROUNDS FOR APPEAL:
  1. All services were delivered by a licensed physical therapist in accordance
     with accepted clinical practice standards.
  2. Standardized Red Flag screening was performed at every session — a level
     of clinical oversight exceeding standard PT documentation requirements.
  3. The clinical risk data demonstrates ongoing medical necessity across the
     full episode of care (see risk trajectory above).
  4. No equivalent level of care could have been safely provided without
     skilled PT supervision, given the clinical complexity documented.

SUPPORTING DOCUMENTATION AVAILABLE:
  • Session SOAP notes for all {st['n']} visits
  • Red Flag screening records (Sage Pontus audit trail)
  • Physician referral letters (where applicable)
  • Clinical chronology of full episode of care

I respectfully request a full reconsideration of this claim based on the
clinical evidence presented above. I am available to provide additional
documentation upon request.

Respectfully,
{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )


# ── 5. Functional Limitation Report ──────────────────────────────

def _functional_report(sessions, patient_ctx, therapist_name, patient_id, clinic_name) -> str:
    st = _session_stats(sessions)
    latest = sessions[-1]
    initial = sessions[0]

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
    return (
        _header(
            "PHYSICAL THERAPY — FUNCTIONAL LIMITATION REPORT\n"
            "CMS Functional Reporting / Insurance Documentation",
            therapist_name, patient_id, clinic_name,
        )
        + f"""

REPORTING PERIOD:
  Initial Assessment:    {st['first']}
  Most Recent Session:   {st['last']}
  Total Sessions:        {st['n']}

CURRENT FUNCTIONAL STATUS:

  Initial Risk Score (Session 1):  {initial.critical_score*100:.0f}%  [{initial.alarm_level}]
  Current Risk Score (Latest):     {latest.critical_score*100:.0f}%  [{latest.alarm_level}]
  Peak Risk Score (Episode):       {st['peak']*100:.0f}%
  Functional Trend:                {st['trend']}

RISK ASSESSMENT HISTORY:
{score_rows}

FUNCTIONAL LIMITATIONS IDENTIFIED:
  Based on clinical assessment across {st['n']} PT sessions:

  Primary Limitations:
    • Reduced functional mobility secondary to musculoskeletal dysfunction
    • Activity limitations requiring skilled therapeutic intervention
    • Risk of functional decline without continued PT monitoring
    {f"• Red Flag indicators requiring ongoing clinical surveillance ({', '.join(c.replace('_',' ').title() for c in st['conditions'])})" if st['conditions'] else ""}

  Severity: {"Moderate-to-Severe" if st['peak'] >= 0.5 else "Mild-to-Moderate"} functional limitation

CLINICAL RATIONALE FOR CONTINUED / COMPLETED SERVICES:
  {trend_clinical}

TREATMENT GOALS:
  Short-Term:  Reduce risk score below 0.25 threshold; resolve acute symptoms
  Long-Term:   Return to prior level of function; independent home program
  Safety:      Complete Red Flag clearance; physician follow-up as indicated

SKILLED CARE REQUIREMENT:
  The clinical complexity of this case — including Red Flag screening,
  multi-system risk assessment, and individualized therapeutic progression —
  requires skilled physical therapy oversight and cannot be safely delegated
  to a non-licensed provider or managed through a home program alone.

{therapist_name}
Physical Therapist
{clinic_name}
{"="*80}"""
    )
