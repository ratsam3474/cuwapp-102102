#!/bin/bash

# Deploy script for Google Cloud Run

PROJECT_ID="lucky-era-469001-d0"
REGION="us-central1"

echo "Deploying to Google Cloud Run..."

# 1. Deploy Landing Page
echo "Building and deploying landing page..."
cd 10210-landing
gcloud run deploy cuwhapp-landing \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --port 5500 \
  --memory 512Mi

# 2. Deploy Auth Service
echo "Building and deploying auth service..."
cd ../10210-auth
gcloud run deploy cuwhapp-auth \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --port 5502 \
  --memory 512Mi \
  --set-env-vars "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_bm9ybWFsLWNhcmlib3UtMzUuY2xlcmsuYWNjb3VudHMuZGV2JA,CLERK_SECRET_KEY=sk_test_jgzleAHcvFNnkeSsuMuKMjv9slQVgb3NTchskjMZLX"

# 3. Deploy Main API
echo "Building and deploying main API..."
cd ../10210-api
gcloud run deploy cuwhapp-api \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --set-env-vars "DO_CONTAINER_FUNCTION_URL=https://container-manager-337193391523.us-central1.run.app/,CLERK_SECRET_KEY=sk_test_jgzleAHcvFNnkeSsuMuKMjv9slQVgb3NTchskjMZLX"

echo "Deployment complete!"
echo "Landing: https://cuwhapp-landing-*.run.app"
echo "Auth: https://cuwhapp-auth-*.run.app"
echo "API: https://cuwhapp-api-*.run.app"