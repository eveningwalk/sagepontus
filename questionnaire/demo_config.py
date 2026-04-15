"""
경진대회 데모 시연용 기본 답변.
도메인: physical_therapist (물리치료사)
DB 질문 순서(common 1~6, physical_therapist 1~8)와 맞춤.
"""
from __future__ import annotations

from typing import Optional

# (category_name, order) -> 시연용 예시 답변
DEMO_ANSWERS: dict[tuple[str, int], str] = {

    # ── common (1~6) — 물리치료사 맥락 ────────────────────────────────────
    ("common", 1): (
        "외래 물리치료실에서 근골격계 환자를 담당하고 있으며, "
        "오늘은 요추 추간판 탈출증과 방사통을 호소하는 40대 남성 환자의 "
        "치료 계획을 정리하고 싶습니다."
    ),
    ("common", 2): (
        "빠른 통증 감소와 일상 복귀를 1차 목표로 하고, "
        "4주 내 기능 회복 프로그램까지 연결하는 것이 핵심입니다."
    ),
    ("common", 3): (
        "회당 치료 시간이 30분 내외로 제한되어 있고, "
        "환자가 고혈압 약을 복용 중이어서 일부 심부 열치료는 주의가 필요합니다."
    ),
    ("common", 4): (
        "임상 SOAP 노트 형식으로 작성하되, "
        "환자에게 설명할 수 있는 쉬운 홈케어 가이드도 함께 있으면 좋겠습니다."
    ),
    ("common", 5): (
        "ICD 표준 진단 코드와 국제 임상 가이드라인(McKenzie, NICE)을 "
        "참고해 근거 기반 치료 계획을 강조해 주세요."
    ),
    ("common", 6): (
        "진단은 의사 영역이므로 AI가 독립 진단을 내리지 않도록 하고, "
        "모든 수치와 치료 강도는 '제안' 수준으로 명시해 주세요."
    ),

    # ── physical_therapist (1~8) ───────────────────────────────────────────
    ("physical_therapist", 1): (
        "왼쪽 허리 통증과 함께 왼쪽 다리 후면으로 내려가는 저린감이 있으며, "
        "장시간 앉아 있으면 악화됩니다."
    ),
    ("physical_therapist", 2): (
        "MRI 상 L4-L5 추간판 탈출증(HNP) 진단을 받았으며, "
        "좌측 방사통(Radiculopathy)이 동반된 상태입니다."
    ),
    ("physical_therapist", 3): (
        "3년 전 동일 부위 수술 경험 없음, 고혈압 약 복용 중, "
        "6개월 전에 동일 증상으로 물리치료를 3주 받은 경험이 있습니다."
    ),
    ("physical_therapist", 4): (
        "1순위: 통증 수준 NRS 7 → 3 이하로 감소. "
        "2순위: 좌측 하지 근력 회복 및 보행 정상화."
    ),
    ("physical_therapist", 5): (
        "도수치료(요추 mobilization)와 운동치료(맥켄지 신전 운동)를 중심으로, "
        "전기치료(TENS)와 온열치료(핫팩)를 보조로 사용하고 싶습니다."
    ),
    ("physical_therapist", 6): (
        "고혈압으로 인한 심부 열치료 주의, 급성기 굴곡 운동 금기, "
        "건강보험 급여 범위 내 치료로 제한합니다."
    ),
    ("physical_therapist", 7): (
        "전문 임상 SOAP 노트와 함께, "
        "환자용 홈케어 가이드는 의학 용어 없이 쉽게 작성해 주세요."
    ),
    ("physical_therapist", 8): (
        "치료 단계별 진행 기준(예: NRS 점수 변화 시 다음 단계 전환)과 "
        "재발 방지를 위한 자가 운동 프로그램 포함 여부를 중점 검토하겠습니다."
    ),
}


def demo_fallback_answer(category_name: str, order: int) -> str:
    return (
        f"{category_name} 영역 {order}번에 대한 시연용 예시입니다. "
        "실제 상황에 맞게 한두 문장으로 바꿔 주세요."
    )


def get_demo_default_answer(category_name: str, order: int) -> str:
    return DEMO_ANSWERS.get((category_name, order)) or demo_fallback_answer(
        category_name, order
    )


def pick_demo_domain_category_name(exclude_common: bool = True) -> Optional[str]:
    """데모 추천 도메인: settings.DEMO_DOMAIN_CATEGORY(기본 physical_therapist)."""
    from django.conf import settings
    from questionnaire.models.models import Category

    preferred = getattr(settings, "DEMO_DOMAIN_CATEGORY", "physical_therapist")
    if Category.objects.filter(name=preferred).exists():
        return preferred

    qs = Category.objects.exclude(name="common") if exclude_common else Category.objects.all()
    first = qs.order_by("id").first()
    return first.name if first else None
