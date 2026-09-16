# First portal release

Scope: official RISE master search, data coverage and quality diagnostics. RS rankings and trading signals remain blocked. This release does not require completing RS research.

## Changes prepared

- Historical domestic master identities and snapshot names survive removal or renaming in the current master. `master_memberships.is_current` means membership in the latest saved list, not confirmed listing/delisting status. This is not a complete point-in-time security identifier service.
- `refresh_pages.yml` requests a Pages build after each default-branch collector finishes, including failures that saved diagnostic status. It never checks out upstream code or consumes artifacts. Other branches cannot request publication through this workflow.
- The refresh step checks that Pages uses branch publishing from the default branch root. A different configuration fails visibly rather than changing repository settings.

## Release checks

1. Require the latest PR validation run to pass (Python tests, source-backed DB rebuild, issuer reconciliation, JavaScript and browser tests).
2. Confirm repository Settings → Pages uses `Deploy from a branch`, `main`, `/ (root)`. Earlier main Pages runs succeeded, but the connected GitHub reader cannot retrieve the Pages settings endpoint; configuration has not been directly verified here.
3. Merge the reviewed PR when release is approved. Check the resulting Pages build and live portal: 143 products for the saved 2026-09-16 master, search, source dates, coverage, and blocked RS state.
4. Run one collector on main and verify `Refresh Pages after data collection` succeeds, then verify the new capture timestamp on the live page. A queued build request is not proof of successful publication.
5. If publication fails, retain capture evidence, inspect the failed Actions job, and correct the publishing setting/permission. Do not report automatic operation as verified until the live check passes.

## Why explicit refresh is needed

GitHub documents that pushes made with `GITHUB_TOKEN` do not trigger the normal Pages build. The REST Pages build endpoint supports installation tokens with `pages: write`; the new workflow uses this documented route without an additional secret.

- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build

No merge, Pages setting change, or live deployment was performed while preparing this change. Production refresh remains to be verified after release.
