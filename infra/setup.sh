#!/usr/bin/env bash
# One-time GCP + Firebase setup for Ustaad (task T03, owner B). Safe to re-run: each step checks before creating.
# Prereq: the GCP project exists (create it in the console or: gcloud projects create $PROJECT_ID).
# Usage: PROJECT_ID=ustaad-abc BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX ./infra/setup.sh
# Budgets are separate: ./infra/budgets.sh
set -euo pipefail
: "${PROJECT_ID:?set PROJECT_ID}"
: "${BILLING_ACCOUNT:?set BILLING_ACCOUNT}"
REGION="${REGION:-asia-south1}"
BUCKET="${BUCKET:-${PROJECT_ID}-media}"
RUN_SA="ustaad-run@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT_ID"
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"

gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com storage.googleapis.com secretmanager.googleapis.com \
  aiplatform.googleapis.com discoveryengine.googleapis.com places.googleapis.com \
  cloudscheduler.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com \
  billingbudgets.googleapis.com iam.googleapis.com

# Firestore: (default) for dev, "demo" for the judged deployment
for DB in "(default)" demo; do
  if ! gcloud firestore databases describe --database="$DB" >/dev/null 2>&1; then
    gcloud firestore databases create --database="$DB" --location="$REGION" --type=firestore-native
  fi
done

# Media bucket (photos, clips, WhatsApp imports)
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" --uniform-bucket-level-access
fi
gcloud storage buckets update "gs://${BUCKET}" --cors-file=infra/storage-cors.json

# Runtime service account for Cloud Run service + jobs, with only what it needs
if ! gcloud iam service-accounts describe "$RUN_SA" >/dev/null 2>&1; then
  gcloud iam service-accounts create ustaad-run --display-name="Ustaad Cloud Run runtime"
fi
for ROLE in roles/aiplatform.user roles/datastore.user roles/secretmanager.secretAccessor \
            roles/discoveryengine.user roles/run.invoker; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${RUN_SA}" --role="$ROLE" \
    --condition=None --quiet >/dev/null
done
# Signed upload URLs (POST /api/media/upload-url) need the SA to sign as itself
gcloud iam service-accounts add-iam-policy-binding "$RUN_SA" \
  --member="serviceAccount:${RUN_SA}" --role=roles/iam.serviceAccountTokenCreator >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RUN_SA}" --role=roles/storage.objectAdmin >/dev/null

# Secrets with a placeholder version so the first deploy works; replace values in T06:
#   printf '%s' "$VALUE" | gcloud secrets versions add wa-token --data-file=-
for s in wa-token wa-verify-token wa-app-secret places-api-key; do
  if ! gcloud secrets describe "$s" >/dev/null 2>&1; then
    gcloud secrets create "$s" --replication-policy=automatic
    printf 'placeholder' | gcloud secrets versions add "$s" --data-file=-
  fi
done

# Signs demo session tokens (POST /api/demo/session, T27): a random value, never a placeholder.
if ! gcloud secrets describe session-secret >/dev/null 2>&1; then
  gcloud secrets create session-secret --replication-policy=automatic
  openssl rand -base64 32 | tr -d '\n' | gcloud secrets versions add session-secret --data-file=-
fi

# Firebase on the same project (Hosting)
firebase projects:addfirebase "$PROJECT_ID" || echo "Firebase already enabled on ${PROJECT_ID}"

sed -i.bak "s/REPLACE_WITH_PROJECT_ID/${PROJECT_ID}/" .firebaserc && rm -f .firebaserc.bak
echo "Done. Next: ./infra/firestore.sh && ./infra/budgets.sh && make agent-engine"
