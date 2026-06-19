#!/bin/bash
IMAGE="us-east4-docker.pkg.dev/gen-lang-client-0496146114/cloud-run-source-deploy/eveningwalk-sagepontus/sagepontus@sha256:f98923421312db0972913965d2d67a43df062971e90b6be7171707a036395128"
REGION="us-east4"
PROJECT="gen-lang-client-0496146114"

gcloud run jobs create create-admin \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --env-vars-file tmp_envvars.yaml \
  --command python \
  --args "manage.py,createsuperuser,--noinput"

gcloud run jobs execute create-admin \
  --region "$REGION" \
  --project "$PROJECT"
