"""
PMC (PubMed Central) Real-World Academic Case Report Integration Tests
— Source: PubMed Central open-access case reports (pmc.ncbi.nlm.nih.gov)
— 목적: 학술 PT 케이스 리포트 기반 실제 RED 케이스 검증 (MTSamples PT 카테고리 소진 후 보완)

케이스 목록:
  PMC9482352  — CES (cauda equina syndrome, implant-related compression) → RED TP
  PMC6733320  — Fracture (L1 burst fracture in recreational runner)      → RED TP

결과 (2026-06-23):
  TP=2, FP=0, FN=0 — 전체 2건 RED 정확 반환

KB 수정 내역 (이 케이스로 발견):
  RF_008: 척추 맥락 한정 percussion/tuning fork test 패턴 추가
    patterns: positive (?:tuning fork|percussion) test ... vertebr|spine|thorac|lumbar|cervical
  RF_011: 야간통 synonym 보강
    추가: "worsened throughout the night", "worsened throughout night",
           "limiting sleep", "limits sleep" 등
"""

import pytest
from vertical_pt.engine.scorer import score_soap


# ── Fixtures ─────────────────────────────────────────────────────────────────

SOAP_PMC9482352_CES = """
S: 25-year-old male. History of lumbar vertebra fracture 10 years ago sustained in a 7-foot
farm fall, treated with internal fixation implants. Now presents with low back pain (prickling
quality, 7/10 during activity, 4/10 at rest), bilateral lower limb weakness, numbness in both
feet, intermittent urinary incontinence, and bilateral gluteal pain.

O: Grade II tenderness over lumbar spine on palpation. Reduced hip and knee range of motion,
left side particularly affected. Bilateral lower limb strength reduction on manual muscle
testing. Normal lower limb reflexes. Loss of sensation in the perianal area (S3, S4).
Normal anal tone.

A: Cauda equina syndrome secondary to implant-related spinal canal compression.
Requires urgent neurosurgical evaluation prior to any PT intervention.
"""

SOAP_PMC6733320_FX = """
S: 37-year-old male recreational dentist and middle-distance runner. LBP onset after a fall
during uphill 10km run. Stabbing thoracolumbar junction pain 8/10, described as continuous
and deep. Superficial lower posterior back pain 3/10 also present. Pain worsened throughout
the night, severely limiting sleep. Bilateral feet numbness and tingling. Difficulty walking,
required spousal assistance. Pain intensified by walking, brief sitting (10 minutes), and
breathing deeply.

O: Markedly decreased active ROM at T12-L2 during all planes. All active spinal movements
elicited intense pain 9/10. Positive tuning fork test at thoracolumbar vertebrae. Positive
percussion test at affected spinal level (T12-L1). No neurological deficits detected on
initial screening.

A: Clinical presentation highly suspicious for vertebral fracture at thoracolumbar junction.
Positive tuning fork and percussion tests at vertebral level with mechanism of injury
(fall during running) and night pain severity warrant urgent imaging prior to any PT treatment.
Red flags: trauma history, night pain limiting sleep, positive spinal percussion test.
"""


# ── 시나리오 정의 ──────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id": "PMC9482352",
        "title": "CES — 척추 내고정 임플란트 압박 (25M, 방광 실금 + 회음부 감각 소실)",
        "soap_text": SOAP_PMC9482352_CES,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": "cauda_equina",
        "accuracy": "TP",
        "source": "PMC9482352 — J Phys Ther Sci. 2022",
        "clinical_note": (
            "10년 전 농장 추락 골절 후 내고정 → 임플란트 척추강 압박 CES. "
            "방광 기능 이상(urinary incontinence) + 회음부 감각 소실(S3, S4) → "
            "RF_002(방광 기능) ANY_CARDINAL 즉시 RED. "
            "실제 논문: 임플란트 제거 수술 후 4주 다학제 재활."
        ),
    },
    {
        "id": "PMC6733320",
        "title": "Fracture — 달리기 낙상 후 L1 버스트 골절 (37M, 흉요추 타진 양성 + 야간통)",
        "soap_text": SOAP_PMC6733320_FX,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": "fracture",
        "accuracy": "TP",
        "source": "PMC6733320 — Physiother Theory Pract. 2019",
        "clinical_note": (
            "PT 스크리닝 논문 케이스: 37세 남성 러너, 달리기 중 낙상 후 흉요추 통증. "
            "RF_006(낙상 후 외상) + RF_008(척추 타진/tuning fork 양성) → fracture RED. "
            "RF_011(야간통, limiting sleep)도 감지. "
            "실제: L1 압박골절 → CT에서 burst fracture + 척수압박 확인 → 수술. "
            "KB 수정: RF_008에 spinal-context percussion/tuning fork test 패턴 추가로 해결."
        ),
    },
]


# ── pytest ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_pmc_system_behavior(scenario):
    """PMC 학술 케이스 리포트: 현재 시스템 동작 회귀 테스트."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["system_expected"], (
        f"[{scenario['id']}] {scenario['title']}\n"
        f"  expected : {scenario['system_expected']}\n"
        f"  got      : {result['alarm']}\n"
        f"  matched  : {result['matched']}\n"
        f"  source   : {scenario['source']}"
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_pmc_clinical_accuracy(scenario):
    """PMC 케이스: system_expected == clinical_truth."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["clinical_truth"], (
        f"[{scenario['id']}] clinical truth mismatch: "
        f"expected {scenario['clinical_truth']}, got {result['alarm']}"
    )
    if scenario.get("expected_condition"):
        active = {c["condition"] for c in result.get("conditions", [])}
        assert scenario["expected_condition"] in active, (
            f"[{scenario['id']}] expected condition '{scenario['expected_condition']}' "
            f"not found in: {active}"
        )


def test_pmc_accuracy_summary():
    """PMC 전체 케이스 TP/FP/FN 비율 검증. 목표: TP=2, FP=0, FN=0."""
    tp = sum(1 for s in SCENARIOS if s["accuracy"] == "TP")
    fp = sum(1 for s in SCENARIOS if s["accuracy"] == "FP")
    fn = sum(1 for s in SCENARIOS if s["accuracy"] == "FN")
    assert tp == 2, f"Expected 2 TP, got {tp}"
    assert fp == 0, f"Expected 0 FP, got {fp}"
    assert fn == 0, f"Expected 0 FN, got {fn}"
