"""
simulate_cra.py — CRA (Context Retention Algorithm) 로직 구현 및 테스트
"""

import json
import re

# ---------------------------------------------------------------------------
# 1. 용어 매핑 테이블 (구어 → 표준 의학 용어)
# ---------------------------------------------------------------------------
TERM_MAP = {
    # 해부학적 위치
    "목": ("Cervical spine", 0.85),
    "허리": ("Lumbar spine", 0.85),
    "팔": ("Upper extremity", 0.80),
    "어깨": ("Shoulder", 0.85),
    "등": ("Thoracic spine", 0.80),
    # 증상
    "저리다": ("Paresthesia", 0.90),
    "저린": ("Paresthesia", 0.90),
    "뻣뻣": ("Rigidity / Limited ROM", 0.85),
    "뻣뻣해서": ("Rigidity / Limited ROM", 0.85),
    "힘이 빠지는": ("Motor weakness", 0.90),
    "힘 빠짐": ("Motor weakness", 0.90),
    "통증": ("Pain", 0.80),
    "근육통": ("Myalgia", 0.75),
    # 진단
    "목 디스크": ("Cervical disc herniation (HNP)", 0.95),
    "디스크": ("Disc herniation", 0.88),
    # 처치
    "찜질": ("Thermotherapy", 0.90),
    "전기치료": ("Electrical stimulation therapy (EST)", 0.92),
}

# 제거할 노이즈 패턴 (서사적·감정적 불필요 표현)
NOISE_PATTERNS = [
    r"일단\s*",
    r"같기도\s*하고",
    r"좀\s*",
    r"약간\s*",
    r"그냥\s*",
    r"있다고\s*하고",
    r"이라는데",
    r"래요|대요|하더라고요",
    r"느낌",
    r"어제\s*온\s*",
]

# ---------------------------------------------------------------------------
# 2. 깊이 가중치 기준
# ---------------------------------------------------------------------------
DEPTH_RULES = [
    ("Thermotherapy",                      0.9,  "intervention"),
    ("Electrical stimulation therapy",     0.9,  "intervention"),
    ("Cervical disc herniation",           0.95, "diagnosis"),
    ("Disc herniation",                    0.88, "diagnosis"),
    ("Motor weakness",                     0.90, "symptom"),
    ("Paresthesia",                        0.88, "symptom"),
    ("Rigidity / Limited ROM",             0.85, "symptom"),
    ("Myalgia",                            0.75, "symptom"),
    ("Pain",                               0.70, "symptom"),
    ("Cervical spine",                     0.30, "location"),
    ("Lumbar spine",                       0.30, "location"),
    ("Upper extremity",                    0.25, "location"),
]


# ---------------------------------------------------------------------------
# 3. CRA 처리 함수
# ---------------------------------------------------------------------------
def process_cra(raw_input: str) -> dict:
    # --- STEP 1: Noise Removal ---
    cleaned = raw_input
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # --- STEP 2: Standard Mapping ---
    tokens = []
    unmapped_count = 0
    low_confidence_terms = []

    for colloquial, (standard, confidence) in TERM_MAP.items():
        if colloquial in raw_input:
            token = {
                "original": colloquial,
                "standard": standard,
                "confidence": confidence,
            }
            if confidence < 0.7:
                low_confidence_terms.append(token)
                unmapped_count += 1
            tokens.append(token)

    # --- STEP 3: Ambiguity Protocol ---
    if low_confidence_terms:
        return {
            "status": "AMBIGUITY_HALT",
            "question": (
                f"다음 용어의 의미가 불명확합니다: "
                f"{[t['original'] for t in low_confidence_terms]}. "
                "정확한 임상 맥락을 보충해 주세요."
            ),
        }

    # --- STEP 4: Depth Weighting ---
    weighted_tokens = []
    for token in tokens:
        depth_score = 0.5  # 기본값
        category = "unknown"
        for keyword, score, cat in DEPTH_RULES:
            if keyword in token["standard"]:
                depth_score = score
                category = cat
                break
        weighted_tokens.append({
            **token,
            "depth_score": depth_score,
            "category": category,
        })

    # 환자 메타데이터 추출
    age_match = re.search(r"(\d+)대", raw_input)
    gender_match = re.search(r"(남자|여자|남성|여성)", raw_input)

    return {
        "status": "OK",
        "patient_meta": {
            "age_group": age_match.group(0) if age_match else None,
            "gender": "M" if gender_match and "남" in gender_match.group(0) else
                      "F" if gender_match and "여" in gender_match.group(0) else None,
        },
        "noise_removed": cleaned,
        "tokens": sorted(weighted_tokens, key=lambda t: t["depth_score"], reverse=True),
        "token_count": len(weighted_tokens),
    }


# ---------------------------------------------------------------------------
# 4. 테스트 실행
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_input = (
        "어제 온 40대 남자 환자, 왼쪽 목이 뻣뻣해서 고개를 못 돌리겠대요. "
        "예전에 목 디스크 판정 받은 적 있다고 하고, 오늘은 팔까지 좀 힘이 빠지는 "
        "느낌이라는데 일단 단순 근육통 같기도 하고.. 찜질이랑 전기치료 원함."
    )

    result = process_cra(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
