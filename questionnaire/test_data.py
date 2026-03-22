# test_data.py
# 실행 방법: python manage.py shell < test_data.py

from questionnaire.models import Category, Step, Question, Answer

# --- Category ---
cat1 = Category.objects.create(name="온라인 마케팅")

# --- Steps ---
step1 = Step.objects.create(category=cat1, name="시장 조사", order=1)
step2 = Step.objects.create(category=cat1, name="상품 분석", order=2)

# --- Step 1 Questions ---
q1 = Question.objects.create(step=step1, text="경쟁사 분석을 진행하셨나요?", order=1)
q2 = Question.objects.create(step=step1, text="목표 고객을 정의하셨나요?", order=2)

# --- Step 2 Questions ---
q3 = Question.objects.create(step=step2, text="상품 특징을 정리하셨나요?", order=1)
q4 = Question.objects.create(step=step2, text="가격 전략을 결정하셨나요?", order=2)

# --- Answers ---
# Step 1
Answer.objects.create(question=q1, text="예", next_question=q2, order=1)
Answer.objects.create(question=q1, text="아니오", next_question=q2, order=2)
Answer.objects.create(question=q2, text="예", next_question=q3, order=1)
Answer.objects.create(question=q2, text="아니오", next_question=q3, order=2)

# Step 2
Answer.objects.create(question=q3, text="예", next_question=q4, order=1)
Answer.objects.create(question=q3, text="아니오", next_question=q4, order=2)
Answer.objects.create(question=q4, text="예", next_question=None, order=1)
Answer.objects.create(question=q4, text="아니오", next_question=None, order=2)

print("Animamus 테스트 데이터가 정상적으로 생성되었습니다.")
