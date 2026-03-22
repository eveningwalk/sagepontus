import os
import json
from django.core.management.base import BaseCommand
from questionnaire.models import Category, Question  # 실제 모델 경로 맞게 수정

class Command(BaseCommand):
    help = 'questions 디렉토리의 JSON 파일을 읽어 질문을 DB에 등록합니다.'

    def handle(self, *args, **kwargs):
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'questions')
        print("\nJson directory path : ", base_path)
        
        # 디렉토리 존재 여부 확인
        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR("❌ questions 디렉토리가 존재하지 않습니다."))
            return

        # JSON 파일 목록 필터링
        file_list = [
            f for f in os.listdir(base_path)
            if f.endswith('.json') and not f.startswith('.') and f != '.ipynb_checkpoints'
        ]

        if not file_list:
            self.stdout.write(self.style.WARNING("⚠️ questions 디렉토리에 등록할 JSON 파일이 없습니다."))
            return

        for file_name in file_list:
            json_path = os.path.join(base_path, file_name)
            self.stdout.write(self.style.NOTICE(f"📂 {file_name} 처리 시작..."))

            # JSON 읽기
            try:
                with open(json_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"❌ JSON 파싱 오류: {file_name}, {str(e)}"))
                continue

            # category와 questions 가져오기
            if isinstance(data, dict) and 'questions' in data:
                category_name = data.get('category', 'common')
                questions = data['questions']
            elif isinstance(data, list):
                # 리스트로 바로 들어온 경우, 파일명에서 category 추출
                category_name = os.path.splitext(file_name)[0].split('_')[-1]
                questions = data
            else:
                self.stdout.write(self.style.ERROR(f"❌ {file_name}에서 questions 데이터를 찾을 수 없습니다."))
                continue

            # Category 존재 확인
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"⚠️ Category '{category_name}'가 존재하지 않아 생략됨"))
                continue

            # questions 등록
            for item in questions:
                if not isinstance(item, dict):
                    self.stdout.write(self.style.ERROR(f"❌ {file_name}에서 item이 dict가 아닙니다: {item}"))
                    continue

                # 중복 order 체크 및 생성/업데이트
                try:
                    q, created = Question.objects.update_or_create(
                        category=category,
                        order=item.get('order', 0),
                        defaults={
                            'question_text': item.get('question_text', ''),
                            'question_description': item.get('description', ''),
                            'question_hint': item.get('hint', ''),
                            'purpose': item.get('purpose', 'context'),  # 🔹 추가
                        }
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ {file_name}에서 질문 등록 실패: {e}"))
                    continue

            self.stdout.write(self.style.SUCCESS(f"✅ '{category_name}' 질문 등록 완료 (from {file_name})"))

        self.stdout.write(self.style.SUCCESS("🎉 모든 JSON 파일 처리 완료"))
