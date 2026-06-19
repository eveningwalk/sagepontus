"""
SOAP Clinical Context Extractor
PT SOAP 텍스트 → 구조화 임상 컨텍스트 JSON 분류

원칙: temperature=0, 입력 내용만 분류 — 추론/추가 없음
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_EMPTY: dict[str, Any] = {
    "patient_age":            None,
    "patient_sex":            None,
    "primary_diagnosis":      None,
    "comorbidities":          [],
    "chief_complaint":        None,
    "onset_duration":         None,
    "vas_score":              None,
    "mmt_findings":           [],
    "rom_findings":           [],
    "neurological_findings":  [],
    "special_tests":          [],
    "functional_limitations": [],
    "red_flag_findings":      [],
    "treatment_performed":    [],
    "medications":            [],
    "precautions":            [],
    "goals_stg":              [],
    "goals_ltg":              [],
    "other_findings":         [],
}

_SYSTEM = (
    "You are a clinical data classifier for physical therapy SOAP notes. "
    "Extract ONLY information explicitly present in the note. "
    "Do NOT infer, add clinical knowledge, or enrich beyond what is written. "
    "Return null for absent string fields, [] for absent list fields."
)

_PROMPT_PREFIX = """\
Classify the physical therapy SOAP note below into structured JSON.
Copy values verbatim or with minimal reformatting. Do not add information not in the text.

Rules:
- mmt_findings: include muscle/movement name + grade (e.g. "Lt trunk extension F+")
- rom_findings: include movement + value (e.g. "Shoulder flexion 120")
- special_tests: "test name: result" format (e.g. "SLR Lt: positive at 45 degrees")
- vas_score: copy as written (e.g. "6/10", "VAS 7")
- red_flag_findings: only objective signs that constitute red flags
- goals_stg: Short-Term Goals — copy verbatim as a list (e.g. ["Reduce pain to 3/10", "Improve SLR to 60 deg"])
- goals_ltg: Long-Term Goals — copy verbatim as a list (e.g. ["Return to work", "Independent ADLs without pain"])
- other_findings: ONLY content that does NOT fit any field above (e.g. psychosocial factors, FABQ scores, fear-avoidance beliefs, yellow flag screening results, occupation/work history). Fill other fields first; put leftovers here.
- If a field has no data in the note, return null or []

SOAP Note:
"""

_PROMPT_SUFFIX = """

Return ONLY valid JSON (no markdown fences, no extra text):
{"patient_age": null, "patient_sex": null, "primary_diagnosis": null, "comorbidities": [], "chief_complaint": null, "onset_duration": null, "vas_score": null, "mmt_findings": [], "rom_findings": [], "neurological_findings": [], "special_tests": [], "functional_limitations": [], "red_flag_findings": [], "treatment_performed": [], "medications": [], "precautions": [], "goals_stg": [], "goals_ltg": [], "other_findings": []}"""


def extract_clinical_context(soap_text: str) -> dict[str, Any]:
    """SOAP 텍스트 → 구조화 임상 컨텍스트. temperature=0, 입력 분류만."""
    if not soap_text or not soap_text.strip():
        return dict(_EMPTY)

    try:
        from questionnaire.prompts.service import _chat_generate

        prompt = _PROMPT_PREFIX + soap_text.strip() + _PROMPT_SUFFIX
        # gemini-flash-lite: thinking 없음 → 분류 작업에 최적 (2.5-flash는 thinking이 max_tokens 소모)
        # 주의: "models/" 접두어를 쓰면 gemini_client가 HF ID로 인식해 기본 모델로 폴백됨
        raw = _chat_generate()(
            "gemini-flash-lite-latest",
            prompt,
            {"max_tokens": 2048, "temperature": 0},
            system=_SYSTEM,
        )

        raw = raw.strip()
        if not raw:
            logger.warning("SOAP extractor: 빈 응답")
            return dict(_EMPTY)

        # markdown fence 제거 (```json ... ``` 또는 ``` ... ```)
        fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", raw, re.DOTALL)
        if fence_match:
            raw = fence_match.group(1).strip()
        # fence 제거 후에도 {가 있는 위치부터 슬라이싱 (앞에 텍스트가 붙는 경우 방어)
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}") + 1
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start:brace_end]

        data   = json.loads(raw)
        result = dict(_EMPTY)
        for k in _EMPTY:
            v = data.get(k)
            if v is not None and v != [] and v != "":
                result[k] = v
        return result

    except Exception as e:
        logger.warning("SOAP extractor 실패: %s", e)
        return dict(_EMPTY)
