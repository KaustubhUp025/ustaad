#!/usr/bin/env bash
# Vector indexes for fault-card search: 768 dims (embed with output_dimensionality=768), flat; one plain and one
# with brand as a prefilter (SPEC §4, §7). Safe to re-run: each index is created independently and
# "already exists" is treated as success.
set -euo pipefail
VEC='field-path=embedding,vector-config={"dimension":"768","flat":"{}"}'

create() {  # $1 = database, remaining args = extra --field-config flags
  local db="$1"; shift
  local out
  if out=$(gcloud firestore indexes composite create --database="$db" --collection-group=fault_cards \
        --query-scope=COLLECTION "$@" --field-config="$VEC" --async 2>&1); then
    echo "created in ${db}: $*"
  elif grep -qiE "already exists|ALREADY_EXISTS" <<<"$out"; then
    echo "exists in ${db}: $*"
  else
    echo "$out" >&2; exit 1
  fi
}

for DB in "(default)" demo; do
  create "$DB"
  create "$DB" --field-config=order=ASCENDING,field-path=brand
done
echo "Check build status: gcloud firestore indexes composite list --database=demo"
