#!/usr/bin/env bash
# Budget alerts at ₹500, ₹2,000 and ₹5,000 (spec §5). Amount currency must match the billing account.
set -euo pipefail
: "${BILLING_ACCOUNT:?set BILLING_ACCOUNT}"
: "${PROJECT_ID:?set PROJECT_ID}"
for AMOUNT in 500 2000 5000; do
  gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT" \
    --display-name="ustaad-${AMOUNT}" \
    --budget-amount="${AMOUNT}INR" \
    --filter-projects="projects/${PROJECT_ID}" \
    --threshold-rule=percent=0.9 \
    --threshold-rule=percent=1.0
done
