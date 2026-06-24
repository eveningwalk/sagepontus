#!/bin/bash
set -e

echo "=== Running tests ==="
python -m pytest vertical_pt/tests/ -v --tb=short

echo "=== Deploying to Cloud Run ==="
gcloud run deploy --source .
