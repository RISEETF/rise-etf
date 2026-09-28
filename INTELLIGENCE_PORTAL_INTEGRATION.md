# RISE Intelligence Portal v0.4 Integration

The Intelligence Portal is isolated under `/intelligence/`; existing root portal and collectors are unchanged.

Safe update command:
```bash
python scripts/update_intelligence_portal.py --snapshot intelligence_inbox/snapshot.json --narrative intelligence_inbox/report.txt --portal-dir intelligence
```

The builder validates the Dashboard Snapshot, preserves same-date prior vintages, updates daily/latest/archive JSON, renders the full report HTML, and appends framework-state history.

Validation:
```bash
python scripts/validate_intelligence_snapshot.py intelligence/data/latest.json
python -m unittest tests.test_intelligence_portal -v
```

Production boundary: this package adds a deterministic validated publishing layer; it does not alter existing market-data collectors or production authorization.
