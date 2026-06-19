#!/usr/bin/env bash
# Metabase를 Cloud Run에 배포
# 사용법: bash scripts/deploy_metabase.sh
# 전제조건: gcloud auth login, PROJECT_ID 설정

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-northeast1"
SERVICE="sagepontus-metabase"

echo "▶ Deploying Metabase to Cloud Run (project: $PROJECT_ID)"

gcloud run deploy "$SERVICE" \
  --image metabase/metabase:latest \
  --platform managed \
  --region "$REGION" \
  --port 3000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --set-env-vars "MB_DB_TYPE=h2,MB_DB_FILE=/metabase-data/metabase.db,JAVA_TIMEZONE=America/New_York" \
  --allow-unauthenticated

echo "✅ Metabase deployed."
echo "⚠️  초기 접속 후 반드시 admin 계정 설정 및 외부 접근 제한 필요"
echo "   DB 연결: Cloud Run 콘솔 → 환경변수에 DATABASE_URL 추가"
