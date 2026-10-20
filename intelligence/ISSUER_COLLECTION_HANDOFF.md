# Issuer collection resilience — 2026-10-20

Branch: fix/independent-issuer-collection. User authorized homepage/API separation and transient retries. Existing KRX daily identity inventory remains the primary exchange observation; no source records or historical master are reset.

Implementation: Finder and paginated API are collected independently in parallel. Each HTTP request retries transient failures up to three attempts, with 1/2 second backoff; authorization/not-found errors are not retried. API completeness/identity checks and Finder/API total agreement remain mandatory for a dated canonical master.

When API passes but Finder retrieval/date validation fails, preserve a hash-bound raw API capture and a separate data/master/api_captures version. Its effective_date is null and collection time is explicitly not a source effective date. Mark collection PARTIAL with master_updated=false and nonzero exit; keep the workflow failure visible and canonical master unchanged. Existing workflow stages these paths already. Consumers do not silently use undated captures as current official facts.

Local verification: 152 tests passed, including homepage timeout with valid API preservation, mismatched counts, transient retry/exhaustion, no retry on HTTP403 and existing historical integrity tests. GitHub CI and production run outcomes must be checked after PR creation/merge; not yet claimed here.

Resume: git fetch origin; inspect PR for this branch; python -m unittest discover -s tests -q. Check data/master_collection_status.json and the official master workflow separately from Intelligence publication. External endpoint recovery is not guaranteed by retries; if both endpoints fail, keep last good data and diagnose source connectivity. Password deferred; P2 remains separate.
