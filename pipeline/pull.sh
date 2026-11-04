#!/usr/bin/env bash
# Pull a dated snapshot from GCS into a temporary work dir (data never lives in the repo).
# Usage: WORK=$(pipeline/pull.sh YYYYMMDD)   (prints the work dir; remove it when done: rm -r "$WORK")
#        pipeline/pull.sh YYYYMMDD /path/to/workdir
# Layout of WORK: *.json, activity.jsonl, data/, photos/, fonts/, raw/ (raw only with PULL_RAW=1)
set -euo pipefail
DATE="${1:?YYYYMMDD}"
WORK="${2:-$(mktemp -d "${TMPDIR:-/tmp}/politics-os.XXXXXX")}"
SRC="gs://politics-os-data-2026/v1/snapshots/$DATE"
A=(--quiet); [ -n "${POS_GCS_ACCOUNT:-}" ] && A+=(--account="$POS_GCS_ACCOUNT")  # gcloud account (default: the active one)
mkdir -p "$WORK/data"
for f in roster.json activity.jsonl speeches.jsonl bills_shu.json bills_shu_old.json san_bills.json san_votes_all.json \
         transparency.json party_pledges.json photos.json zero_check.json last_speech.json meetings.jsonl questions.json cabinet.json x_reactions.jsonl pledges_personal_raw.jsonl pledges_spec.jsonl; do
  gcloud storage cp "$SRC/$f" "$WORK/$f" "${A[@]}" >&2 || echo "missing $f" >&2
done
for f in members.json meta.json records.json pledges.json japan-map.json speeches.json x_reactions.json pledges_personal.json party_finance.json; do
  gcloud storage cp "$SRC/$f" "$WORK/data/$f" "${A[@]}" >&2 || echo "missing data/$f" >&2
done
gcloud storage cp -r "$SRC/photos" "$WORK/" "${A[@]}" >&2
gcloud storage cp -r "gs://politics-os-data-2026/v1/fonts" "$WORK/" "${A[@]}" >&2   # for local preview
if [ "${PULL_RAW:-0}" = 1 ]; then
  mkdir -p "$WORK/raw" && gcloud storage cp -r "gs://politics-os-data-2026/v1/raw/$DATE" "$WORK/raw/" "${A[@]}" >&2
fi
echo "$WORK"
