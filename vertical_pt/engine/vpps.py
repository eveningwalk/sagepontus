"""
VPPS (Vertical Prompt Propagation System)
비정형 SOAP 텍스트 → 증상 팩트 JSON 추출

핵심 원칙:
- 할루시네이션 배제: KB에 정의된 증상만 추출 (임의 진단 금지)
- 부정 표현 처리: "no fever", "denies weight loss" → 양성 매칭 제외
- 매칭 전략: substring → regex 순으로 실행, 중복 제거
- AI 2차 패스: 규칙 기반 미탐지 시 선택적 AI 보완
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_KB_PATH = Path(__file__).resolve().parents[1] / "prompts" / "kb_red_flag.json"
_FALLBACK_KB_PATH = Path(__file__).resolve().parents[2] / "questionnaire/prompts/kb/pt_red_flag.json"

# 부정 표현 — "no improvement" 같이 자체가 Red Flag인 표현은 제외
_NEGATION_RE = re.compile(
    r"(?:no|without|denies?|absence of|negative for|ruled out|"
    r"not experiencing|not having|no history of|no evidence of)"
    r"\s+"
    r"(?!improvement|improving|relief|response|change|comfortable)"
    r"(?:\w+\s+){0,3}",
    re.IGNORECASE,
)


def _load_kb() -> dict:
    path = _KB_PATH if _KB_PATH.exists() else _FALLBACK_KB_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _strip_negations(text: str) -> str:
    return _NEGATION_RE.sub(lambda m: " " * len(m.group(0)), text)


def _make_hit(kb_id: str, entry: dict) -> dict:
    return {
        "kb_id":         kb_id,
        "label":         entry["label"],
        "weight":        entry["depth"],
        "alarm_level":   entry.get("alarm_level", "YELLOW"),
        "condition_ref": entry.get("condition_ref", ""),
        "category":      entry.get("category", ""),
    }


def _rule_match(text: str, kb: dict) -> list[dict]:
    """KB synonym 매칭 — 긴 패턴 우선, 부정어 처리 후."""
    clean = _strip_negations(text).lower()
    hits: list[dict] = []
    seen: set[str] = set()

    entries: list[tuple[str, str, dict]] = []
    for kb_id, entry in kb.items():
        label = entry["label"]
        label_en = label.split("(")[0].strip()
        raw_syns = [label] + ([label_en] if label_en != label else []) + entry.get("synonyms", [])
        for syn in raw_syns:
            entries.append((syn.lower(), kb_id, entry))
    entries.sort(key=lambda x: len(x[0]), reverse=True)

    for syn_lower, kb_id, entry in entries:
        if kb_id in seen:
            continue
        if syn_lower in clean:
            seen.add(kb_id)
            hits.append(_make_hit(kb_id, entry))

    return hits


def _regex_match(text: str, kb: dict, seen: set[str]) -> list[dict]:
    """
    KB patterns 필드 기반 정규식 매칭 — substring으로 못 잡는 구조적 표현 포착.
    예: "Pain 8/10 at rest", "15lbs weight loss", "no mechanism of injury"
    """
    # 부정어 처리된 텍스트 사용
    clean = _strip_negations(text)
    hits: list[dict] = []

    for kb_id, entry in kb.items():
        if kb_id in seen:
            continue
        for raw_pattern in entry.get("patterns", []):
            try:
                if re.search(raw_pattern, clean, re.IGNORECASE | re.DOTALL):
                    seen.add(kb_id)
                    hits.append(_make_hit(kb_id, entry))
                    break
            except re.error as e:
                logger.warning("VPPS regex error kb_id=%s pattern=%r: %s", kb_id, raw_pattern, e)

    return hits


def extract_symptoms(soap_text: str, use_ai: bool = False,
                     pre_confirmed_ids: list[str] | None = None) -> dict[str, Any]:
    """
    SOAP 텍스트에서 Red Flag 증상 팩트 추출.

    Returns:
        {
            "hits": [...],          # 매칭된 증상 목록
            "hit_count": int,
            "has_red_indicator": bool,
            "source": "rule" | "ai",
        }
    """
    kb = _load_kb()

    # 1차: substring 매칭
    hits = _rule_match(soap_text, kb)
    seen = {h["kb_id"] for h in hits}

    # 2차: regex 매칭 (substring에서 놓친 것만)
    regex_hits = _regex_match(soap_text, kb, seen)
    hits = sorted(hits + regex_hits, key=lambda h: h["weight"], reverse=True)

    # 2.5차: UI에서 직접 확인된 항목 주입 (체크박스 오버라이드)
    if pre_confirmed_ids:
        seen = {h["kb_id"] for h in hits}
        for rf_id in pre_confirmed_ids:
            if rf_id in kb and rf_id not in seen:
                hits.append(_make_hit(rf_id, kb[rf_id]))
                seen.add(rf_id)
        hits = sorted(hits, key=lambda h: h["weight"], reverse=True)

    # 3차: AI 패스 (옵션, 여전히 아무것도 안 잡혔을 때만)
    if use_ai and not hits:
        hits = _ai_extract(soap_text, kb) or hits

    has_red = any(h["alarm_level"] == "RED" for h in hits)

    return {
        "hits":              hits,
        "hit_count":         len(hits),
        "has_red_indicator": has_red,
        "source":            "rule",
    }


def _ai_extract(soap_text: str, kb: dict) -> list[dict] | None:
    """AI 2차 패스 — 규칙 기반에서 놓친 증상 보완 (선택적)."""
    try:
        from questionnaire.prompts.service import _chat_generate

        slim_kb = {
            kb_id: [entry["label"]] + entry.get("synonyms", [])[:5]
            for kb_id, entry in kb.items()
        }
        prompt = (
            "You are a clinical screening assistant for physical therapists.\n"
            "From the SOAP note below, extract ONLY factual symptom observations "
            "that match entries in the provided KB. Do NOT infer or diagnose.\n\n"
            f"KB (id → [label, synonyms...]):\n{json.dumps(slim_kb, ensure_ascii=False)}\n\n"
            f"SOAP Note:\n{soap_text}\n\n"
            "Return JSON: {\"matched_ids\": [\"RF_001\", ...]}"
        )
        raw = _chat_generate()("gemini-2.5-flash", prompt, {"max_tokens": 512, "temperature": 0.1})
        data = json.loads(raw)
        matched_ids = data.get("matched_ids", [])
        return [
            _make_hit(kb_id, kb[kb_id])
            for kb_id in matched_ids if kb_id in kb
        ]
    except Exception as e:
        logger.warning("VPPS AI extract 실패: %s", e)
        return None
