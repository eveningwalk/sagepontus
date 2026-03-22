# 공통·startup 카테고리와 질문이 없으면 생성 (migrate만으로 프로덕션 DB 보장)
# seed_categories JSON 누락·실패 시에도 Category 404 방지

from django.db import migrations


def ensure_seed(apps, schema_editor):
    Category = apps.get_model("questionnaire", "Category")
    Question = apps.get_model("questionnaire", "Question")

    common, _ = Category.objects.get_or_create(
        name="common",
        defaults={"description": ""},
    )
    startup, _ = Category.objects.get_or_create(
        name="startup",
        defaults={"description": ""},
    )

    COMMON = [
        {
            "order": 1,
            "question_text": "오늘 정리하고 싶은 주제나 고민은 무엇인가요?",
            "question_description": "당신이 AI에게 도움을 받고 싶은 주제를 한 문장으로 구체적으로 작성해주세요. AI가 전체 Prompt를 이해하고 분석하는 데 활용됩니다.",
            "question_hint": "예: '오늘은 블로그 글 아이디어를 구체적으로 정리하고 싶습니다.'",
            "purpose": "context",
        },
        {
            "order": 2,
            "question_text": "이 주제를 해결하거나 결과물을 얻고 싶은 가장 큰 이유는 무엇인가요?",
            "question_description": "심리적 동기나 목표를 한 문장으로 작성해주세요. AI가 사용자의 동기와 목적을 이해하고 Prompt를 설계할 때 참고됩니다.",
            "question_hint": "예: '전문성을 강조하고 성장할 수 있는 결과물을 얻고 싶습니다.'",
            "purpose": "motivation",
        },
        {
            "order": 3,
            "question_text": "현재 이 주제를 다루는 데 가장 큰 어려움은 무엇인가요?",
            "question_description": "문제를 해결하는 데 방해가 되는 핵심 장애 요소를 한 문장으로 작성해주세요. AI가 현실적인 솔루션을 생성할 때 참고됩니다.",
            "question_hint": "예: '시간이 부족하고 아이디어 정리가 잘 되지 않습니다.'",
            "purpose": "constraint",
        },
        {
            "order": 4,
            "question_text": "이 결과물이 어떤 형태나 스타일로 나오면 가장 도움이 될까요?",
            "question_description": "AI가 생성할 결과물의 톤, 길이, 포맷 등을 한 문장으로 구체적으로 작성해주세요.",
            "question_hint": "예: '친근한 톤으로 단계별 계획을 요약한 형태가 가장 도움이 됩니다.'",
            "purpose": "constraint",
        },
        {
            "order": 5,
            "question_text": "이 주제와 관련해서 포함하거나 강조하고 싶은 핵심 요소가 있나요?",
            "question_description": "AI가 놓치지 말아야 할 중요한 포인트를 한 문장으로 작성해주세요.",
            "question_hint": "예: '특정 사례와 나의 가치관, 목표 달성 전략을 반드시 포함해주세요.'",
            "purpose": "motivation",
        },
        {
            "order": 6,
            "question_text": "AI에게 제공한 정보 중 추가로 강조하고 싶은 내용이나 주의점이 있나요?",
            "question_description": "사용자가 Prompt에 반영되길 원하는 세부 조건이나 유의사항을 한 문장으로 작성해주세요.",
            "question_hint": "예: '금지어 사용 금지, 특정 스타일과 관점을 반드시 반영해주세요.'",
            "purpose": "constraint",
        },
    ]

    STARTUP = [
        {
            "order": 1,
            "question_text": "당신이 해결하고 싶은 문제(문제 정의)는 무엇인가요?",
            "question_description": "공통 질문과 달리, 창업 아이템이나 서비스가 해결하려는 핵심 비즈니스 문제를 한 문장으로 작성해주세요.",
            "question_hint": "예: '소상공인의 온라인 마케팅이 부족하여 매출이 감소하고 있습니다.'",
            "purpose": "context",
        },
        {
            "order": 2,
            "question_text": "해결책(제품/서비스)의 핵심 가치는 무엇인가요?",
            "question_description": "당신의 솔루션이 제공하는 특별한 가치를 한 문장으로 작성해주세요. AI가 이 가치를 중심으로 Prompt를 구성합니다.",
            "question_hint": "예: '우리 서비스는 사용자가 시간을 절약하고 더 나은 경험을 할 수 있도록 돕습니다.'",
            "purpose": "motivation",
        },
        {
            "order": 3,
            "question_text": "현재 사용할 수 있는 자금 및 리소스는 무엇인가요?",
            "question_description": "투입 가능한 자원과 지원을 한 문장으로 작성해주세요. AI가 현실적 제안을 생성할 때 활용됩니다.",
            "question_hint": "예: '초기 자금 1000만원, 2명의 팀원, 네트워크 지원 가능'",
            "purpose": "constraint",
        },
        {
            "order": 4,
            "question_text": "당신의 주요 고객 타겟은 누구인가요?",
            "question_description": "제품/서비스의 1차 고객군을 한 문장으로 작성해주세요. 공통 질문과 달리 사업적 관점에서 구체화합니다.",
            "question_hint": "예: '20대 대학생을 대상으로 온라인 교육 서비스를 제공합니다.'",
            "purpose": "context",
        },
        {
            "order": 5,
            "question_text": "이 창업이 성공했을 때 당신의 삶은 어떻게 바뀔까요?",
            "question_description": "창업으로 인해 예상되는 구체적인 변화와 성과를 한 문장으로 작성해주세요. AI가 목표 지향적인 Prompt를 설계할 때 참고합니다.",
            "question_hint": "예: '재정적 자유를 얻고 사회적 영향력을 확대할 수 있습니다.'",
            "purpose": "motivation",
        },
        {
            "order": 6,
            "question_text": "이 문제를 해결하는 데 가장 중요하게 생각하는 요소는 무엇인가요?",
            "question_description": "우선순위를 한 문장으로 작성하면 AI가 핵심 포인트 중심의 솔루션을 구성할 수 있습니다.",
            "question_hint": "예: '사용자 경험과 비용 효율성을 최우선으로 고려합니다.'",
            "purpose": "motivation",
        },
        {
            "order": 7,
            "question_text": "이 창업에서 반드시 지켜야 하는 조건이나 피해야 할 사항이 있나요?",
            "question_description": "AI가 현실적이고 안전한 제안을 만들도록, 반드시 지켜야 할 제약 조건을 한 문장으로 작성해주세요.",
            "question_hint": "예: '법적 제한과 브랜드 이미지를 유지해야 합니다.'",
            "purpose": "constraint",
        },
        {
            "order": 8,
            "question_text": "이 목표를 달성하고 싶은 시간 범위는 언제까지인가요?",
            "question_description": "마감이나 단계 목표를 한 문장으로 작성하면 AI가 단계별 계획을 생성할 수 있습니다.",
            "question_hint": "예: '3개월 내 MVP 출시, 6개월 내 고객 1000명 확보를 목표로 합니다.'",
            "purpose": "constraint",
        },
        {
            "order": 9,
            "question_text": "AI가 제안할 솔루션이나 문서는 어떤 스타일/톤이면 좋나요?",
            "question_description": "원하는 스타일이나 톤을 한 문장으로 작성하면 AI가 결과물을 해당 스타일로 생성할 수 있습니다.",
            "question_hint": "예: '간결한 보고서 형식, 단계별 계획, 발표용 슬라이드 요약을 원합니다.'",
            "purpose": "constraint",
        },
        {
            "order": 10,
            "question_text": "AI가 참고해야 할 자료나 이미 갖고 있는 정보가 있나요?",
            "question_description": "사용자가 제공하는 기존 자료나 배경 정보를 한 문장으로 작성하면 AI Prompt가 더 정확하고 개인화된 결과물을 생성할 수 있습니다.",
            "question_hint": "예: '기존 시장 조사 데이터와 경쟁사 정보, 고객 피드백을 포함합니다.'",
            "purpose": "context",
        },
    ]

    for row in COMMON:
        Question.objects.update_or_create(
            category=common,
            order=row["order"],
            defaults={
                "question_text": row["question_text"],
                "question_description": row["question_description"],
                "question_hint": row["question_hint"],
                "purpose": row["purpose"],
            },
        )

    for row in STARTUP:
        Question.objects.update_or_create(
            category=startup,
            order=row["order"],
            defaults={
                "question_text": row["question_text"],
                "question_description": row["question_description"],
                "question_hint": row["question_hint"],
                "purpose": row["purpose"],
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0009_question_purpose"),
    ]

    operations = [
        migrations.RunPython(ensure_seed, noop_reverse),
    ]
