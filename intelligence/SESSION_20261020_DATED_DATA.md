# Session checkpoint — 2026-10-20

## Verified outcome

Dated-data reporting and automated publication fixes are merged and verified in production. No further user decision was required for this change. Password/access protection remains deferred by user instruction. This is not a claim that all P2 research capabilities are complete.

Branch: main. Last observed main commit before this documentation commit: cbf03b9b4db0ebb08dbf87dd32b5ec34d3ef983b. Local worktree clean. This checkpoint supersedes the pending verification statements in DATED_DATA_HANDOFF.md.

- PR #53: FULL 1.2 dated observations; implementation a8e1f56eb4091d34622ac57da23dea6e7623e725, merge 6527c3771589f6b2c6ecbde73ebae67004349abd. CI 39343817897 and 39343817884 succeeded.
- PR #54: serialize GCLRI collection with publication and safely retry a push after unrelated remote commits; implementation 279c50ffc44ea6cde374f6eb177061f3092808dd, merge fa671458017e5ee559282c25d6fc073bc74442c4. CI 39344201627 and 39344201487 succeeded.
- PR #55: remove moving live-data dates from regression fixtures; implementation 2789b9b367c5bc680821bfb77f6b50d70367d8e4, merge cee31d2fb3a57c4bffbf01e737fd9d5d41c32c65. CI 39344504974 succeeded.

Production daily run 39344617605 succeeded and PUBLISHED the 2026-10-20 report (runtime commit 17b7a458a350fb87701571dca7134de818490639). Subsequent scheduled market collection 39350668971 and daily run 39350688392 both succeeded. The latter ran all four engines, research, report generation and publication checks with no blockers; it correctly recorded UNCHANGED instead of making a duplicate revision (runtime commit 68f9879; exact SHA available via git log). Publication archive count: 15. Today's source values were current, so dated_context is empty; delayed/all-dated scenarios are covered by tests.

Pages run 39371643138 succeeded at cbf03b9b4db0ebb08dbf87dd32b5ec34d3ef983b. On 2026-10-20, public GitHub Pages responses were fetched and matched repository bytes exactly:

- intelligence/data/latest.json SHA256 4e4b98c02b9f03cc1437f0c034b05b02003ecd4ed0e4c148e2d1bcd65726ef45
- intelligence/reports/2026-10-20.html SHA256 004e70db5409c5841f37c131f5b6d36ee24637d7e34abe49066689aed7457da1
- data/operations/intelligence.json SHA256 501e3dfa86a9d8dd09c8f4626bf9b073fe52cbe55e5ded265aac83ea2926d2c0

Final local verification on updated main: `python -m unittest discover -s tests -q` — 149 tests passed. Failure messages printed by negative-path fixtures are expected; process exit code was 0.

## Changes and preserved safeguards

See PRs for exact diffs. Changed production areas: full-report composer, daily orchestration, snapshot validator/schema, source retrieval metadata, portal labels/rendering, GCLRI collector workflow and guarded push helper. Tests and operations documentation updated. Dated context is labeled with its actual close/observation date and cannot become a current signal or ETF recommendation. Failed/invalid collection still blocks publication. Earlier reports, same-day vintages, source history and research rules remain intact. No production-eligibility promotion was made.

Earlier failures remain real historical failures: collection 39343936124 lost a concurrent push race; dependent 39343963877 correctly blocked. Daily 39344307800 failed at old date-sensitive tests. PRs #54/#55 resolved these causes; later successful runs are recorded above, not substituted for failed outcomes.

## Remaining work / limitations

Official RISE master run 39371488988 failed collecting https://kbam.co.kr/find with URLError timeout. Its status is FAILED, not completed; this separate source outage did not block the verified market-report pipeline. Existing scheduled retries remain enabled. Do not replace source facts or relabel the last successful master as freshly collected. Investigate source availability before changing parsing logic.

P2 remains: verified holdings/exposure linkage, investor-category flows, competitor metrics and evaluated product opportunities. Independent-observation historical calibration remains required; repeated execution is not new market evidence. Vercel password/auth work remains deferred.

## Resume commands

```sh
git fetch origin
git switch main
git merge --ff-only origin/main
git status --short --branch
python -m unittest discover -s tests -q
cat data/operations/intelligence.json
cat data/master_collection_status.json
```

Inspect GitHub Actions and public bytes separately from local publication receipts. Run collection experiments in an isolated checkout to avoid modifying tracked raw data. The next concrete unresolved issue is official-master source reachability; do not weaken validation to turn an outage into success.
