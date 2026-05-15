# startup_bizplan 카테고리 + Q1~Q6 질문 생성
from django.db import migrations


def ensure_startup_bizplan(apps, schema_editor):
    Category = apps.get_model("questionnaire", "Category")
    Question = apps.get_model("questionnaire", "Question")

    cat, _ = Category.objects.get_or_create(
        name="startup_bizplan",
        defaults={"description": "모두의 창업 사업계획서"},
    )

    QUESTIONS = [
        {
            "order": 1,
            "question_text": "나의 아이디어를 한 줄로 소개해주세요.",
            "question_description": "서비스/제품의 핵심을 한 문장으로 압축해주세요.",
            "question_hint": "예: 'AI로 병원 예약 대기 시간을 줄여주는 중소병원 전용 서비스'",
            "purpose": "context",
        },
        {
            "order": 2,
            "question_text": "아이디어를 떠올린 배경 이야기를 들려주세요.",
            "question_description": "어떤 경험이나 문제 의식에서 출발했는지 자유롭게 서술해주세요.",
            "question_hint": "예: '직접 겪은 불편함, 주변에서 목격한 문제, 또는 시장 공백을 발견한 계기'",
            "purpose": "motivation",
        },
        {
            "order": 3,
            "question_text": "아이디어는 누구의 어떤 문제를 해결해주나요?",
            "question_description": "타겟 고객과 그들이 겪는 핵심 문제를 구체적으로 작성해주세요.",
            "question_hint": "예: '중소 병원 원무과 직원 — 수기 예약 관리로 인한 오버부킹과 노쇼 문제'",
            "purpose": "context",
        },
        {
            "order": 4,
            "question_text": "아이디어를 어떻게 실현하고 싶으신가요?",
            "question_description": "솔루션의 핵심 방식과 실행 계획을 작성해주세요.",
            "question_hint": "예: 'AI 예약 최적화 SaaS — 3개월 내 MVP, 파일럿 병원 3곳 확보 후 확장'",
            "purpose": "context",
        },
        {
            "order": 5,
            "question_text": "사업계획서의 주요 독자는 누구인가요?",
            "question_description": "누가 이 계획서를 읽을지 알면 AI가 톤과 강조점을 맞출 수 있습니다.",
            "question_hint": "예: '공모전 심사위원 / 초기 투자자(엔젤) / 정부 지원사업 담당자'",
            "purpose": "constraint",
        },
        {
            "order": 6,
            "question_text": "특별히 강조하고 싶은 강점이나 차별점이 있나요?",
            "question_description": "경쟁사 대비 우위, 팀 역량, 보유 기술 등 부각하고 싶은 요소를 작성해주세요.",
            "question_hint": "예: '공동창업자의 병원 IT 10년 경력, 국내 유일 중소병원 특화 솔루션'",
            "purpose": "motivation",
        },
    ]

    for row in QUESTIONS:
        Question.objects.update_or_create(
            category=cat,
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
        ("questionnaire", "0020_add_vertical_profile_block_type"),
    ]

    operations = [
        migrations.RunPython(ensure_startup_bizplan, noop_reverse),
    ]
