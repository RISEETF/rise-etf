# AAPL issuer reconciliation and real split fixture — 2026-09-16

## Findings

Eight dividends in the 2024-09-16–2026-09-15 capture and one historical 2020
dividend match selected facts from Apple's official dividend-history table after
accounting for the table's stated unadjusted amount basis. These are amount-only
matches, not independently verified ex-dividend dates.

Apple's table gives declared, record and payable dates. The captured Yahoo event
date is not silently renamed a record date. For example, the November 2024 event
is dated November 8 by the provider, while Apple's record date is November 11.
The amount matches, but this source does not establish the ex-date.

The 2020 split ratio and first split-adjusted trading date match the provider's
event: 4:1 on August 31. Apple's FAQ separately labels August 28 as the split date.
The dividend-history footnote explicitly identifies the first trading date, so
that field controls comparison to the daily-price event; both labels are retained.

The official August 2020 cash dividend is $0.82 on its unadjusted share basis.
Dividing by the subsequent 4:1 split yields the provider's $0.205. Directly comparing
the two unaligned amounts would create a false data-quality failure.

The captured August 28/31 closes are approximately 124.8075 and 129.0400. Their
as-received change is about 3.3912%. Dividing the prior close by four again would
produce about 313.5649%, an intentionally incorrect double-adjustment counterexample.
The code preserves the received prices and does not apply that extra adjustment.
This diagnostic is not a certified total return or proof of all provider adjustments.

## Evidence and access limits

- [Apple dividend history](https://investor.apple.com/dividend-history/default.aspx)
- [Apple FAQ](https://investor.apple.com/faq/default.aspx)
- `data/validation/apple_official_extract.json`: selected factual rows transcribed
  from the web tool's official-page text on 2026-09-16. This is not a full source
  archive or an automatically refreshed issuer feed. The original HTML hash is
  explicitly null; the evidence-file hash refers only to the saved transcription.
- Direct automated access returned a challenge page. No challenge workaround was
  attempted and no issuer refresh job was scheduled.
- Provider source bytes and normalized observations for the bounded 2020 fixture
  are preserved separately under `data/validation/aapl_2020/`. They do not enter
  the main price-series table or inflate the current universe's history coverage.
- The fixture manifest pins the recent and historical capture IDs. Later regular
  collection does not silently broaden this issuer-validation claim.

## Matching and reproduction

Within each selected observation window, a provider cash event on or up to seven
calendar days before an issuer record date is an association candidate only.
Multiple candidates or reuse produce an unresolved result, never an arbitrary
match. This window is not an ex-date rule or exchange calendar. Subsequent splits
in the selected issuer evidence convert the official amount basis for this
bounded case. A general production action engine needs a complete split ledger.

Run `python scripts/verify_apple_actions.py` to reparse hash-checked provider bytes
and reproduce `data/quality/apple_issuer_validation.json` offline. `--collect`
requests a new bounded historical fixture; normal CI never fetches it.

The Python suite has 24 passing tests, including date-type separation, ambiguous
matching, amount differences, split-date choice, price preservation and reproduction
from the stored real case. CI also checks the portal's explicit partial-validation
labels. Still unresolved: independently sourced cash ex-dates, other issuers,
Korean ETF distribution adjustments, exchange calendars and FX timing. RS remains
blocked for every instrument.
