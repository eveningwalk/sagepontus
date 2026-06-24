"""
Referral Letter Generator
Red Flag 알람 → 의사 리퍼럴 레터 자동 생성

근거 기반 작성: 임상 가이드라인 인용, 할루시네이션 배제.
"""

from __future__ import annotations

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)


def _strip_md(text: str) -> str:
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}',   r'\1', text)
    text = re.sub(r'^#{1,6}\s+(.+)$', lambda m: m.group(1).upper() + ':', text, flags=re.MULTILINE)
    text = re.sub(r'`{1,3}', '', text)
    return text.strip()

_SCREENING_SOURCE_LABELS: dict[str, str] = {
    "pmh":                   "Past Medical History",
    "risk_factor":           "Risk Factors",
    "clinical_presentation": "Clinical Presentation",
    "associated_symptoms":   "Associated Signs & Symptoms",
    "ros":                   "Review of Systems",
}

_SOURCE_ORDER = ["pmh", "risk_factor", "clinical_presentation", "associated_symptoms", "ros", "other"]


def _format_indicators_grouped(matched: list[str], breakdown: dict[str, list[str]]) -> str:
    """screening_breakdown 있으면 카테고리별 그룹, 없으면 단순 목록."""
    if not breakdown:
        return "\n".join(f"  • {m}" for m in matched)
    lines: list[str] = []
    for src in _SOURCE_ORDER:
        items = breakdown.get(src, [])
        if not items:
            continue
        label = _SCREENING_SOURCE_LABELS.get(src, src.replace("_", " ").title())
        lines.append(f"  [{label}]")
        lines.extend(f"    • {item}" for item in items)
    return "\n".join(lines)


_CONDITION_META = {
    "cauda_equina": {
        "title":    "Cauda Equina Syndrome (마미총 증후군)",
        "urgency":  "EMERGENCY — Same-day ER referral",
        "guideline":"APTA Clinical Practice Guidelines; Goodman & Snyder Ch.14",
        "action":   "Emergent MRI of lumbar spine; surgical consultation within 48 hours",
    },
    "fracture": {
        "title":    "Suspected Spinal Fracture",
        "urgency":  "URGENT — Imaging prior to any manual therapy",
        "guideline":"APTA Low Back Pain CPG; Goodman & Snyder Ch.14",
        "action":   "Plain radiograph or CT lumbar spine; orthopedic consultation",
    },
    "malignancy": {
        "title":    "Suspected Spinal Malignancy / Metastatic Disease",
        "urgency":  "URGENT — Medical evaluation within 24-48 hours",
        "guideline":"Henschke et al. Screen of 5 CPR; Goodman & Snyder Ch.13",
        "action":   "CBC, ESR, CRP, PSA (if male); MRI lumbar spine; oncology referral if indicated",
    },
    "infection": {
        "title":    "Suspected Spinal Infection (Discitis / Osteomyelitis)",
        "urgency":  "URGENT — Same-day medical evaluation",
        "guideline":"Goodman & Snyder Ch.14; IDSA Spinal Infection Guidelines",
        "action":   "ESR, CRP, WBC, blood cultures; MRI lumbar spine with contrast",
    },
    "vascular": {
        "title":    "Suspected Abdominal Aortic Aneurysm (AAA)",
        "urgency":  "EMERGENCY — Immediate ER if acute pain escalation",
        "guideline":"Goodman & Snyder Ch.6; ACC/AHA AAA Guidelines",
        "action":   "Abdominal ultrasound or CT-A; vascular surgery consultation",
    },
    "inflammatory": {
        "title":    "Suspected Inflammatory Spondyloarthropathy (Ankylosing Spondylitis)",
        "urgency":  "NON-URGENT — Rheumatology referral within 2 weeks",
        "guideline":"ASAS Classification Criteria; Goodman & Snyder Ch.27",
        "action":   "HLA-B27, ESR, CRP; pelvic X-ray; MRI SI joints; rheumatology referral",
    },
    "pathological_fracture": {
        "title":    "Suspected Pathological Fracture (Malignancy + Fracture co-present)",
        "urgency":  "EMERGENCY — Same-day oncology + orthopedic evaluation",
        "guideline":"Goodman & Snyder Ch.13-14; APTA Cancer Rehabilitation CPG",
        "action":   "Urgent MRI spine; oncology + orthopedic co-consult; no manual therapy or weight-bearing until imaging",
    },
}


def generate_referral_letter(
    alert,
    patient_id: str,
    therapist_name: str,
    clinic_name: str = "",
    session_date: date | None = None,
) -> str:
    """
    RedFlagAlert 객체 → 리퍼럴 레터 텍스트 생성.

    Args:
        alert:          RedFlagAlert 인스턴스
        patient_id:     익명 환자 ID
        therapist_name: 치료사 이름
        clinic_name:    클리닉/센터 이름 (선택)
        session_date:   세션 날짜 (없으면 오늘)
    """
    meta = _CONDITION_META.get(alert.condition, {
        "title":    alert.condition,
        "urgency":  "Medical evaluation recommended",
        "guideline":"Clinical judgment",
        "action":   "Physician evaluation",
    })

    today = (session_date or date.today()).strftime("%B %d, %Y")
    clinic_line = f"{clinic_name}\n" if clinic_name else ""
    indicators_str = "\n".join(f"  • {label}" for label in alert.matched_indicators)
    trigger_line = (
        f"\nPrimary trigger: {alert.trigger_label}\n"
        if alert.trigger_label else ""
    )

    letter = f"""
================================================================================
  PHYSICAL THERAPY — PHYSICIAN REFERRAL LETTER
================================================================================
  Date:      {today}
  From:      {therapist_name}
{clinic_line}  Patient:   {patient_id} (anonymous ID — PHI withheld per HIPAA)
  Re:        Clinical Red Flag Alert — {meta['title']}
================================================================================

Dear Physician,

I am writing to refer the above patient for urgent medical evaluation following
identification of clinical red flag indicators during physical therapy assessment.

  Alert Level:         {alert.alarm_level}
  Suspected Condition: {meta['title']}
  Urgency:             {meta['urgency']}

OBSERVED CLINICAL INDICATORS:
{indicators_str}{trigger_line}
  Risk Score: {alert.score:.2f} / 1.00

CLINICAL BASIS:
  {meta['guideline']}

RECOMMENDED EVALUATION:
  {meta['action']}

IMPORTANT:
  Physical therapy treatment has been suspended pending medical clearance.
  This patient should not receive spinal manipulation or progressive loading
  exercises until the above conditions have been ruled out.

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  This referral was generated by Sage Pontus PT Red Flag Screening System,
  based on the Goodman & Snyder Differential Diagnosis framework.

  Respectfully,
  {therapist_name}
  Physical Therapist
  {clinic_name}
================================================================================
""".strip()

    return letter


def generate_multi_referral_letter(
    conditions: list[dict],
    patient_id: str,
    therapist_name: str,
    clinic_name: str = "",
    session_date: "date | None" = None,
) -> str:
    """
    멀티 컨디션 리퍼럴 레터 — conditions 리스트 (scorer 반환값) 기반.

    Args:
        conditions: detect_red_flags()["conditions"] 리스트
        patient_id, therapist_name, clinic_name, session_date: 기존과 동일
    """
    from datetime import date as _date
    today = (session_date or _date.today()).strftime("%B %d, %Y")
    clinic_line = f"{clinic_name}\n" if clinic_name else ""

    # NONE 제외하고 RED 우선 정렬
    active = [c for c in conditions if c.get("alarm", "NONE") != "NONE"]
    if not active:
        return ""

    # 리퍼럴 대상 섹션 빌드
    condition_sections = []
    for c in active:
        cond_id = c["condition"]
        meta = _CONDITION_META.get(cond_id, {
            "title":    cond_id.replace("_", " ").title(),
            "urgency":  "Medical evaluation recommended",
            "guideline":"Clinical judgment",
            "action":   "Physician evaluation",
        })
        indicators_str = _format_indicators_grouped(
            c.get("matched", []), c.get("screening_breakdown", {})
        )
        trigger_line = f"\n  Primary trigger: {c['trigger']}\n" if c.get("trigger") else ""
        section = (
            f"  [{c['alarm']}] {meta['title']}\n"
            f"  Urgency: {meta['urgency']}\n"
            f"  Indicators:\n{indicators_str}{trigger_line}"
            f"  Recommended: {meta['action']}\n"
            f"  Guideline: {meta['guideline']}"
        )
        condition_sections.append(section)

    conditions_body = "\n\n".join(condition_sections)
    top_alarm = active[0]["alarm"]

    letter = f"""
================================================================================
PHYSICAL THERAPY — PHYSICIAN REFERRAL LETTER
================================================================================
Date:      {today}
From:      {therapist_name}
{clinic_line}Patient:   {patient_id} (anonymous ID — PHI withheld per HIPAA)
Re:        Clinical Red Flag Alert — {len(active)} Condition(s) Identified
================================================================================

Dear Physician,

I am writing to refer the above patient for urgent medical evaluation following
identification of clinical red flag indicators during physical therapy assessment.

OVERALL ALERT LEVEL: {top_alarm}

IDENTIFIED CONDITIONS:
--------------------------------------------------------------------------------
{conditions_body}
--------------------------------------------------------------------------------

IMPORTANT: Physical therapy treatment has been suspended pending medical
clearance. This patient should not receive spinal manipulation or progressive
loading exercises until the above conditions have been ruled out.

This referral was generated by Sage Pontus PT Red Flag Screening System,
based on the Goodman & Snyder Differential Diagnosis framework.

Respectfully,
{therapist_name}
Physical Therapist
{clinic_name}
================================================================================
""".strip()

    return letter


def generate_referral_letter_ai(
    alert,
    patient_id: str,
    therapist_name: str,
    clinic_name: str = "",
    few_shot_examples: list[str] | None = None,
) -> str:
    """AI 버전 리퍼럴 레터 — Gemini 2.5 Flash + few-shot."""
    from questionnaire.prompts.gemini_client import chat_completion_generate

    meta = _CONDITION_META.get(alert.condition, {
        "title":    alert.condition.replace("_", " ").title(),
        "urgency":  "Medical evaluation recommended",
        "guideline":"Clinical judgment",
        "action":   "Physician evaluation",
    })

    raw_indicators = list(alert.matched_indicators)
    breakdown      = getattr(alert, "screening_breakdown", {}) or {}
    indicators_str = _format_indicators_grouped(raw_indicators, breakdown)

    few_shot_block = ""
    if few_shot_examples:
        joined = "\n\n---\n\n".join(few_shot_examples[:3])
        few_shot_block = (
            "\n\nEXAMPLE LETTERS (previously approved by this therapist — match this style):\n\n"
            + joined + "\n\n---\n\n"
        )

    system = (
        "You are an expert physical therapy clinical documentation specialist. "
        "Write a professional, medically precise physician referral letter. "
        "Output plain text only — do NOT use markdown (**, *, #, ```). "
        "Use ALL CAPS for section headers and plain bullet points (•) for lists."
    )

    user_prompt = (
        f"Write a Physician Referral Letter for the following red flag alert.{few_shot_block}\n"
        f"THERAPIST: {therapist_name}, PT\n"
        f"CLINIC: {clinic_name or 'N/A'}\n"
        f"PATIENT ID: {patient_id} (anonymous — no PHI)\n"
        f"SESSION DATE: {alert.timeline.session_date}\n\n"
        f"RED FLAG ALERT:\n"
        f"  Alarm Level:          {alert.alarm_level}\n"
        f"  Suspected Condition:  {meta['title']}\n"
        f"  Urgency:              {meta['urgency']}\n"
        f"  Risk Score:           {alert.score:.2f} / 1.00\n\n"
        f"OBSERVED INDICATORS:\n{indicators_str}\n\n"
        f"RECOMMENDED EVALUATION:\n  {meta['action']}\n\n"
        f"CLINICAL GUIDELINE:\n  {meta['guideline']}\n\n"
        "IMPORTANT: Use only the anonymous patient ID above. "
        "Output a complete referral letter ready to send. No markdown formatting."
    )

    raw = chat_completion_generate(
        model_id="gemini-2.5-flash",
        user=user_prompt,
        generation={"max_tokens": 1500, "temperature": 0.3},
        system=system,
    )
    return _strip_md(raw)
