#!/usr/bin/env python3
"""
Red Flag Algorithm Validation — Phase 2
가상 환자 시나리오로 탐지 알고리즘 민감도/특이도 검증

Usage:
    python scripts/red_flag/validate_scenarios.py
    python scripts/red_flag/validate_scenarios.py --verbose
    python scripts/red_flag/validate_scenarios.py --condition cauda_equina
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 경로 설정 ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
KB_PATH = ROOT / "questionnaire/prompts/kb/pt_red_flag.json"
PROTOCOLS_DIR = ROOT / "data/red_flag_protocols"

# ── 터미널 컬러 ───────────────────────────────────────────────────────────────
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ══════════════════════════════════════════════════════════════════════════════
# 가상 환자 시나리오 (25건)
# 형식: soap_text, expected_alarm, expected_condition, description
# ══════════════════════════════════════════════════════════════════════════════
SCENARIOS = [

    # ── RED: Cauda Equina ────────────────────────────────────────────────────
    {
        "id": "CES_01",
        "description": "CES — 방광 저류 + 안장 감각 소실",
        "soap_text": (
            "67F, LBP 3/7. Pt reports inability to urinate since yesterday morning. "
            "Also reports saddle area numbness and perianal numbness. "
            "Bilateral leg weakness noted on exam. Denies trauma."
        ),
        "expected_alarm": "RED",
        "expected_condition": "cauda_equina",
    },
    {
        "id": "CES_02",
        "description": "CES — 대변 실금 + 양측 하지 무력",
        "soap_text": (
            "52M. Acute onset bowel incontinence today. "
            "Bilateral lower extremity weakness 3/5. "
            "Perineal numbness confirmed. Previously treated for L4-L5 HNP."
        ),
        "expected_alarm": "RED",
        "expected_condition": "cauda_equina",
    },
    {
        "id": "CES_03",
        "description": "CES — 소변 실금 단독 (조기 징후)",
        "soap_text": (
            "44F. Presented with sudden urinary incontinence this AM. "
            "Reports genital numbness started 2 days ago. "
            "Worsening numbness in both legs."
        ),
        "expected_alarm": "RED",
        "expected_condition": "cauda_equina",
    },

    # ── RED: Fracture ────────────────────────────────────────────────────────
    {
        "id": "FX_01",
        "description": "골절 — 고령 낙상 + 골다공증",
        "soap_text": (
            "78F. Fall down stairs 2 days ago. PMH: osteoporosis, on calcium supplement. "
            "Point tenderness L2-L3 on percussion. Pain worsened by weight bearing. "
            "Unable to ambulate independently."
        ),
        "expected_alarm": "RED",
        "expected_condition": "fracture",
    },
    {
        "id": "FX_02",
        "description": "골절 — 장기 스테로이드 + 교통사고",
        "soap_text": (
            "61M. MVA 3 days ago, rear-end collision. "
            "PMH: rheumatoid arthritis, on prednisone for 2 years. "
            "Severe point tenderness T12. Pain 9/10 with any movement."
        ),
        "expected_alarm": "RED",
        "expected_condition": "fracture",
    },
    {
        "id": "FX_03",
        "description": "골절 — 폐경 후 여성 + 미끄러짐",
        "soap_text": (
            "65F postmenopausal. Slipped on wet floor yesterday. "
            "Bone density low per recent DEXA scan. "
            "Percussion tenderness at L1. Cannot tolerate weight bearing."
        ),
        "expected_alarm": "RED",
        "expected_condition": "fracture",
    },

    # ── RED: Malignancy ──────────────────────────────────────────────────────
    {
        "id": "CA_01",
        "description": "악성 종양 — 암 기왕력 단독 (즉시 RED)",
        "soap_text": (
            "58M. Low back pain x 6 weeks, not improving. "
            "PMH: prostate cancer treated 3 years ago, cancer survivor. "
            "Night pain, wakes from sleep. No trauma."
        ),
        "expected_alarm": "RED",
        "expected_condition": "malignancy",
    },
    {
        "id": "CA_02",
        "description": "악성 종양 — Screen of 5 중 4개",
        "soap_text": (
            "67F. LBP 8 weeks, no improvement with PT or rest. "
            "Unexplained weight loss 12 lbs over 3 months. "
            "Night pain, cannot find comfortable position. Age 67, no prior cancer."
        ),
        "expected_alarm": "RED",
        "expected_condition": "malignancy",
    },
    {
        "id": "CA_03",
        "description": "악성 종양 — 유방암 기왕력 + 야간통",
        "soap_text": (
            "54F. Breast cancer surgery 5 years ago, currently in remission. "
            "New onset thoracic and lumbar pain x 3 weeks. "
            "Pain at night, wakes patient around 3am. Fatigue and malaise."
        ),
        "expected_alarm": "RED",
        "expected_condition": "malignancy",
    },

    # ── RED: Infection ───────────────────────────────────────────────────────
    {
        "id": "INF_01",
        "description": "척추 감염 — 발열 + 요로감염 후",
        "soap_text": (
            "48M. Fever 38.5C noted at eval. Recent UTI treated with antibiotics 2 weeks ago. "
            "Constant back pain, no positional relief. Night sweats past week. "
            "Diabetes mellitus, poorly controlled."
        ),
        "expected_alarm": "RED",
        "expected_condition": "infection",
    },
    {
        "id": "INF_02",
        "description": "척추 감염 — IV drug use + 발열",
        "soap_text": (
            "35M. IV drug use history. Fever 39.1C today. "
            "Severe lumbar pain unrelenting, no position change provides relief. "
            "Recent skin infection left arm."
        ),
        "expected_alarm": "RED",
        "expected_condition": "infection",
    },

    # ── RED: Vascular ────────────────────────────────────────────────────────
    {
        "id": "AAA_01",
        "description": "AAA — 박동성 복부 종괴 + 자세 무관 통증",
        "soap_text": (
            "71M. LBP onset 1 week, gradual. HTN, smoker 30 pack-years. "
            "Patient reports pulsating sensation in abdomen around navel. "
            "Pain identical in all positions, no movement-related change."
        ),
        "expected_alarm": "RED",
        "expected_condition": "vascular",
    },
    {
        "id": "AAA_02",
        "description": "AAA — 치료 중 갑작스러운 통증 극대화",
        "soap_text": (
            "68M. During manual therapy, sudden severe tearing pain in abdomen. "
            "Previously known hypertension, atherosclerosis. "
            "Patient becomes diaphoretic and pale."
        ),
        "expected_alarm": "RED",
        "expected_condition": "vascular",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # YELLOW 케이스 (8건)
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "YEL_01",
        "description": "YELLOW — 악성종양 Screen of 5 중 2개",
        "soap_text": (
            "55M. LBP x 5 weeks, slightly improving. "
            "Night pain, wakes occasionally. Age 55. No cancer history, no weight loss."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "malignancy",
    },
    {
        "id": "YEL_02",
        "description": "YELLOW — 골절 위험인자 (고령 + 골다공증, 외상 없음)",
        "soap_text": (
            "72F. LBP onset gradual. PMH: osteoporosis. No recent fall or trauma. "
            "Pain with weight bearing, mild point tenderness. "
            "Has not had imaging in 2 years."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "fracture",
    },
    {
        "id": "YEL_03",
        "description": "YELLOW — 강직성 척추염 패턴",
        "soap_text": (
            "28M. LBP x 4 months, insidious onset. Morning stiffness over 1 hour daily. "
            "Improves with walking and exercise, worsens with rest. "
            "Alternating buttock pain. Wakes around 3am with pain."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "inflammatory",
    },
    {
        "id": "YEL_04",
        "description": "YELLOW — 면역저하 + 척추 주사 후 통증",
        "soap_text": (
            "50F. Diabetes, blood sugar poorly controlled. "
            "Epidural injection L4-L5 performed 2 weeks ago at pain clinic. "
            "New onset severe back pain different from prior. No fever currently."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "infection",
    },
    {
        "id": "YEL_05",
        "description": "RED — 악성종양 Screen of 5 중 3개 (Goodman's 기준 RED)",
        "soap_text": (
            "62F. LBP 7 weeks, no improvement with PT. "
            "Night pain regularly. No cancer history. Unexplained fatigue and malaise. "
            "Age 62. No weight loss reported."
        ),
        "expected_alarm": "RED",
        "expected_condition": "malignancy",
    },
    {
        "id": "YEL_06",
        "description": "YELLOW — 혈관 위험인자 조합 (AAA 주의)",
        "soap_text": (
            "66M. Hypertension, atherosclerosis hx. Back pain 2 weeks. "
            "Pain does not change with movement or position notably. "
            "No pulsating mass palpated. No acute change."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "vascular",
    },
    {
        "id": "YEL_07",
        "description": "YELLOW — 4주 치료 무반응 + 야간통",
        "soap_text": (
            "53M. Treated for LBP x 5 weeks, no improvement at all. "
            "Night pain that wakes him. Age 53. No prior cancer. No weight changes."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "malignancy",
    },
    {
        "id": "YEL_08",
        "description": "YELLOW — 조조 강직 + 운동 시 호전 패턴",
        "soap_text": (
            "32F. LBP 3 months, insidious onset. "
            "Morning stiffness lasting about 90 minutes. Improves significantly with activity. "
            "Worse with prolonged sitting/rest. NSAIDs work well."
        ),
        "expected_alarm": "YELLOW",
        "expected_condition": "inflammatory",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NONE 케이스 — 정상 근골격계 (7건, 알람 없어야 함)
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "NONE_01",
        "description": "정상 — 기계적 요통",
        "soap_text": (
            "34M. LBP after heavy lifting at work. Pain 5/10, improves with rest. "
            "Worse with forward flexion. No leg symptoms. No red flags noted."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_02",
        "description": "정상 — L4-L5 HNP 우측 방사통",
        "soap_text": (
            "45F. L4-L5 disc herniation, right radiculopathy. "
            "Pain and tingling right leg to knee. Improving with traction. "
            "Normal bladder and bowel function. No night pain."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_03",
        "description": "정상 — 근육 긴장",
        "soap_text": (
            "28M. Muscle strain lower back, weekend soccer injury. "
            "Local pain 4/10, no radiation. Improving with heat and stretching. "
            "Full bladder and bowel control."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_04",
        "description": "정상 — 척추관 협착 (고령, 위험인자 없음)",
        "soap_text": (
            "68F. Lumbar stenosis, neurogenic claudication. "
            "Pain and leg heaviness with walking > 2 blocks, relieved by sitting. "
            "No recent trauma, no fever, no weight loss. Stable presentation."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_05",
        "description": "정상 — 임신 관련 요통",
        "soap_text": (
            "29F, 24 weeks pregnant. Lumbar and pelvic girdle pain. "
            "Bilateral hip pain, worse with walking. Normal obstetric check. "
            "No neurological symptoms. Typical pregnancy-related presentation."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_06",
        "description": "정상 — 직업성 요통 (트럭 운전사)",
        "soap_text": (
            "41M, truck driver. Chronic LBP x 2 years, gradually improving. "
            "Mechanical pain pattern, better with movement. "
            "No systemic symptoms, no night pain, full bladder bowel control."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
    {
        "id": "NONE_07",
        "description": "정상 — 스포츠 부상 후 회복기",
        "soap_text": (
            "22M. Post-injury LBP from football tackle 3 weeks ago. "
            "Pain 3/10, improving week by week. No neuro signs. "
            "Age 22, no risk factors, responding well to treatment."
        ),
        "expected_alarm": "NONE",
        "expected_condition": None,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# 탐지 엔진 (VPPS 프로토타입)
# ══════════════════════════════════════════════════════════════════════════════

def load_kb() -> dict:
    with open(KB_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_protocol(filename: str) -> dict:
    path = PROTOCOLS_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_index() -> list:
    path = PROTOCOLS_DIR / "index.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["protocols"]


_NEGATION_PATTERNS = re.compile(
    r"(?:no|without|denies?|absence of|negative for|ruled out|"
    r"not experiencing|not having|no history of|no evidence of)"
    r"\s+"
    r"(?!improvement|improving|relief|response|change|comfortable)"
    r"(?:\w+[,;.]?\s*){0,5}",  # 쉼표·마침표 뒤 단어도 마스킹
    re.IGNORECASE,
)


def _strip_negations(text: str) -> str:
    """부정 표현 이후 최대 3단어를 마스킹해 false match 방지."""
    def _mask(m: re.Match) -> str:
        return " " * len(m.group(0))
    return _NEGATION_PATTERNS.sub(_mask, text)


def match_kb(text: str, kb: dict) -> list[dict]:
    """KB synonym 매칭 — 부정어 처리 후 긴 패턴 우선."""
    text_lower = _strip_negations(text).lower()
    hits = []
    seen = set()

    entries = []
    for kb_id, entry in kb.items():
        for syn in [entry["label"]] + entry.get("synonyms", []):
            entries.append((syn.lower(), kb_id, entry))
    entries.sort(key=lambda x: len(x[0]), reverse=True)

    for syn_lower, kb_id, entry in entries:
        if kb_id in seen:
            continue
        if syn_lower in text_lower:
            seen.add(kb_id)
            hits.append({
                "kb_id": kb_id,
                "label": entry["label"],
                "weight": entry["depth"],
                "alarm_level": entry.get("alarm_level", "YELLOW"),
                "condition_ref": entry.get("condition_ref", ""),
                "category": entry.get("category", ""),
            })

    return hits


def score_condition(protocol: dict, hits: list[dict]) -> dict:
    """단일 프로토콜에 대한 매칭 점수 계산."""
    protocol_id = protocol.get("protocol_id", "")
    condition_ref = protocol_id.replace("rfp_", "")
    condition_hits = [h for h in hits if h["condition_ref"] == condition_ref]

    if not condition_hits:
        return {"alarm": "NONE", "score": 0.0, "matched": []}

    logic = protocol.get("decision_logic", "WEIGHTED_SUM")

    # ANY_CARDINAL: standalone_trigger 하나라도 매칭 → 즉시 RED
    if logic == "ANY_CARDINAL":
        indicators = {ind["id"]: ind for ind in protocol.get("indicators", [])}
        kb_to_indicator = {}
        for ind in protocol.get("indicators", []):
            if ind.get("standalone_trigger"):
                for syn in [ind["label"]] + ind.get("synonyms", []):
                    kb_to_indicator[syn.lower()] = ind

        for hit in condition_hits:
            if hit["alarm_level"] == "RED":
                return {
                    "alarm": "RED",
                    "score": 1.0,
                    "matched": [h["label"] for h in condition_hits],
                    "trigger": hit["label"],
                }
        # cardinal 아니어도 여러 개 매칭 시 RED
        if len(condition_hits) >= 2:
            return {
                "alarm": "RED",
                "score": 0.9,
                "matched": [h["label"] for h in condition_hits],
            }
        return {
            "alarm": "YELLOW",
            "score": 0.5,
            "matched": [h["label"] for h in condition_hits],
        }

    # SCREEN_OF_5: 매칭된 screen_item 수로 판단
    if logic == "SCREEN_OF_5":
        threshold = protocol.get("threshold", {})
        red_count = threshold.get("red", 3)
        yellow_count = threshold.get("yellow", 2)

        # 암 기왕력 단독 RED (standalone_trigger)
        cancer_history_keywords = [
            "cancer history", "암 기왕력", "cancer survivor",
            "previous cancer", "암 수술 받음", "암 치료력",
            "유방암", "폐암", "전립선암", "갑상선암", "대장암", "위암"
        ]
        for hit in condition_hits:
            if hit["kb_id"] == "RF_009":
                return {
                    "alarm": "RED",
                    "score": 1.0,
                    "matched": [h["label"] for h in condition_hits],
                    "trigger": "Cancer history (standalone RED trigger)",
                }

        count = len(condition_hits)
        score = count / 5.0
        if count >= red_count:
            return {"alarm": "RED", "score": score, "matched": [h["label"] for h in condition_hits]}
        if count >= yellow_count:
            return {"alarm": "YELLOW", "score": score, "matched": [h["label"] for h in condition_hits]}
        return {"alarm": "NONE", "score": score, "matched": [h["label"] for h in condition_hits]}

    # WEIGHTED_SUM (기본)
    threshold = protocol.get("threshold", {"red": 0.70, "yellow": 0.45})
    red_t = threshold.get("red", 0.70)
    yellow_t = threshold.get("yellow", 0.45)

    # standalone_trigger 체크
    for hit in condition_hits:
        if hit["alarm_level"] == "RED" and hit["weight"] >= 0.95:
            return {
                "alarm": "RED",
                "score": 1.0,
                "matched": [h["label"] for h in condition_hits],
                "trigger": hit["label"],
            }

    # 가중치 합산 (최대 1.0으로 클램핑)
    score = min(sum(h["weight"] for h in condition_hits), 1.0)

    # fracture: trauma multiplier 적용
    if condition_ref == "fracture":
        trauma_hits = [h for h in condition_hits if "trauma" in h["category"].lower() or "외상" in h["label"]]
        if trauma_hits:
            score = min(score * protocol.get("scoring_rules", {}).get("trauma_multiplier", 1.3), 1.0)

    # RED 알람 지표가 하나도 없으면 YELLOW 이상으로 올리지 않음
    has_red_indicator = any(h["alarm_level"] == "RED" for h in condition_hits)
    protocol_max_alarm = protocol.get("alarm_level", "RED")

    raw_alarm = "RED" if score >= red_t else "YELLOW" if score >= yellow_t else "NONE"

    # 프로토콜 자체가 YELLOW-max이거나 RED 지표가 없으면 RED 차단
    if raw_alarm == "RED" and (protocol_max_alarm == "YELLOW" or not has_red_indicator):
        raw_alarm = "YELLOW"

    # fracture: 외상력 없으면 RED → YELLOW (외상 없는 위험인자 조합은 YELLOW)
    if condition_ref == "fracture" and raw_alarm == "RED":
        trauma_present = any("Trauma" in h["label"] or "외상" in h["label"] for h in condition_hits)
        if not trauma_present:
            raw_alarm = "YELLOW"

    return {"alarm": raw_alarm, "score": round(score, 3), "matched": [h["label"] for h in condition_hits]}


def detect(soap_text: str, kb: dict, protocols_index: list) -> dict:
    """SOAP 텍스트에서 Red Flag 탐지 — 가장 높은 알람 레벨 반환."""
    hits = match_kb(soap_text, kb)

    results = {}
    final_alarm = "NONE"
    final_condition = None
    alarm_priority = {"RED": 2, "YELLOW": 1, "NONE": 0}

    for proto_meta in protocols_index:
        protocol = load_protocol(proto_meta["file"])
        if not protocol:
            continue
        result = score_condition(protocol, hits)
        condition_id = proto_meta["id"].replace("rfp_", "")
        results[condition_id] = result

        if alarm_priority.get(result["alarm"], 0) > alarm_priority.get(final_alarm, 0):
            final_alarm = result["alarm"]
            final_condition = condition_id

    return {
        "alarm": final_alarm,
        "condition": final_condition,
        "details": results,
        "kb_hits": [h["label"] for h in hits],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 리포트 출력
# ══════════════════════════════════════════════════════════════════════════════

def alarm_colored(level: str) -> str:
    if level == "RED":
        return f"{RED}RED  {RESET}"
    if level == "YELLOW":
        return f"{YELLOW}YELLOW{RESET}"
    return f"{GRAY}NONE {RESET}"


def run_validation(filter_condition: Optional[str] = None, verbose: bool = False) -> dict:
    kb = load_kb()
    protocols_index = load_index()

    scenarios = SCENARIOS
    if filter_condition:
        scenarios = [s for s in scenarios if s.get("expected_condition") == filter_condition
                     or (filter_condition == "none" and s["expected_alarm"] == "NONE")]

    print(f"\n{BOLD}{'═'*65}{RESET}")
    print(f"{BOLD}  PT Red Flag Algorithm Validation Report{RESET}")
    print(f"{BOLD}{'═'*65}{RESET}")
    print(f"  KB: {KB_PATH.name}  |  프로토콜: {len(protocols_index)}개  |  시나리오: {len(scenarios)}건\n")

    groups = {
        "RED":    [s for s in scenarios if s["expected_alarm"] == "RED"],
        "YELLOW": [s for s in scenarios if s["expected_alarm"] == "YELLOW"],
        "NONE":   [s for s in scenarios if s["expected_alarm"] == "NONE"],
    }

    total = passed = fn = fp = 0
    false_negatives = []
    false_positives = []

    for group_label, group_scenarios in groups.items():
        if not group_scenarios:
            continue

        color = RED if group_label == "RED" else YELLOW if group_label == "YELLOW" else GRAY
        print(f"{color}{BOLD}{'─'*65}{RESET}")
        print(f"{color}{BOLD}  {group_label} 케이스 ({len(group_scenarios)}건){RESET}")
        print(f"{color}{BOLD}{'─'*65}{RESET}")

        for s in group_scenarios:
            result = detect(s["soap_text"], kb, protocols_index)
            got_alarm = result["alarm"]
            got_cond  = result["condition"]
            exp_alarm = s["expected_alarm"]

            is_pass = got_alarm == exp_alarm
            total += 1
            if is_pass:
                passed += 1
            elif exp_alarm == "RED" and got_alarm != "RED":
                fn += 1
                false_negatives.append(s)
            elif exp_alarm == "NONE" and got_alarm != "NONE":
                fp += 1
                false_positives.append(s)

            icon = f"{GREEN}✅{RESET}" if is_pass else f"{RED}❌{RESET}"
            got_str = alarm_colored(got_alarm)
            exp_str = alarm_colored(exp_alarm)
            cond_str = f"({got_cond or '-'})" if got_cond else ""

            print(f"  {icon} [{s['id']:<8}] {s['description']:<46}")
            print(f"          예상: {exp_str}  →  결과: {got_str} {cond_str}")

            if verbose:
                print(f"          KB 매칭: {result['kb_hits'][:4]}")
                for cond, detail in result["details"].items():
                    if detail["alarm"] != "NONE":
                        print(f"          {cond}: {detail['alarm']} (score={detail['score']}) matched={detail['matched'][:2]}")
            print()

    # ── 종합 지표 ──────────────────────────────────────────────────────────
    red_cases   = len(groups["RED"])
    none_cases  = len(groups["NONE"])
    accuracy    = passed / total * 100 if total else 0
    sensitivity = (red_cases - fn) / red_cases * 100 if red_cases else 0
    specificity = (none_cases - fp) / none_cases * 100 if none_cases else 0
    fnr         = fn / red_cases * 100 if red_cases else 0
    fpr         = fp / none_cases * 100 if none_cases else 0

    print(f"\n{BOLD}{'═'*65}{RESET}")
    print(f"{BOLD}  📊 종합 성능 지표{RESET}")
    print(f"{BOLD}{'═'*65}{RESET}")
    print(f"  전체 정확도      : {BOLD}{accuracy:.1f}%{RESET}  ({passed}/{total})")

    sens_color = GREEN if sensitivity >= 90 else YELLOW if sensitivity >= 80 else RED
    fnr_color  = GREEN if fnr <= 10 else YELLOW if fnr <= 20 else RED
    spec_color = GREEN if specificity >= 85 else YELLOW if specificity >= 70 else RED

    print(f"  Sensitivity (민감도) : {sens_color}{BOLD}{sensitivity:.1f}%{RESET}  (RED 케이스 탐지율)")
    print(f"  Specificity (특이도) : {spec_color}{BOLD}{specificity:.1f}%{RESET}  (정상 케이스 정확 판정률)")
    print(f"  False Negative Rate  : {fnr_color}{BOLD}{fnr:.1f}%{RESET}  ⚠️  (RED인데 놓친 비율 — 핵심 지표)")
    print(f"  False Positive Rate  : {BOLD}{fpr:.1f}%{RESET}  (정상인데 알람 발생)")

    if false_negatives:
        print(f"\n{RED}{BOLD}  ⚠️  False Negative (놓친 RED 케이스) — 즉시 개선 필요:{RESET}")
        for s in false_negatives:
            print(f"    · [{s['id']}] {s['description']}")

    if false_positives:
        print(f"\n{YELLOW}{BOLD}  ℹ️  False Positive (과잉 알람 케이스):{RESET}")
        for s in false_positives:
            print(f"    · [{s['id']}] {s['description']}")

    # ── 조건별 성능 ────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'─'*65}{RESET}")
    print(f"{BOLD}  📊 조건별 RED 탐지율{RESET}")
    print(f"{BOLD}{'─'*65}{RESET}")

    condition_groups: dict[str, list] = {}
    for s in SCENARIOS:
        if s["expected_alarm"] == "RED" and s.get("expected_condition"):
            cond = s["expected_condition"]
            condition_groups.setdefault(cond, []).append(s)

    for cond, cond_scenarios in sorted(condition_groups.items()):
        hits_count = 0
        for s in cond_scenarios:
            r = detect(s["soap_text"], kb, protocols_index)
            if r["alarm"] == "RED":
                hits_count += 1
        rate = hits_count / len(cond_scenarios) * 100
        rate_color = GREEN if rate == 100 else YELLOW if rate >= 67 else RED
        print(f"  {cond:<22} : {rate_color}{BOLD}{rate:.0f}%{RESET}  ({hits_count}/{len(cond_scenarios)})")

    print(f"\n{BOLD}{'═'*65}{RESET}\n")

    return {
        "total": total, "passed": passed, "accuracy": accuracy,
        "sensitivity": sensitivity, "specificity": specificity,
        "fnr": fnr, "fpr": fpr,
        "false_negatives": [s["id"] for s in false_negatives],
    }


def save_results(results: dict, out_path: Optional[str] = None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if out_path:
        path = Path(out_path)
    else:
        save_dir = ROOT / "data" / "validation_results"
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / f"validation_{timestamp}.json"

    payload = {
        "timestamp": timestamp,
        "scenario_count": results["total"],
        "passed": results["passed"],
        "accuracy": round(results["accuracy"], 1),
        "sensitivity": round(results["sensitivity"], 1),
        "specificity": round(results["specificity"], 1),
        "fnr": round(results["fnr"], 1),
        "fpr": round(results["fpr"], 1),
        "false_negatives": results["false_negatives"],
        "kb_path": str(KB_PATH),
        "protocols_dir": str(PROTOCOLS_DIR),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PT Red Flag 알고리즘 검증")
    parser.add_argument("--verbose", "-v", action="store_true", help="KB 매칭 상세 출력")
    parser.add_argument("--condition", "-c", help="특정 조건만 테스트 (cauda_equina, fracture, malignancy, infection, vascular, inflammatory, none)")
    parser.add_argument("--save", "-s", action="store_true", help="결과를 data/validation_results/에 JSON으로 저장")
    parser.add_argument("--out", "-o", help="저장 경로 지정 (--save 없이도 동작)")
    args = parser.parse_args()

    results = run_validation(filter_condition=args.condition, verbose=args.verbose)

    if args.save or args.out:
        saved_path = save_results(results, out_path=args.out)
        print(f"{GREEN}💾 결과 저장: {saved_path}{RESET}\n")

    if results["fnr"] > 15:
        print(f"{RED}⚠️  FNR {results['fnr']:.1f}% — 임계치 초과. KB 또는 가중치 조정 필요.{RESET}\n")
        sys.exit(1)
    elif results["sensitivity"] >= 90 and results["specificity"] >= 80:
        print(f"{GREEN}✅ 알고리즘 검증 통과 — Phase 3 진행 가능{RESET}\n")
    else:
        print(f"{YELLOW}⚠️  성능 기준 미달 — KB 보강 후 재실행 필요{RESET}\n")
