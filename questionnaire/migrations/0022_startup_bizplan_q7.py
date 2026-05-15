# startup_bizplan Q7 추가: 어떤 결과물을 원하시나요?
from django.db import migrations


def add_q7(apps, schema_editor):
    Category = apps.get_model("questionnaire", "Category")
    Question = apps.get_model("questionnaire", "Question")

    cat = Category.objects.filter(name="startup_bizplan").first()
    if not cat:
        return

    Question.objects.update_or_create(
        category=cat,
        order=7,
        defaults={
            "question_text": "어떤 결과물을 원하시나요?",
            "question_description": "AI가 생성할 프롬프트의 목적을 구체적으로 알려주세요. 원하는 결과물의 형태와 분량을 작성해주세요.",
            "question_hint": "예: '전체 사업계획서 초안 (A4 5장 분량)' / '1페이지 요약본' / '투자자용 피치 스크립트' / '문제 정의 섹션만 상세히'",
            "purpose": "constraint",
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0021_startup_bizplan"),
    ]

    operations = [
        migrations.RunPython(add_q7, noop_reverse),
    ]
