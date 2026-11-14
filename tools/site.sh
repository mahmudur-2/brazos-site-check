#!/usr/bin/env bash
# Sets BASE for the later steps: the live site, or this repo's dist/ served on the Mac (base=local).
set -euo pipefail
if [ "$BASE_INPUT" = local ]; then
  [ -d dist ] || { echo "base=local needs a dist/ folder in the repo"; exit 1; }
  nohup node serve.mjs dist 8790 > serve.log 2>&1 &
  for _ in $(seq 30); do curl -fsS -o /dev/null http://localhost:8790/ && break; sleep 1; done
  curl -fsS -o /dev/null http://localhost:8790/
  echo "BASE=http://localhost:8790" >> "$GITHUB_ENV"
else
  [[ "$BASE_INPUT" =~ ^https?://[A-Za-z0-9.:-]+/?$ ]] || { echo "base: a site origin like https://example.com, or local"; exit 1; }
  echo "BASE=${BASE_INPUT%/}" >> "$GITHUB_ENV"
fi
