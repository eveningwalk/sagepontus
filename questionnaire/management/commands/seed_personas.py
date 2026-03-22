import os, json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from questionnaire.models import Category, Question, Answer

class Command(BaseCommand):
    help = 'management/questions/ 디렉토리의 JSON 파일을 기반으로 질문과 페르소나 답변을 등록합니다.'

    def handle(self, *args, **kwargs):
        # 사용자 생성
        minjun, _ = User.objects.get_or_create(username='minjun')
        sua, _ = User.objects.get_or_create(username='sua')

        # 질문 디렉토리 경로 설정
        base_path = os.path.join(os.path.dirname(__file__), '..', 'questions')
        file_list = [f for f in os.listdir(base_path) if f.endswith('.json')]

        # 페르소나 답변 사전
        persona_answers = {
            'minjun': {
                'common': [
                    "고객 유입이 부족하다",
                    "업무 집중도가 떨어진다",
                    "SNS 운영을 강화해봤다",
                    "지속성이 부족했다",
                    "작업 효율이 높아질 것이다"
                ],
                'solo_founder': [
                    "반복 업무가 많다",
                    "신뢰와 전문성을 전달하고 싶다",
                    "콘텐츠 제작에 가장 많은 시간을 쓴다",
                    "마케팅에서 도움이 필요하다",
                    "월 매출 500만 원을 달성하고 싶다"
                ]
            },
            'sua': {
                'common': [
                    "팀 내 역할이 모호하다",
                    "협업이 지연된다",
                    "역할을 재조정해봤다",
                    "이해관계가 충돌했다",
                    "협업이 원활해질 것이다"
                ],
                'pm': [
                    "외주 일정이 불확실하다",
                    "우선순위가 혼란스럽다",
                    "승인 지연이 있다",
                    "클라이언트와 이메일로 소통 중이다",
                    "기능 테스트 완료가 필요하다"
                ]
            }
        }

        # 파일별 질문 등록 및 답변 연결
        for file_name in file_list:
            category_name, _ = os.path.splitext(file_name)
            file_path = os.path.join(base_path, file_name)

            with open(file_path, encoding='utf-8') as f:
                questions = json.load(f)

            category, _ = Category.objects.get_or_create(name=category_name)

            for idx, q in enumerate(questions):
                question, _ = Question.objects.get_or_create(
                    question_text=q['question_text'],
                    defaults={
                        'order': q.get('order', idx + 1),
                        'question_description': q.get('description', ''),
                        'question_hint': q.get('hint', ''),
                        'category': category
                    }
                )

                # 민준 답변 등록
                if category_name in persona_answers['minjun']:
                    try:
                        answer_text = persona_answers['minjun'][category_name][idx]
                        Answer.objects.get_or_create(
                            user=minjun,
                            question=question,
                            defaults={'answer_text': answer_text}
                        )
                    except IndexError:
                        pass  # 질문 수와 답변 수가 다를 경우 무시

                # 수아 답변 등록
                if category_name in persona_answers['sua']:
                    try:
                        answer_text = persona_answers['sua'][category_name][idx]
                        Answer.objects.get_or_create(
                            user=sua,
                            question=question,
                            defaults={'answer_text': answer_text}
                        )
                    except IndexError:
                        pass

            self.stdout.write(self.style.SUCCESS(f"✅ {category_name} 질문 및 페르소나 답변 등록 완료"))

        self.stdout.write(self.style.SUCCESS("🎉 전체 질문과 페르소나 응답 등록이 완료되었습니다."))