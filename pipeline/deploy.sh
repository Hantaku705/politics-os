#!/usr/bin/env bash
# Deploy: uploads CODE ONLY (a few KB). Vercel's build step (build/fetch-data.mjs) pulls data, photos and fonts
# straight from gs://politics-os-data-2026/v1/ using the read-only service account in env GCS_SA_KEY_B64.
# Nothing is downloaded to this machine.
# Usage: pipeline/deploy.sh            -> production
#        pipeline/deploy.sh preview    -> preview URL (use this instead of a local server)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-prod}" = "preview" ]; then
  vercel deploy --yes --scope hantakus-projects
else
  vercel deploy --prod --yes --scope hantakus-projects
fi
