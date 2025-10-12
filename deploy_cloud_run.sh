#!/bin/bash
# Deploy ADK Web UI to Cloud Run with OAuth for end users

set -e

PROJECT_ID="escribania-mastropasqua"
REGION="us-central1"
SERVICE_NAME="adk-rag-agent-ui"

echo "🚀 Deploying ADK Web UI to Cloud Run..."
echo "📦 Project: $PROJECT_ID"
echo "📍 Region: $REGION"
echo ""

# Submit build to Cloud Build
echo "📦 Building and deploying with Cloud Build..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=$PROJECT_ID \
  --region=$REGION

echo ""
echo "========================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================================================"
echo ""
echo "🌐 Your ADK Web UI is now available at:"
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)"

echo ""
echo "🔐 OAuth Login Configuration:"
echo "   Add this redirect URI to your OAuth client:"
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)" | sed 's/$/\/oauth2callback/'

echo ""
echo "========================================================================"
