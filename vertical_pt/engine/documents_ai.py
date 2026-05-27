"""AI 버전 문서 생성 — Gemini 2.5 Flash, few-shot from chosen history."""

from __future__ import annotations

import logging
from typing import Any

from questionnaire.prompts.gemini_client import chat_completion_generate

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an expert physical therapy documentation specialist. "
    "Generate professional, legally defensible PT documents based on the clinical data. "
    "If example documents are provided, match their style and tone exactly. "
    "Use the patient's anonymous ID throughout — never invent or include PHI."
)

_DOC_LABELS = {
    "medical_necessity":   "Medical Necessity Letter",
    "legal_defense":       "Standard of Care Defense Documentation",
    "clinical_chronology": "Clinical Session Chronology",
    "insurance_appeal":    "Insurance Appeal Letter",
    "functional_report":   "Functional Limitation Report",
}


def generate_document_ai(
    doc_type: str,
    sessions: list,
    therapist_name: str,
    patient_id: str,
    clinic_name: str = "",
    clinical_context: dict | None = None,
    few_shot_examples: list[str] | None = None,
) -> str:
    ctx = clinical_context or {}

    session_lines = []
    for i, s in enumerate(sessions, 1):
        line = (
            f"  Session {i}: {s.session_date} | Alarm: {s.alarm_level} | "
            f"Risk: {s.critical_score*100:.0f}%"
        )
        if s.triggered_condition:
            line += f" | {s.triggered_condition.replace('_', ' ').title()}"
        session_lines.append(line)

    few_shot_block = ""
    if few_shot_examples:
        joined = "\n\n---\n\n".join(few_shot_examples[:3])
        few_shot_block = (
            "\n\nEXAMPLE DOCUMENTS (previously approved by this therapist — match this style):\n\n"
            + joined
            + "\n\n---\n\n"
        )

    def _list(key: str) -> str:
        v = ctx.get(key) or []
        return ", ".join(v) if v else "N/A"

    user_prompt = (
        f"Generate a {_DOC_LABELS.get(doc_type, doc_type)} for the following patient."
        f"{few_shot_block}\n"
        f"THERAPIST: {therapist_name}, PT\n"
        f"CLINIC: {clinic_name or 'N/A'}\n"
        f"PATIENT ID: {patient_id} (anonymous — no PHI)\n\n"
        f"CLINICAL CONTEXT:\n"
        f"  Primary Diagnosis: {ctx.get('primary_diagnosis') or 'Musculoskeletal dysfunction'}\n"
        f"  Chief Complaint: {ctx.get('chief_complaint') or 'Not specified'}\n"
        f"  Age/Sex: {ctx.get('patient_age', 'N/A')} / {ctx.get('patient_sex', 'N/A')}\n"
        f"  VAS Score: {ctx.get('vas_score') or 'N/A'}\n"
        f"  MMT Findings: {_list('mmt_findings')}\n"
        f"  ROM Findings: {_list('rom_findings')}\n"
        f"  Neurological: {_list('neurological_findings')}\n"
        f"  Functional Limitations: {_list('functional_limitations')}\n"
        f"  Precautions: {_list('precautions')}\n"
        f"  STG: {_list('goals_stg')}\n"
        f"  LTG: {_list('goals_ltg')}\n\n"
        f"SESSION HISTORY ({len(sessions)} sessions):\n"
        + "\n".join(session_lines)
        + "\n\nIMPORTANT: Use only the anonymous patient ID above. "
        "Format as a complete, professional clinical document ready to send."
    )

    return chat_completion_generate(
        model_id="gemini-2.5-flash",
        user=user_prompt,
        generation={"max_tokens": 3000, "temperature": 0.3},
        system=_SYSTEM,
    )
