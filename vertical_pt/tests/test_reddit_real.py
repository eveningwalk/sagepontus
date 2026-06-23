"""
Reddit r/physicaltherapy — Real-World Red Flag Cases
Source: https://www.reddit.com/r/physicaltherapy/comments/1smcimq/
        "What's the biggest red flag you caught during your career?"

원출처: PT 현직자들이 실제로 경험한 Red Flag 사례 공유 스레드 (7년 전 게시물).
변환 방식: 임상 서술에 충실한 SOAP S+O 재구성 — 진단명, 결과는 원문 기준.
목적: 합성·교과서 데이터에 없는 실제 임상 언어 패턴으로 TP/FN 갭 탐지.

KB 수정 이력 (이 파일 생성 과정에서 발견된 갭 처리):
  - RF_034 pattern: "(?:chest|thoracic)" → "(?:chest)" 만으로 축소
    → "upper thoracic and lumbar pain" 이 cardiovascular ROS로 오탐되는 FP 수정
  - RF_011 pattern: 유연한 야간통 패턴 추가
    → "pain also present at night" 같이 사이에 단어 있는 표현 포착
  - RF_017 synonyms: "constant regardless of position", "unresponsive to position" 추가
    → 자세 무관 통증의 다양한 표현 커버

알려진 KB 갭 (이 테스트가 xfail로 추적):
  - RDT_05: UMN 징후 (hyperreflexia, spasticity, complete LE sensory/motor loss)
    → KB가 LMN(CES) 중심으로 설계되어 척수 압박 상위 운동신경원 징후 미탐지

결과 요약 (2026-06-23):
  TP=4 (RDT_01 YELLOW, RDT_02/03/04 RED)
  FN=1 (RDT_05: KB UMN 갭 — xfail로 추적 중)
"""

import pytest
from vertical_pt.engine.scorer import score_soap


# ── SOAP 재구성 텍스트 ─────────────────────────────────────────────────────────

# chmrly 댓글 — 사례 3: 흉요추부 통증, 자세 무관 상수통, 야간통, 야간발한
# 결과: 췌장암 진단 (초음파 의뢰 후)
SOAP_RDT01_PANCREATIC = """
S: Patient presents with upper thoracic and lumbar pain at T12-L2 level, radiating to the left.
Pain is constant regardless of activity or position. Pain also present at night with associated
night sweats. Tried foam rolling without any relief. Pain unresponsive to any position change.

O: Lumbar and thoracic ROM within functional limits. No significant ROM deficits noted.
Neurodynamic testing performed — no improvement in pain. Light therapeutic exercise attempted
— pain unchanged. Pain pattern appears non-mechanical.
"""

# BlueGillMan 댓글 — 우측 앞 고관절 통증, 잦은 낙상, 양측 하지 근력 약화, 항진된 심부건반사
# 결과: ALS 진단 (상위 운동신경원 의심으로 신경과 의뢰 후)
SOAP_RDT02_ALS = """
S: Patient referred for anterior right hip pain with frequent falls over the past several months.
Symptoms have been progressively worsening. No prior spinal diagnosis.

O: Lower extremity strength bilateral: weaker than expected for age, right greater than left.
Deep tendon reflexes bilateral lower extremity: hyperreflexive. No clonus observed.
Gait assessment: antalgic pattern. Progressive bilateral leg weakness noted on exam.
Upper motor neuron signs suspected.
"""

# wi_voter 댓글 — 낙상 후 경추·상배부 통증, "머리가 떨어질 것 같다" 주소
# 결과: 치돌기 골절 (구강 개방 엑스레이 확인)
SOAP_RDT03_DENS_FX = """
S: Patient presents with neck pain and upper back pain following a fall. Patient reports
her head feels like it is going to fall off. Significant cervical pain and instability concern.

O: Cervical ROM severely limited in all directions due to pain and guarding.
Conservative treatment applied to ribs and thoracic spine only per clinical judgment.
Neurological screen: intact upper extremity sensation and strength bilaterally.
"""

# tjreicks 댓글 — 마미증후군 징후 명확한 케이스
# 결과: 응급 수술 (직접 경험 1년에 3건)
SOAP_RDT04_CES = """
S: Patient presents with acute onset bilateral leg weakness and numbness in the perineal
and saddle area. Reports difficulty with bladder control — unable to initiate urination.
Also reports perianal numbness started approximately 2 days ago.

O: Bilateral lower extremity weakness 3/5 throughout. Saddle anesthesia confirmed on
sensory screen. Deep tendon reflexes diminished bilateral lower extremity.
Bowel and bladder dysfunction reported. Emergent referral indicated.
"""

# PaperPusherPT 댓글 — 양측 무릎 구축, 고관절 이하 감각·운동 소실
# 결과: 척추 종양 의심으로 신경과 의뢰 (직장 이직 후 결과 불명)
# KB 갭: UMN 징후 (spasticity, hyperreflexia, complete LE sensory/motor loss) 미탐지
SOAP_RDT05_SPINAL_TUMOR = """
S: Patient presents with bilateral knee contractures following healed tibial fractures.
Family reports progressive loss of sensation and movement below the hip level bilaterally.

O: Sensory screen bilateral lower extremity from hip to foot: absent bilaterally.
Voluntary motor function bilateral lower extremity: absent throughout.
Bilateral knee and ankle extension: severe spasticity noted.
Deep tendon reflexes bilateral knees and ankles: hyperreflexive.
Upper extremity strength and sensation: within normal limits.

A: Complete bilateral lower extremity sensory and motor loss below hips.
Upper motor neuron signs present. Pattern inconsistent with knee fracture sequelae alone.
"""


# ── 시나리오 정의 ─────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id": "RDT_01",
        "title": "췌장암 — 흉요추 상수통 + 야간발한 (chmrly)",
        "soap_text": SOAP_RDT01_PANCREATIC,
        "system_expected": "YELLOW",
        "clinical_truth": "YELLOW",
        "accuracy": "TP",
        "kb_gap": None,
        "clinical_note": (
            "SCREEN_OF_5: RF_011(야간통) + RF_012(무반응) + RF_022(야간발한) = 3개 "
            "→ RED 기준 4개 미달 → YELLOW 정합. "
            "PT 임상 직관(비기계적 패턴)이 의뢰 트리거였고 알람은 YELLOW 수준 근거가 맞음. "
            "조건 레이블이 vascular로 표시되는 이슈 있음 (RF_017 condition_ref=vascular). "
            "알람 레벨은 정확."
        ),
    },
    {
        "id": "RDT_02",
        "title": "ALS — 잦은 낙상 + 진행성 양측 하지 근력 약화 + UMN 징후 (BlueGillMan)",
        "soap_text": SOAP_RDT02_ALS,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "accuracy": "TP",
        "kb_gap": None,
        "clinical_note": (
            "RF_005(Progressive Neurological Deficit) via 'bilateral leg weakness'. "
            "조건 레이블 cauda_equina 표시 — 실제 진단은 ALS(UMN)이나 "
            "'양측 하지 진행성 약화'는 CES와 동일 KB entry로 탐지. 알람 레벨 RED 정확."
        ),
    },
    {
        "id": "RDT_03",
        "title": "치돌기 골절 — 낙상 후 경추통 + 머리 불안정감 (wi_voter)",
        "soap_text": SOAP_RDT03_DENS_FX,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "accuracy": "TP",
        "kb_gap": None,
        "clinical_note": (
            "RF_006(Significant Trauma) 낙상 기전. "
            "'head feels like it is going to fall off' → cervical instability 표현 → "
            "현재 KB에 직접 synonym 없으나 외상력으로 RED 도달. "
            "향후 경추 불안정 표현 synonym 보강 시 추가 강화 가능."
        ),
    },
    {
        "id": "RDT_04",
        "title": "마미증후군 — 안장 감각 소실 + 방광 기능 이상 (tjreicks)",
        "soap_text": SOAP_RDT04_CES,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "accuracy": "TP",
        "kb_gap": None,
        "clinical_note": (
            "RF_001(Saddle Anesthesia) + RF_002(Bladder Dysfunction) + RF_004(Bilateral LE Weakness). "
            "교과서적 CES 3대 징후 전부 명시 → RED 정합. "
            "실제 PT 직업 현장의 CES 기술 방식 검증됨."
        ),
    },
    {
        "id": "RDT_05",
        "title": "척추 종양 — 완전 양측 하지 감각·운동 소실 + UMN 징후 (PaperPusherPT)",
        "soap_text": SOAP_RDT05_SPINAL_TUMOR,
        "system_expected": "NONE",
        "clinical_truth": "RED",
        "accuracy": "FN",
        "kb_gap": "UMN signs (hyperreflexia, spasticity, complete LE sensory/motor loss) — KB is LMN/CES focused",
        "clinical_note": (
            "KB 갭: VPPS는 LMN(CES) 중심으로 설계됨. "
            "UMN 징후인 spasticity, hyperreflexia, 완전 양측 하지 감각·운동 소실은 "
            "현재 어떤 KB entry에도 synonym/pattern 없음. "
            "negation stripper 이슈도 없음 — 'absent bilaterally' 같이 긍정 표현으로 기술해도 탐지 실패. "
            "수정 방향: RF_005에 UMN synonym 추가 또는 신규 RF entry 신설."
        ),
    },
]


# ── 시스템 동작 회귀 테스트 (현재 실제 출력 추적) ─────────────────────────────

@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_reddit_system_behavior(scenario):
    """Reddit 케이스 현재 시스템 출력 회귀 — system_expected가 바뀌면 즉시 알림."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["system_expected"], (
        f"[{scenario['id']}] {scenario['title']}\n"
        f"  expected : {scenario['system_expected']}\n"
        f"  got      : {result['alarm']}\n"
        f"  matched  : {result['matched']}\n"
        f"  note     : {scenario['clinical_note'][:120]}"
    )


# ── 임상 정확도 목표 테스트 (FN은 xfail — KB 수정 시 자동 pass) ───────────────

@pytest.mark.parametrize(
    "scenario",
    [s for s in SCENARIOS if s["accuracy"] == "TP"],
    ids=[s["id"] for s in SCENARIOS if s["accuracy"] == "TP"],
)
def test_reddit_clinical_accuracy_tp(scenario):
    """TP 케이스: system output == clinical truth."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["clinical_truth"], (
        f"[{scenario['id']}] TP regression: "
        f"expected {scenario['clinical_truth']}, got {result['alarm']}"
    )


@pytest.mark.parametrize(
    "scenario",
    [s for s in SCENARIOS if s["accuracy"] == "FN"],
    ids=[s["id"] for s in SCENARIOS if s["accuracy"] == "FN"],
)
@pytest.mark.xfail(
    reason="Known KB gap — UMN signs not in KB. Will auto-pass when RF_005 UMN synonyms added.",
    strict=True,
)
def test_reddit_known_gaps_xfail(scenario):
    """FN 케이스: KB 갭으로 현재 탐지 실패 — KB 수정 시 자동 pass."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["clinical_truth"], (
        f"[{scenario['id']}] Gap: {scenario['kb_gap']}\n"
        f"  clinical_truth : {scenario['clinical_truth']}\n"
        f"  got            : {result['alarm']}"
    )


def test_reddit_accuracy_summary():
    """Reddit 케이스 전체 정확도 요약 — TP/FN 비율 추적."""
    tp = sum(1 for s in SCENARIOS if s["accuracy"] == "TP")
    fn = sum(1 for s in SCENARIOS if s["accuracy"] == "FN")
    total = len(SCENARIOS)

    assert tp == 4, f"TP regression: expected 4, got {tp}"
    assert fn == 1, f"FN count changed: expected 1 (UMN gap), got {fn}"
    assert total == 5
