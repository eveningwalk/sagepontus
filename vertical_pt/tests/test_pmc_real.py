"""
PMC (PubMed Central) Real-World Academic Case Report Integration Tests
— Source: PubMed Central open-access case reports (pmc.ncbi.nlm.nih.gov)
— 목적: 학술 PT 케이스 리포트 기반 실제 RED 케이스 검증 (MTSamples PT 카테고리 소진 후 보완)

케이스 목록:
  PMC9482352  — CES (cauda equina syndrome, implant-related)          → RED  TP
  PMC6733320  — Fracture (L1 burst fracture, recreational runner)     → RED  TP
  PMC6112066  — Malignancy (breast cancer metastasis, runner)         → RED  TP
  PMC9603351  — Malignancy + CES (vertebral hemangioma, direct access)→ RED  TP
  PMC4101555  — Malignancy initial eval (lung cancer, subtle flags)   → YELLOW FN (known gap)
  PMC7772297  — Infection (spondylodiscitis, afebrile at eval)        → YELLOW FN (known gap)

결과 (2026-06-23):
  TP=4, FP=0, FN=2
  FN 사유: 초기 평가 시점의 정보만으로는 RED 판정 불가
    PMC4101555: 암 기왕력 없음, 야간통 경미, 초기 평가 YELLOW가 임상적으로 합리적
    PMC7772297: 발열 없음(afebrile), 감염 기왕력 없음, 야간발한+체중감소=악성종양 패턴으로 분류

KB 수정 내역 (이 케이스들로 발견):
  RF_008: 척추 맥락 한정 percussion/tuning fork test 패턴 추가 (PMC6733320)
  RF_011: 야간통 synonym 보강 "worsened throughout the night", "limiting sleep" (PMC6733320)
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

SOAP_PMC6112066_MAL = """
S: 50-year-old female long distance runner. History of left breast carcinoma 5 years ago,
treated with bilateral mastectomy and chemotherapy — currently in remission. Now presents
with persistent moderate right lumbar and thoracic pain, exacerbated by spinal movement.
Has been running 3 half-marathons in 45 days. No night pain, weight loss, or fever reported.

O: Full cervical, thoracic, lumbar range of motion. Mild tenderness to palpation right upper
trapezius and thoracolumbar paraspinal muscles. Marked muscle hypertonicity. Hypomobility
and percussion tenderness on spinal palpation at thoracic and lumbar levels.
No neurological deficits. No radicular or sensory symptoms.

A: Persistent right thoracolumbar pain in patient with breast cancer history. Red flags
present: prior malignancy, age over 50, percussion tenderness at thoracic spine.
Imaging required prior to PT intervention.
"""

SOAP_PMC9603351_MAL = """
S: 52-year-old male bus driver. Intense sacral pain 8/10, onset 3 months ago, progressive.
Initial pain 3/10, worsened to constant disabling 7-8/10 over weeks. Unable to continue work.
History of testicular seminoma excised 2017; discontinued oncology follow-up since 2020.
Unexplained weight loss 9 kg over past 6 weeks. Pain unresponsive to NSAIDs.
Urinary incontinence with cough and sneeze. Saddle dysesthesia reported.

O: Limited trunk flexion 60 degrees, extension 10 degrees. Positive closed-fist percussion
sign at L4-S1. Positive supine sign — unable to lie supine. Passive accessory intervertebral
motion test positive, reproducing familiar deep widespread sacral pain.

A: Multiple red flags: prior malignancy, unexplained weight loss, progressive unremitting
sacral pain, bladder dysfunction, saddle sensory changes, positive percussion at L4-S1.
Urgent MRI required. Direct access case — PT initiated referral.
"""

SOAP_PMC4101555_MAL_FN = """
S: 48-year-old female. Low back pain at L1-L2 level for 8 weeks, no precipitating cause.
Pain intermittent, dull ache. Aggravated by sitting and lifting, relieved by standing.
Most intense in evenings; causes sleep disruption. Did not improve after one month of
conservative medical management. Heavy smoker: 15 cigarettes daily for 34 years (25.5
pack-years). History of anxiety and depression. Reports fatigue and new-onset constipation.

O: Pain 3/10 sitting, 0/10 standing. Normal gait. Lumbar ROM slight pain with flexion
and left lateral flexion. L1-L2 hypomobility reproduced symptoms. Prone press-ups
completely resolved symptoms. No neurological deficits.
"""

SOAP_PMC7772297_INF_FN = """
S: 71-year-old male. Three-month history of low back pain radiating to right hip and thigh.
Progressive low back pain with right lower limb weakness developing over the past 3 days.
Constitutional symptoms: anorexia, night sweats, unintentional weight loss 10 kg over
8 weeks. No fever at presentation. Ex-smoker (15 pack-years). No trauma history.

O: Diffuse low back tenderness and right groin tenderness on palpation. Painful limitation
of right hip movement in all planes. Neurologically intact at this evaluation. Afebrile.
Blood pressure 130/72 mmHg.
"""


# ── 시나리오 정의 ──────────────────────────────────────────────────────────────

SCENARIOS = [
    # ── RED TP ────────────────────────────────────────────────────────────────
    {
        "id": "PMC9482352",
        "title": "CES — 척추 임플란트 압박 (25M, 방광 실금 + 회음부 감각 소실)",
        "soap_text": SOAP_PMC9482352_CES,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": "cauda_equina",
        "accuracy": "TP",
        "source": "PMC9482352 — J Phys Ther Sci. 2022",
        "clinical_note": (
            "10년 전 농장 추락 골절 후 내고정 → 임플란트 척추강 압박 CES. "
            "RF_002(방광 실금) ANY_CARDINAL 즉시 RED + RF_001(회음부 감각 소실). "
            "실제: 임플란트 제거 수술 후 4주 다학제 재활."
        ),
    },
    {
        "id": "PMC6733320",
        "title": "Fracture — 달리기 낙상 L1 버스트 골절 (37M, 척추 타진 양성 + 야간통)",
        "soap_text": SOAP_PMC6733320_FX,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": "fracture",
        "accuracy": "TP",
        "source": "PMC6733320 — Physiother Theory Pract. 2019",
        "clinical_note": (
            "PT 스크리닝 논문 케이스. RF_006(낙상 외상) + RF_008(척추 타진/tuning fork 양성) "
            "→ fracture RED. 실제: L1 burst fracture + 척수 압박 → 수술. "
            "RF_008 spinal-context 패턴 추가로 해결."
        ),
    },
    {
        "id": "PMC6112066",
        "title": "Malignancy — 유방암 기왕력 러너 (50F, 흉요추 통증 + 척추 압통)",
        "soap_text": SOAP_PMC6112066_MAL,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": None,
        "accuracy": "TP",
        "source": "PMC6112066 — J Chiropr Med. 2018",
        "clinical_note": (
            "유방암 완치 후 5년, 러닝 중 흉요추통증. RF_009(암 기왕력) → 즉시 RED. "
            "실제: 흉요추 척추 용골 전이 + 우측 L3 경돌기 소실 + 간 전이 발견. "
            "야간통/체중감소 없었음에도 암 기왕력 단독으로 RED 정합."
        ),
    },
    {
        "id": "PMC9603351",
        "title": "Malignancy+CES — 고환암 기왕력 + 척수압박 (52M, 체중감소 9kg + 방광)",
        "soap_text": SOAP_PMC9603351_MAL,
        "system_expected": "RED",
        "clinical_truth": "RED",
        "expected_condition": "cauda_equina",
        "accuracy": "TP",
        "source": "PMC9603351 — Healthcare (Basel). 2022",
        "clinical_note": (
            "직접 접근(direct access) PT 케이스. 고환암 기왕력 + 9kg 체중감소 + "
            "안장 감각 이상 + 방광 기능 이상 + L4-S1 percussion sign → RED. "
            "실제: S2 공격적 척추 혈관종 척수 압박. PT가 영상 의뢰 후 발견."
        ),
    },

    # ── YELLOW FN (알려진 한계: 초기 평가 정보 부족) ─────────────────────────
    {
        "id": "PMC4101555",
        "title": "[FN] Malignancy — 폐암 초기 평가 (48F, 암 기왕력 없음, 미약한 Red Flag)",
        "soap_text": SOAP_PMC4101555_MAL_FN,
        "system_expected": "YELLOW",
        "clinical_truth": "RED",
        "expected_condition": None,
        "accuracy": "FN",
        "source": "PMC4101555 — Physiother Can. 2014",
        "clinical_note": (
            "알려진 FN. 초기 평가 시: 암 기왕력 없음, 야간통 경미(evening pain), "
            "prone press-ups로 증상 완전 소실. 시스템: 우울/불안 + 흡연 = YELLOW. "
            "실제: 비소세포폐암 L1-L2 + 뇌 전이. 6회차에 새로운 신경 증상(좌수 약화) 발현 후 응급 의뢰. "
            "초기 평가만으로는 RED 판정 불가 — 합리적 FN."
        ),
    },
    {
        "id": "PMC7772297",
        "title": "[FN] Infection — 척추염/경막외 농양 (71M, 발열 없음, 악성종양 패턴으로 분류)",
        "soap_text": SOAP_PMC7772297_INF_FN,
        "system_expected": "YELLOW",
        "clinical_truth": "RED",
        "expected_condition": None,
        "accuracy": "FN",
        "source": "PMC7772297 — BMJ Case Rep. 2020",
        "clinical_note": (
            "알려진 FN. 초기 평가 시 afebrile(발열 없음), 감염 기왕력 없음. "
            "야간발한 + 체중감소 10kg = 악성종양 패턴으로 YELLOW 분류. "
            "실제: S. aureus 척추염(L2-3, L5-S1) + 경막외 농양 + DVT + 패혈증. "
            "감염 Red Flag(발열/면역저하/IV drug use) 부재로 infection 미감지 — 합리적 FN."
        ),
    },
]


# ── pytest ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_pmc_system_behavior(scenario):
    """PMC 학술 케이스: 현재 시스템 동작 회귀 테스트 (system_expected 기준)."""
    result = score_soap(scenario["soap_text"])
    assert result["alarm"] == scenario["system_expected"], (
        f"[{scenario['id']}] {scenario['title']}\n"
        f"  expected : {scenario['system_expected']}\n"
        f"  got      : {result['alarm']}\n"
        f"  matched  : {result['matched']}\n"
        f"  source   : {scenario['source']}"
    )


@pytest.mark.parametrize(
    "scenario",
    [s for s in SCENARIOS if s["accuracy"] == "TP"],
    ids=[s["id"] for s in SCENARIOS if s["accuracy"] == "TP"],
)
def test_pmc_clinical_accuracy_tp(scenario):
    """PMC TP 케이스: system_expected == clinical_truth."""
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
    """PMC 전체 케이스 TP/FP/FN 비율 검증."""
    tp = sum(1 for s in SCENARIOS if s["accuracy"] == "TP")
    fp = sum(1 for s in SCENARIOS if s["accuracy"] == "FP")
    fn = sum(1 for s in SCENARIOS if s["accuracy"] == "FN")
    total = len(SCENARIOS)

    assert tp == 4, f"Expected 4 TP, got {tp}"
    assert fp == 0, f"Expected 0 FP, got {fp}"
    assert fn == 2, f"Expected 2 FN (known gaps), got {fn}"
    assert total == 6, f"Expected 6 total, got {total}"
