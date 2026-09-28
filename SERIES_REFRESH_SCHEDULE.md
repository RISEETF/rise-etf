# Price and FX refresh schedule

The existing GitHub Actions `Capture dated price and FX series` workflow recaptures
all pilot sources and rebuilds the database, coverage, and exploratory RS.

| KST schedule | UTC cron | Purpose |
| --- | --- | --- |
| Mon–Sat 08:15 | `15 23 * * 0-5` | Recapture prior Korean dates; Saturday includes Friday |
| Tue–Sat 14:15 | `15 5 * * 2-6` | Recapture US dates after New York midnight, including Friday on Saturday |
| Mon–Fri 17:15 | `15 8 * * 1-5` | Existing afternoon refresh |

The 14:15 KST slot is 01:15 in New York during daylight time and 00:15
during standard time. It supports the conservative RS rule requiring price date
to precede capture-local date. The morning slot alone cannot admit the previous
US session under that rule because New York is still on that date.

These schedules are retrieval opportunities, not guaranteed publication or
delivery times. Exchange holidays and provider delays can leave observation dates
unchanged. Capturing after local midnight does not certify an official close.
The RS session guard and its audit remain in force. All slots use the existing
shared writer concurrency group; overlapping runs queue instead of racing commits.

No new secrets, providers, or permissions are introduced. Existing manual dispatch,
calculation-code push trigger, and failure handling remain available.
