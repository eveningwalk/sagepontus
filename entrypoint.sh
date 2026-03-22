#!/bin/sh
set -e
cd /app
# Cloud Run: DATABASE_URL(Supabase) 없으면 로컬 SQLite — 컨테이너 기동 시 스키마 생성
python manage.py migrate --noinput
exec gunicorn animamus_project.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 1 \
  --timeout 120
