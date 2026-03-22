import json
import os
from django.core.management.base import BaseCommand
from questionnaire.models.models import Category

class Command(BaseCommand):
    help = 'categories.json 파일을 기반으로 카테고리를 자동 등록합니다.'

    def handle(self, *args, **options):
        # categories.json 파일 경로 설정
        base_dir = os.path.dirname(os.path.abspath(__file__))
        #file_path = os.path.join(base_dir, '..', '..', '..', 'categories.json')
        file_path = os.path.join(base_dir, '..', 'categories.json')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'파일을 찾을 수 없습니다: {file_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('JSON 파일 형식이 잘못되었습니다.'))
            return

        for name in categories:
            obj, created = Category.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'카테고리 생성됨: {name}'))
            else:
                self.stdout.write(self.style.WARNING(f'이미 존재함: {name}'))
