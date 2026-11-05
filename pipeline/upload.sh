#!/usr/bin/env bash
# Upload a work dir (raw HTML + pipeline outputs + built site data + photos) to the private GCS bucket.
# Usage: pipeline/upload.sh YYYYMMDD WORKDIR
#   WORKDIR layout: raw/YYYYMMDD/..., *.json, activity*.jsonl, data/*.json, photos/
# After this succeeds and pipeline/deploy.sh is done, delete WORKDIR (nothing is kept in the repo).
set -euo pipefail
DATE="${1:?YYYYMMDD}"
WORK="${2:?WORKDIR}"
BUCKET="gs://politics-os-data-2026"
ACCOUNT="${POS_GCS_ACCOUNT:-}"   # gcloud account (default: the active one)
ACCT=(); [ -n "$ACCOUNT" ] && ACCT=(--account="$ACCOUNT")
cp1() { gcloud storage cp "$1" "$2" ${ACCT[@]+"${ACCT[@]}"} --quiet; }
cpdir() { gcloud storage cp -r "$1" "$2" ${ACCT[@]+"${ACCT[@]}"} --quiet; }  # one directory -> one destination

# raw HTML (top-level files, then each sub-directory such as gian/ sanvote/ sangian/)
if [ -d "$WORK/raw/$DATE" ]; then
  for f in "$WORK"/raw/"$DATE"/*; do
    if [ -d "$f" ]; then cpdir "$f" "$BUCKET/v1/raw/$DATE/"; else cp1 "$f" "$BUCKET/v1/raw/$DATE/$(basename "$f")"; fi
  done
fi

# pipeline snapshots
if ls "$WORK"/speeches*.jsonl >/dev/null 2>&1; then cat "$WORK"/speeches*.jsonl > "$WORK/.speeches_merged" && cp1 "$WORK/.speeches_merged" "$BUCKET/v1/snapshots/$DATE/speeches.jsonl" && rm "$WORK/.speeches_merged"; fi
cat "$WORK"/activity*.jsonl > "$WORK/.activity_merged" && cp1 "$WORK/.activity_merged" "$BUCKET/v1/snapshots/$DATE/activity.jsonl" && rm "$WORK/.activity_merged"
for f in roster.json bills_shu.json bills_shu_old.json san_bills.json san_votes_all.json transparency.json \
         party_pledges.json photos.json zero_check.json last_speech.json meetings.jsonl questions.json cabinet.json x_reactions.jsonl pledges_personal_raw.jsonl pledges_spec.jsonl progress.jsonl; do
  if [ -f "$WORK/$f" ]; then cp1 "$WORK/$f" "$BUCKET/v1/snapshots/$DATE/$f"; fi
done

# built site data (snapshot + latest = what pipeline/deploy.sh serves)
for f in members.json meta.json records.json pledges.json japan-map.json speeches.json x_reactions.json pledges_personal.json party_finance.json pledges_progress.json; do
  [ -f "$WORK/data/$f" ] || continue
  cp1 "$WORK/data/$f" "$BUCKET/v1/snapshots/$DATE/$f"
  cp1 "$WORK/data/$f" "$BUCKET/v1/$f"
done
if [ -d "$WORK/photos" ]; then
  cpdir "$WORK/photos" "$BUCKET/v1/snapshots/$DATE/"
  cpdir "$WORK/photos" "$BUCKET/v1/"
fi
gcloud storage ls -l "$BUCKET/v1/snapshots/$DATE/**" ${ACCT[@]+"${ACCT[@]}"} | tail -3

# Verify every local file reached GCS with the same size, then delete the work dir (CLEAN=1, default).
# The work dir is only removed when it is a temp dir created by pull.sh (name politics-os.XXXXXX) and all sizes match.
if [ "${CLEAN:-1}" = 1 ]; then
  python3 -I - "$WORK" "$BUCKET" "$DATE" "$ACCOUNT" <<'PY'
import shutil, subprocess, sys
from pathlib import Path
work, bucket, date, acct = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3], sys.argv[4]
def sizes(prefix):
    out = subprocess.run(["gcloud", "storage", "ls", "-l", "-r", prefix, *([f"--account={acct}"] if acct else [])], capture_output=True, text=True).stdout
    return {p[-1]: int(p[0]) for p in (l.split() for l in out.splitlines()) if len(p) >= 3 and p[0].isdigit() and p[-1].startswith("gs://")}
remote = {**sizes(f"{bucket}/v1/snapshots/{date}/"), **sizes(f"{bucket}/v1/raw/{date}/")}
bad = []
for f in work.rglob("*"):
    if not f.is_file() or f.name.startswith("."):
        continue
    rel = f.relative_to(work).as_posix()
    if rel.startswith(f"raw/{date}/"):
        key = f"{bucket}/v1/raw/{date}/" + rel[len(f"raw/{date}/"):]
    elif rel.startswith("data/") or rel.startswith("photos/"):
        key = f"{bucket}/v1/snapshots/{date}/" + rel.split("/", 1)[1] if rel.startswith("data/") else f"{bucket}/v1/snapshots/{date}/{rel}"
    elif rel.startswith("activity") or rel.startswith("speeches_") or rel.startswith("fonts/") or rel in ("index.html", "app.js", "styles.css", "robots.txt"):
        continue  # merged into one snapshot file / kept elsewhere / code
    else:
        key = f"{bucket}/v1/snapshots/{date}/{rel}"
    if remote.get(key) != f.stat().st_size:
        bad.append(rel)
if bad:
    print("NOT cleaned: size mismatch or missing in GCS ->", bad[:10], f"({len(bad)} files)")
    sys.exit(1)
if not work.name.startswith("politics-os."):
    print("NOT cleaned: not a pull.sh temp dir ->", work)
    sys.exit(0)
shutil.rmtree(work)
print("verified in GCS and removed local work dir:", work)
PY
fi
