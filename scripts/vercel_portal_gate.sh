#!/bin/sh
# Vercel: 0 skips, 1 builds. Preview policy stays unchanged.
[ "${VERCEL_ENV:-}" = production ] || exit 1
[ "${VERCEL_GIT_COMMIT_REF:-}" = main ] || exit 1
base=${VERCEL_GIT_PREVIOUS_SHA:-HEAD^1}
git rev-parse --verify --quiet "$base^{commit}" >/dev/null || exit 1
# Unknown or mixed changes must build. Compare to last deployed tree if available.
git diff --quiet "$base" HEAD -- data/operations/portal-release-day.txt || exit 1
git diff --quiet "$base" HEAD -- . ':(exclude)data/**' || exit 1
exit 0
