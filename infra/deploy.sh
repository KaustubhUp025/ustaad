#!/usr/bin/env bash
# Deploy the API to Cloud Run. Prefer: make deploy-dev / make deploy-demo.
#   ENV=dev  → service ustaad-api-dev, min 0, Firestore (default)
#   ENV=demo → service ustaad-api,     min 1, Firestore demo   (A only, from a git tag)
# Required env: PROJECT_ID, LIVE_MODEL, MEDIA_BUCKET, ALLOWED_ORIGINS (comma-separated is fine)
set -euo pipefail
ENV="${ENV:-dev}"
: "${PROJECT_ID:?}" "${LIVE_MODEL:?set after the T05 smoke test}" "${MEDIA_BUCKET:?}" "${ALLOWED_ORIGINS:?}"
REGION="${REGION:-asia-south1}"
SERVICE="ustaad-api-dev"; MIN=0; DB="(default)"; DEMO_SAFE=0
if [[ "$ENV" == "demo" ]]; then SERVICE="ustaad-api"; MIN="${MIN_INSTANCES:-1}"; DB="demo"; DEMO_SAFE=1; fi

# '^@^' makes '@' the separator, so commas inside ALLOWED_ORIGINS survive
ENVVARS="^@^GOOGLE_CLOUD_PROJECT=${PROJECT_ID}@GOOGLE_CLOUD_LOCATION=global@GOOGLE_GENAI_USE_ENTERPRISE=TRUE@GOOGLE_GENAI_USE_VERTEXAI=TRUE"
ENVVARS+="@FIRESTORE_DB=${DB}@FLASH_MODEL=${FLASH_MODEL:-gemini-3.8-flash}@LIVE_MODEL=${LIVE_MODEL}"
ENVVARS+="@TTS_MODEL=${TTS_MODEL:-gemini-3.8-flash-tts}@EMBED_MODEL=${EMBED_MODEL:-gemini-embedding-001}@EMBED_DIM=768"
ENVVARS+="@TRANSCRIBE_MODEL=${TRANSCRIBE_MODEL:-}@MEDIA_BUCKET=${MEDIA_BUCKET}@AGENT_ENGINE_ID=${AGENT_ENGINE_ID:-}"
ENVVARS+="@LIVE_LOCATION=${LIVE_LOCATION:-us-central1}@EMBED_LOCATION=${EMBED_LOCATION:-asia-south1}@AGENT_SEARCH_DATASTORE=${AGENT_SEARCH_DATASTORE:-}@ALLOWED_ORIGINS=${ALLOWED_ORIGINS}"
ENVVARS+="@DEMO_SAFE=${DEMO_SAFE}"

# 1 GiB: at 512 MiB the demo service was killed on its first Live session (513 MiB used, Oct 18, rev 00002).
gcloud run deploy "$SERVICE" \
  --project "$PROJECT_ID" \
  --source backend \
  --region "$REGION" \
  --service-account "ustaad-run@${PROJECT_ID}.iam.gserviceaccount.com" \
  --timeout 3600 \
  --session-affinity \
  --min-instances "$MIN" \
  --max-instances 4 \
  --memory 1Gi \
  --allow-unauthenticated \
  --set-env-vars "$ENVVARS" \
  --set-secrets "TG_BOT_TOKEN=tg-bot-token:latest,TG_WEBHOOK_SECRET=tg-webhook-secret:latest,PLACES_API_KEY=places-api-key:latest,SESSION_SECRET=session-secret:latest"
