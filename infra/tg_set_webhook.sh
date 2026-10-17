#!/usr/bin/env bash
# Points the quotes bot at a Cloud Run service's POST /webhook/telegram, with the secret Telegram sends back in
# X-Telegram-Bot-Api-Secret-Token. ENV=dev (default) → ustaad-api-dev, ENV=demo → ustaad-api. Seed vendors first
# (infra/tg_chat_ids.py): getUpdates stops working once a webhook is set.
set -euo pipefail
: "${PROJECT_ID:?}"
REGION="${REGION:-asia-south1}"
SERVICE="ustaad-api-dev"; [[ "${ENV:-dev}" == "demo" ]] && SERVICE="ustaad-api"

URL=$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)')
TOKEN=$(gcloud secrets versions access latest --project "$PROJECT_ID" --secret tg-bot-token)
SECRET=$(gcloud secrets versions access latest --project "$PROJECT_ID" --secret tg-webhook-secret)

curl -fsS "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  --data-urlencode "url=${URL}/webhook/telegram" \
  --data-urlencode "secret_token=${SECRET}" \
  --data-urlencode 'allowed_updates=["message","callback_query"]'
echo
curl -fsS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
echo
