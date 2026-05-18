"""
Red Flag Scorer
VPPS 추출 결과 + 프로토콜 → 알람 레벨 + 조건 결정 (멀티 컨디션)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "data" / "red_flag_protocols"
_ALARM_PRIORITY = {"RED": 2, "YELLOW": 1, "NONE": 0}

# Pathological Fracture 복합 규칙: Malignancy + Fracture 동시 활성
_PATHOLOGICAL_FRACTURE = {
    "condition":  "pathological_fracture",
    "alarm":      "RED",
    "score":      1.0,
    "matched":    [],
    "trigger":    "Pathological Fracture — Cancer + Fracture indicators co-present",
}


def _load_index() -> list[dict]:
    path = _PROTOCOLS_DIR / "index.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["protocols"]


def _load_protocol(filename: str) -> dict:
    path = _PROTOCOLS_DIR / filename
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _score_condition(protocol: dict, hits: list[dict]) -> dict[str, Any]:
    """단일 프로토콜에 대한 알람 점수 계산."""
    condition_ref = protocol.get("protocol_id", "").replace("rfp_", "")
    condition_hits = [h for h in hits if h["condition_ref"] == condition_ref]

    if not condition_hits:
        return {"alarm": "NONE", "score": 0.0, "matched": [], "trigger": ""}

    logic = protocol.get("decision_logic", "WEIGHTED_SUM")

    # ── ANY_CARDINAL ──────────────────────────────────────────────────────
    if logic == "ANY_CARDINAL":
        for hit in condition_hits:
            if hit["alarm_level"] == "RED":
                return {
                    "alarm":   "RED",
                    "score":   1.0,
                    "matched": [h["label"] for h in condition_hits],
                    "trigger": hit["label"],
                }
        if len(condition_hits) >= 2:
            return {"alarm": "RED", "score": 0.9, "matched": [h["label"] for h in condition_hits], "trigger": ""}
        return {"alarm": "YELLOW", "score": 0.5, "matched": [h["label"] for h in condition_hits], "trigger": ""}

    # ── SCREEN_OF_5 ───────────────────────────────────────────────────────
    if logic == "SCREEN_OF_5":
        threshold = protocol.get("threshold", {})
        cancer_hit = next((h for h in condition_hits if h["kb_id"] == "RF_009"), None)
        if cancer_hit:
            return {
                "alarm":   "RED",
                "score":   1.0,
                "matched": [h["label"] for h in condition_hits],
                "trigger": cancer_hit["label"],
            }
        count = len(condition_hits)
        score = round(count / 5.0, 3)
        if count >= threshold.get("red", 3):
            return {"alarm": "RED",    "score": score, "matched": [h["label"] for h in condition_hits], "trigger": ""}
        if count >= threshold.get("yellow", 2):
            return {"alarm": "YELLOW", "score": score, "matched": [h["label"] for h in condition_hits], "trigger": ""}
        return {"alarm": "NONE", "score": score, "matched": [h["label"] for h in condition_hits], "trigger": ""}

    # ── WEIGHTED_SUM (기본) ───────────────────────────────────────────────
    threshold = protocol.get("threshold", {"red": 0.70, "yellow": 0.45})

    for hit in condition_hits:
        if hit["alarm_level"] == "RED" and hit["weight"] >= 0.95:
            return {
                "alarm":   "RED",
                "score":   1.0,
                "matched": [h["label"] for h in condition_hits],
                "trigger": hit["label"],
            }

    score = min(sum(h["weight"] for h in condition_hits), 1.0)

    if condition_ref == "fracture":
        trauma_hits = [h for h in condition_hits if "trauma" in h.get("category", "")]
        if trauma_hits:
            score = min(score * 1.3, 1.0)

    has_red_indicator  = any(h["alarm_level"] == "RED" for h in condition_hits)
    protocol_max_alarm = protocol.get("alarm_level", "RED")

    raw = "RED" if score >= threshold["red"] else "YELLOW" if score >= threshold["yellow"] else "NONE"
    if raw == "RED" and (protocol_max_alarm == "YELLOW" or not has_red_indicator):
        raw = "YELLOW"

    return {
        "alarm":   raw,
        "score":   round(score, 3),
        "matched": [h["label"] for h in condition_hits],
        "trigger": "",
    }


def detect_red_flags(vpps_result: dict) -> dict[str, Any]:
    """
    VPPS 결과 → 전체 프로토콜 스캔 → 전체 활성 조건 + 최고 알람 반환.

    Returns:
        {
            "alarm":      "RED" | "YELLOW" | "NONE",
            "condition":  str | None,    # 최고 위험 조건 (하위 호환)
            "score":      float,
            "matched":    [str, ...],
            "trigger":    str,
            "conditions": [              # 활성 조건 전체 (NONE 제외)
                {
                    "condition": str,
                    "alarm":     str,
                    "score":     float,
                    "matched":   [str, ...],
                    "trigger":   str,
                },
                ...
            ],
            "details":    {condition: {...}, ...},
        }
    """
    hits = vpps_result.get("hits", [])
    index = _load_index()

    final_alarm     = "NONE"
    final_condition = None
    final_score     = 0.0
    final_matched   = []
    final_trigger   = ""
    details: dict[str, Any] = {}
    active_conditions: list[dict] = []

    for proto_meta in index:
        protocol = _load_protocol(proto_meta["file"])
        if not protocol:
            continue
        result = _score_condition(protocol, hits)
        cond = proto_meta["id"].replace("rfp_", "")
        details[cond] = result

        if result["alarm"] != "NONE":
            active_conditions.append({"condition": cond, **result})

        if _ALARM_PRIORITY.get(result["alarm"], 0) > _ALARM_PRIORITY.get(final_alarm, 0):
            final_alarm     = result["alarm"]
            final_condition = cond
            final_score     = result["score"]
            final_matched   = result["matched"]
            final_trigger   = result.get("trigger", "")

    # Pathological Fracture 복합 규칙
    active_names = {c["condition"] for c in active_conditions}
    if "malignancy" in active_names and "fracture" in active_names:
        all_matched = list({
            m
            for c in active_conditions
            if c["condition"] in ("malignancy", "fracture")
            for m in c["matched"]
        })
        pf = {**_PATHOLOGICAL_FRACTURE, "matched": all_matched}
        active_conditions.append(pf)
        final_alarm     = "RED"
        final_condition = "pathological_fracture"
        final_score     = 1.0
        final_trigger   = pf["trigger"]
        final_matched   = all_matched
        details["pathological_fracture"] = pf

    # 심각도 순 정렬
    active_conditions.sort(
        key=lambda c: (_ALARM_PRIORITY.get(c["alarm"], 0), c["score"]),
        reverse=True,
    )

    return {
        "alarm":      final_alarm,
        "condition":  final_condition,
        "score":      final_score,
        "matched":    final_matched,
        "trigger":    final_trigger,
        "conditions": active_conditions,
        "details":    details,
    }


def score_soap(soap_text: str, use_ai: bool = False) -> dict[str, Any]:
    """SOAP 텍스트 입력 → 알람 결과 반환 (VPPS + Scorer 통합 진입점)."""
    from .vpps import extract_symptoms
    vpps = extract_symptoms(soap_text, use_ai=use_ai)
    result = detect_red_flags(vpps)
    result["vpps"] = vpps
    return result
