"""
PT CRA (Context Retention Algorithm) — 환자 시계열 컨텍스트 빌더

기존 questionnaire/prompts/cra_engine.py를 PT Red Flag 도메인에 특화.
PatientTimeline DB에서 이전 세션 데이터를 로드하여 시계열 추세를 분석.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_patient_context(patient_id: str, therapist_id: int, limit: int = 12) -> dict[str, Any]:
    """
    환자의 최근 세션 이력 로드 → 시계열 컨텍스트 반환.

    Args:
        patient_id:    익명 환자 ID
        therapist_id:  치료사 User ID
        limit:         최대 세션 수 (기본 12 = 약 3개월)

    Returns:
        {
            "session_count":    int,
            "trend":            "escalating" | "stable" | "improving" | "new",
            "peak_score":       float,
            "recent_scores":    [float, ...],
            "prev_alarms":      ["RED", "YELLOW", ...],
            "prev_conditions":  ["fracture", ...],
            "summary":          str,
        }
    """
    try:
        from vertical_pt.models import PatientTimeline

        timelines = (
            PatientTimeline.objects
            .filter(therapist_id=therapist_id, patient_id=patient_id)
            .order_by("-session_date")[:limit]
        )
        sessions = list(reversed(list(timelines)))  # 오래된 → 최신 순

        if not sessions:
            return _empty_context()

        scores     = [s.critical_score for s in sessions]
        alarms     = [s.alarm_level for s in sessions]
        conditions = [s.triggered_condition for s in sessions if s.triggered_condition]

        trend = _compute_trend(scores)
        peak  = max(scores)

        return {
            "session_count":   len(sessions),
            "trend":           trend,
            "peak_score":      round(peak, 3),
            "recent_scores":   [round(s, 3) for s in scores[-4:]],
            "prev_alarms":     alarms,
            "prev_conditions": list(set(conditions)),
            "summary":         _build_summary(trend, peak, alarms, conditions),
        }
    except Exception as e:
        logger.warning("build_patient_context 실패: %s", e)
        return _empty_context()


def _empty_context() -> dict[str, Any]:
    return {
        "session_count":   0,
        "trend":           "new",
        "peak_score":      0.0,
        "recent_scores":   [],
        "prev_alarms":     [],
        "prev_conditions": [],
        "summary":         "첫 세션 — 이전 기록 없음.",
    }


def _compute_trend(scores: list[float]) -> str:
    if len(scores) < 2:
        return "new"
    recent = scores[-3:] if len(scores) >= 3 else scores
    delta = recent[-1] - recent[0]
    if delta > 0.15:
        return "escalating"
    if delta < -0.15:
        return "improving"
    return "stable"


def _build_summary(trend: str, peak: float, alarms: list[str], conditions: list[str]) -> str:
    red_count    = alarms.count("RED")
    yellow_count = alarms.count("YELLOW")
    cond_str     = ", ".join(conditions) if conditions else "없음"

    lines = [f"누적 세션: {len(alarms)}회 | 추세: {trend} | 최고 점수: {peak:.2f}"]
    if red_count:
        lines.append(f"⚠️  이전 RED 알람: {red_count}회 (조건: {cond_str})")
    elif yellow_count:
        lines.append(f"주의 세션: {yellow_count}회 (조건: {cond_str})")
    if trend == "escalating":
        lines.append("📈 점수 상승 추세 — 이번 세션 면밀 검토 필요")
    return " | ".join(lines)
