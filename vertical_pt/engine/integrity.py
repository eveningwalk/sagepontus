"""
Session Integrity — SHA-256 tamper-evident sealing for PatientTimeline records.

봉인 대상 필드:
  patient_id, session_date, soap_text, alarm_level, triggered_condition,
  clinical_context, matched_indicators (from alert), created_at

해시는 세션 저장 완료(created_at 확정) 후 계산하여 integrity_hash 필드에 저장.
검증 시 동일 로직으로 재계산 후 비교.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vertical_pt.models import PatientTimeline

_ALGORITHM = "sha256"


def _canonical(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(value) if value is not None else ""


def compute_hash(timeline: "PatientTimeline", matched_indicators: list | None = None) -> str:
    """PatientTimeline 레코드의 SHA-256 무결성 해시를 반환한다."""
    components = [
        timeline.patient_id,
        str(timeline.session_date),
        timeline.soap_text,
        timeline.alarm_level,
        timeline.triggered_condition or "",
        _canonical(timeline.clinical_context or {}),
        _canonical(matched_indicators or []),
        timeline.created_at.isoformat(),
    ]
    raw = "\n".join(components)
    return hashlib.new(_ALGORITHM, raw.encode("utf-8")).hexdigest()


def seal(timeline: "PatientTimeline") -> str:
    """해시를 계산하고 timeline.integrity_hash에 저장 후 반환."""
    alert = timeline.alerts.order_by("-created_at").first()
    matched = alert.matched_indicators if alert else []
    h = compute_hash(timeline, matched)
    timeline.integrity_hash = h
    timeline.save(update_fields=["integrity_hash"])
    return h


def verify(timeline: "PatientTimeline") -> dict:
    """저장된 해시와 현재 레코드 해시를 비교. {ok, stored, computed, algorithm} 반환."""
    if not timeline.integrity_hash:
        return {"ok": False, "reason": "no_hash", "algorithm": _ALGORITHM}

    alert = timeline.alerts.order_by("-created_at").first()
    matched = alert.matched_indicators if alert else []
    computed = compute_hash(timeline, matched)
    ok = computed == timeline.integrity_hash

    return {
        "ok":       ok,
        "stored":   timeline.integrity_hash[:16] + "…",
        "computed": computed[:16] + "…",
        "algorithm": _ALGORITHM,
    }
