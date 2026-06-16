#!/bin/sh
set -e
cd /app
# Cloud Run: DATABASE_URL(Supabase) 없으면 로컬 SQLite — 컨테이너 기동 시 스키마 생성
python manage.py migrate --fake --noinput
python manage.py migrate --noinput
# 프로덕션에서 Category/Question 미시드 시 get_object_or_404(Category) 등 404 방지
python manage.py seed_categories
python manage.py seed_questions
python manage.py collectstatic --noinput
exec gunicorn animamus_project.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 1 \
  --timeout 300
