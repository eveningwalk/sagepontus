"""
정부과제 데모 시연용 기본 답변 (카테고리명 + 질문 순서).
DB에 질문이 더 있어도 fallback 문구로 채움.
"""
from __future__ import annotations

from typing import Optional

# (category_name, order) -> 평가자용 예시 답변
DEMO_ANSWERS: dict[tuple[str, int], str] = {
    ("common", 1): (
        "공공·행정 분야에서 디지털 전환 과제를 수행 중이며, "
        "이해관계자 협의와 규정 준수를 병행해야 하는 상황입니다."
    ),
    ("common", 2): (
        "핵심 목표는 시범 서비스 안정화와 예산 내 결과물 도출이며, "
        "분기별 점검 지표로 진척도를 관리합니다."
    ),
    ("common", 3): (
        "일정·인력·외부 연계(용역) 등 제약이 있어 단계적 롤아웃을 계획하고 있습니다."
    ),
    # startup (questions_startup.json) — 데모 시 연속 화면용
    ("startup", 1): (
        "소상공인·로컬 매장의 온라인 노출이 부족해 신규 고객 유입이 정체되는 문제를 해결하고 싶습니다."
    ),
    ("startup", 2): (
        "반복 업무를 자동화하고, 초보 운영자도 따라 할 수 있는 체크리스트형 가이드를 제공하는 것이 핵심 가치입니다."
    ),
    ("startup", 3): (
        "초기 예산은 제한적이며, 내부 인력 2명과 외부 멘토링·정부 지원 과제 연계를 활용할 계획입니다."
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
    """데모에서 추천할 도메인: settings.DEMO_DOMAIN_CATEGORY(기본 startup), 없으면 common 제외 첫 카테고리."""
    from django.conf import settings
    from questionnaire.models.models import Category

    preferred = getattr(settings, "DEMO_DOMAIN_CATEGORY", "startup")
    if Category.objects.filter(name=preferred).exists():
        return preferred

    qs = Category.objects.exclude(name="common") if exclude_common else Category.objects.all()
    first = qs.order_by("id").first()
    return first.name if first else None
