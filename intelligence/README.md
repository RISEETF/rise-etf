# RISE Intelligence Portal v0.4

JSON-driven decision UI for Daily RISE Market Intelligence.

- `index.html`: portal UI
- `data/latest.json`: canonical current snapshot
- `data/archive.json`: archive manifest
- `data/daily/*.json`: daily snapshots
- `data/framework_history.json`: framework lineage
- `reports/*.html`: full-report drill-down

Pipeline: Full Daily Intelligence → Dashboard Snapshot → validation → daily/latest/archive → full-report HTML → GitHub Pages.
