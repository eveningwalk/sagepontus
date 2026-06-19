"""
Red Flag 알고리즘 시나리오 통합 테스트
— 기존 validate_scenarios.py의 28개 가상 환자 케이스를 pytest parametrize로 변환
— score_soap() 전체 파이프라인 (VPPS → scorer) 검증
"""
import pytest
from vertical_pt.engine.scorer import score_soap

# ── 시나리오 정의 (validate_scenarios.py에서 이전) ───────────────────────────

SCENARIOS = [

    # ── RED: Cauda Equina (3건) ───────────────────────────────────────────────
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

    # ── RED: Fracture (3건) ───────────────────────────────────────────────────
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

    # ── RED: Malignancy (3건) ─────────────────────────────────────────────────
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

    # ── RED: Infection (2건) ──────────────────────────────────────────────────
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

    # ── RED: Vascular (2건) ───────────────────────────────────────────────────
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

    # ── YELLOW (8건) ─────────────────────────────────────────────────────────
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

    # ── NONE: 정상 근골격계 (7건) ─────────────────────────────────────────────
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


# ── pytest parametrize ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_red_flag_scenario(scenario):
    result = score_soap(scenario["soap_text"])

    assert result["alarm"] == scenario["expected_alarm"], (
        f"[{scenario['id']}] {scenario['description']}\n"
        f"  expected alarm : {scenario['expected_alarm']}\n"
        f"  got            : {result['alarm']}\n"
        f"  matched        : {result['matched']}\n"
        f"  conditions     : {[c['condition'] for c in result.get('conditions', [])]}"
    )

    if scenario["expected_condition"] is not None:
        active = {c["condition"] for c in result.get("conditions", [])}
        assert scenario["expected_condition"] in active, (
            f"[{scenario['id']}] expected condition '{scenario['expected_condition']}' "
            f"not in active conditions: {active}"
        )
