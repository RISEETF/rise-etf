#!/usr/bin/env bash
# Push only the collector's isolated commit; preserve unrelated concurrent work.
set -euo pipefail
collection_base=${1:?collector checkout commit required}
if [ "$(git rev-list --count "$collection_base"..HEAD)" != "1" ]; then
  echo 'Expected exactly one collection commit' >&2
  exit 1
fi
if git diff --quiet "$collection_base" HEAD; then
  echo 'Empty collector commit' >&2
  exit 1
fi
while IFS= read -r collection_path; do
  case "$collection_path" in
    data/gclri/latest.json|data/gclri/history.json) ;;
    *) echo 'Collector commit contains unrelated files' >&2; exit 1 ;;
  esac
done < <(git diff --name-only "$collection_base" HEAD)
for push_attempt in 1 2 3; do
  if git push origin HEAD:main; then exit 0; fi
  if [ "$push_attempt" = 3 ]; then break; fi
  git fetch origin main:refs/remotes/origin/main
  if ! git diff --quiet "$collection_base" origin/main -- \
       data/gclri scripts/collect_gclri_market.py scripts/push_gclri_commit.sh \
       .github/workflows/gclri_market_update.yml; then
    echo 'Collector inputs, code or outputs changed upstream; rerun collection' >&2
    exit 1
  fi
  # Only unrelated files changed remotely. No force-push and no report rebase.
  git rebase origin/main
done
exit 1
