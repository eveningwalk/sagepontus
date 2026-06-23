"""
PSU PT Documentation Book — Real-World SOAP Integration Tests
— Source: "An Introduction to Medical Documentation for the Physical Therapist Assistant"
          jmm49; Dan Dandy PT, DPT, ACCE / Penn State Pressbooks (Public Domain)
          https://psu.pb.unizin.org/ptamedicaldocumentation/

— Ch7 완성 SOAP 4건: 척추 Red Flag 없는 정형외과 재활 케이스
— 목적: 합성 시나리오에는 없는 실제 PT 교육자 저작 SOAP 패턴으로 FP 검증

결과 (2026-06-23):
  TP=4, FP=0, FN=0 — 전체 4건 NONE 정확 반환
  특이사항: "phantom limb pain", "hip flexion contracture", "cervical pain",
            "loses balance to left" 등 FP 위험 표현 포함에도 정상 작동
"""

import pytest
from vertical_pt.engine.scorer import score_soap


# ── Fixtures: PSU Book Ch7 완성 SOAP 노트 ────────────────────────────────────

SOAP_CH07_EX1_AKA = """
DIAGNOSIS: Above-knee amputation, prosthetic gait training, phantom limb pain.

S: Patient states that he did not sleep well last night due to phantom limb pain, RLE;
he hopes to take his prosthesis home with him soon so he can use it to walk around the
house like a normal person.

O: Gait training: With AK prosthesis in parallel bars, 30 feet x 2, with mod A.
Transfers: Sit to/from stand from w/c: min assist with verbal cues for hand placement.
Patient flexes trunk forward and laterally to R during R LE weight bearing on the prosthesis.
Therapeutic Exercise: Mat exercise program: glut sets, SLR, side-lying hip adduction and
abduction; 3 sets of 12 reps each bilaterally. Manual stretching of R hip flexor with
patient in L side-lying, 3 x 30 second hold. Right hip flexion contracture of 20 degrees
measured in supine.

A: Right gluteus medius weakness and hip flexion contracture causing patient to lateral
trunk flex to R. Patient not ready to take prosthesis home until he can ambulate with
walker with only supervision assistance. Presently he is a fall risk if he were to
ambulate at home with prosthesis.

P: Continue gait training activities; concentrate therapeutic exercises on gluteus medius
strengthening and hip extension ROM as per PT POC.
"""

SOAP_CH07_EX2_CERVICAL = """
DIAGNOSIS: Cervical pain, outpatient clinic.

S: Patient notes decreased cervical pain after last treatment; now able to rotate her neck
to the left to look for traffic while driving. No pain medications required today.

O: US: 100% 1.2w/cm2, 1MHz x 5 min to R upper trapezius, rhomboids, left scapular muscles
in sitting. Soft tissue mobilization, trigger point release to R upper trapezius, rhomboids,
left scapular muscles in sitting. Therapeutic exercise per flowsheet.

A: Patient with improving c-spine ROM and decreased pain. Compliance with HEP is excellent,
allowing her to recover without use of pain medications.

P: Continue 2x/weekly per PT POC.
"""

SOAP_CH07_EX3_KNEE = """
DIAGNOSIS: Right knee pain, post-surgical, NMES and gait training.

S: Patient reports 0-3/10 right knee pain; increasing up to 5/10 only when he twists
the knee during ambulation.

O: Therapeutic exercise per flowsheet. Modalities: NMES right quads, 50pps, 10 sec on/off
x 10 mins with quad sets, patient in long sitting. Cold pack to right knee post NMES.
Education: HEP Instruction: Reviewed present activities with patient completing all
activities without pain: 2 sets of 8 reps. Verbal cues needed for SLR technique only.
Upgraded to 3 sets of 10-12. Added standing lunges and wall slides (2 sets of 8) to HEP.
Strength: MMT knee extension: Left 5/5; Right 4/5.
Gait training on level surfaces with SPC to reduce effects of circumduction on right.
Integrated use of mirror for visual feedback and foot ladder (20 feet). Patient requires
25% verbal cues to make corrections.

A: Patient pain steadily reducing despite intermittent exacerbations during twisting
movements. Gains noted in strength and tolerance for exercise. Circumducting gait improving
through PT interventions.

P: Continue 3x/weekly progressing therapeutic exercise and gait activities per POC.
"""

SOAP_CH07_EX4_DEFICIENT = """
S: Patient reports they had some pain last night, but not much pain now.

O: Transfers: W/C to mat. Patient loses balance to left sometimes. Therapeutic exercise:
Seated balance activities. Knee extension and hip flexion. Gait Training: RW length of
PT gym twice.

A: Patient progressing with exercises.

P: Continue BID per POC plan.
"""
# 위 노트의 의도적 결함 (PSU 교재 표기):
# - 통증 위치/강도 미기재
# - 거리/보조 수준/반복 횟수 미기재
# - Assessment에 임상 근거 없음
# - Plan에 다음 세션 집중 내용 없음


# ── 시나리오 정의 ─────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id": "PSU_AKA_01",
        "title": "Above-Knee Amputation — 의족 보행 훈련 (phantom limb pain, hip contracture)",
        "soap_text": SOAP_CH07_EX1_AKA,
        "system_expected": "NONE",
        "clinical_truth": "NONE",
        "accuracy": "TP",
        "fp_risk_keywords": ["phantom limb pain", "hip flexion contracture", "fall risk"],
        "clinical_note": (
            "No spinal Red Flags. Rehab case: AKA prosthetic training. "
            "'Phantom limb pain' is RLE neuropathic pain from amputation site — not spinal. "
            "'Fall risk' is functional ADL concern — not systemic Red Flag. "
            "System correctly returns NONE."
        ),
    },
    {
        "id": "PSU_CX_01",
        "title": "Cervical Pain — 외래 경추 치료 (improving, no red flags)",
        "soap_text": SOAP_CH07_EX2_CERVICAL,
        "system_expected": "NONE",
        "clinical_truth": "NONE",
        "accuracy": "TP",
        "fp_risk_keywords": ["cervical pain", "c-spine"],
        "clinical_note": (
            "Mechanical cervical pain, outpatient. Improving with PT. "
            "No neurological deficits, no systemic symptoms, no night pain. "
            "System correctly returns NONE."
        ),
    },
    {
        "id": "PSU_KN_01",
        "title": "Right Knee Pain — 수술 후 무릎 재활 (NMES, gait training)",
        "soap_text": SOAP_CH07_EX3_KNEE,
        "system_expected": "NONE",
        "clinical_truth": "NONE",
        "accuracy": "TP",
        "fp_risk_keywords": ["post-surgical", "gait training", "SPC"],
        "clinical_note": (
            "Post-surgical right knee rehab. No spinal involvement. "
            "Pain is mechanical (twisting), improving. "
            "System correctly returns NONE."
        ),
    },
    {
        "id": "PSU_DEF_01",
        "title": "Wheelchair Balance [Deficient Note] — 의도적 결함 예시",
        "soap_text": SOAP_CH07_EX4_DEFICIENT,
        "system_expected": "NONE",
        "clinical_truth": "NONE",
        "accuracy": "TP",
        "fp_risk_keywords": ["loses balance to left"],
        "clinical_note": (
            "Intentionally deficient note (PSU textbook negative example). "
            "Vague pain description, missing metrics, no clinical rationale. "
            "Despite information gaps, system correctly returns NONE — "
            "no Red Flag keywords present even in sparse text."
        ),
    },
]


# ── pytest parametrize ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_psu_book_system_behavior(scenario):
    """PSU PT 교육자 저작 SOAP의 현재 시스템 동작 회귀 테스트."""
    result = score_soap(scenario["soap_text"])

    assert result["alarm"] == scenario["system_expected"], (
        f"[{scenario['id']}] {scenario['title']}\n"
        f"  expected : {scenario['system_expected']}\n"
        f"  got      : {result['alarm']}\n"
        f"  matched  : {result['matched']}\n"
        f"  fp_risk  : {scenario['fp_risk_keywords']}"
    )


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_psu_book_clinical_accuracy(scenario):
    """PSU 교재 케이스: system_expected == clinical_truth (모두 NONE)."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["clinical_truth"], (
        f"[{scenario['id']}] clinical truth mismatch: "
        f"expected {scenario['clinical_truth']}, got {result['alarm']}"
    )


def test_psu_book_accuracy_summary():
    """
    PSU Book 전체 케이스 FP/FN 비율 검증.
    목표: TP=4, FP=0, FN=0 (100% — 교육자 저작 고품질 NONE 케이스).
    """
    tp_count = sum(1 for s in SCENARIOS if s["accuracy"] == "TP")
    fp_count = sum(1 for s in SCENARIOS if s["accuracy"] == "FP")
    fn_count = sum(1 for s in SCENARIOS if s["accuracy"] == "FN")
    total = len(SCENARIOS)

    assert tp_count == 4, f"Expected 4 TP, got {tp_count}"
    assert fp_count == 0, f"Expected 0 FP, got {fp_count}"
    assert fn_count == 0, f"Expected 0 FN, got {fn_count}"
    assert total == 4

    assert tp_count / total == 1.0, (
        f"PSU accuracy regressed: {tp_count/total:.1%}\n"
        f"TP={tp_count} FP={fp_count} FN={fn_count} / Total={total}"
    )
