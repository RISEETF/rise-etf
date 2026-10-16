#!/usr/bin/env python3
import argparse, json, shutil, html, tempfile, os
from uuid import uuid4
from datetime import date
from pathlib import Path
from datetime import datetime, timezone
from validate_intelligence_snapshot import validate

def render_report(snapshot, narrative_text):
    d=dict(snapshot)
    d.setdefault('regime_confidence','미제공')
    d.setdefault('regime_change_candidate','미제공')
    body = "".join("<p>" + html.escape(x) + "</p>" for x in narrative_text.split("\n\n") if x.strip())
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>RISE Daily Intelligence — {html.escape(d['asof_date'])}</title><style>body{{font-family:system-ui,'Noto Sans KR';max-width:980px;margin:40px auto;padding:0 20px;background:#0b1020;color:#eef3ff;line-height:1.7}}a{{color:#9fc0ff}}.meta{{background:#121a2d;border:1px solid #253451;padding:16px;border-radius:14px}}</style></head><body><p><a href="../index.html">← RISE Intelligence Portal</a></p><h1>RISE Daily Intelligence — {html.escape(d['asof_date'])}</h1><div class="meta"><b>Current Regime:</b> {html.escape(d['current_regime'])}<br><b>Confidence:</b> {html.escape(str(d['regime_confidence']))}{'%' if isinstance(d['regime_confidence'], (int,float)) else ''}<br><b>Regime Change:</b> {html.escape(d['regime_change_status'])} · {html.escape(d['regime_change_candidate'])}<br><b>Top Change:</b> {html.escape(d['top_change'])}</div><hr>{body}</body></html>'''

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_portal(portal):
    """Validate the entire publication, including historical report links."""
    manifest = read_json(portal / "data/archive.json")
    dates = manifest["dates"]
    if not dates or dates != sorted(set(dates)) or manifest["latest"] != max(dates):
        raise ValueError("archive must contain sorted unique dates and chronological latest")
    for day in dates:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("noncanonical archive date")
        snapshot = read_json(portal / f"data/daily/{day}.json")
        errors = validate(snapshot)
        if errors or snapshot["asof_date"] != day:
            raise ValueError(f"invalid daily snapshot {day}: {errors}")
        report = snapshot.get("full_report_path")
        if report:
            if report != f"reports/{day}.html" or snapshot.get("report_status") in {
                "SUMMARY_ONLY_FULL_REPORT_PENDING", "HTML_PUBLISH_BLOCKED"
            }:
                raise ValueError(f"report path/status mismatch: {day}")
            text = (portal / report).read_text(encoding="utf-8")
            if "<html" not in text.lower() or "</html>" not in text.lower() or day not in text:
                raise ValueError(f"invalid report HTML: {day}")
        elif snapshot.get("snapshot_type") != "SUMMARY_ONLY":
            raise ValueError(f"FULL snapshot requires report: {day}")
    if read_json(portal / "data/latest.json") != read_json(portal / f"data/daily/{max(dates)}.json"):
        raise ValueError("latest differs from chronological latest daily snapshot")


def publish(snapshot_path, narrative_path, portal, revision_reason=None):
    portal = Path(portal).resolve()
    d = read_json(Path(snapshot_path))
    errors = validate(d)
    if not isinstance(d, dict) or d.get("snapshot_type") == "SUMMARY_ONLY":
        errors.append("routine Daily publishing requires canonical FULL snapshot")
    if errors:
        raise ValueError("snapshot validation failed: " + "; ".join(errors))
    d.setdefault("schema_version", "1.0")
    asof = d["asof_date"]
    if date.fromisoformat(asof).isoformat() != asof:
        raise ValueError("asof_date must be canonical YYYY-MM-DD")
    narrative = Path(narrative_path).read_text(encoding="utf-8")
    if not narrative.strip():
        raise ValueError("narrative must not be empty")
    d["full_report_path"] = f"reports/{asof}.html"
    d["report_status"] = "PUBLISHED"
    report = render_report(d, narrative)
    portal.parent.mkdir(parents=True, exist_ok=True)
    lock = portal.parent / ("." + portal.name + ".publish.lock")
    # Exclusive lock also blocks retries after abrupt termination until reviewed.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with tempfile.TemporaryDirectory(prefix=".intelligence-stage-", dir=portal.parent) as tmp:
            stage = Path(tmp) / "portal"
            if portal.exists():
                shutil.copytree(portal, stage)
            else:
                stage.mkdir()
            daily = stage / f"data/daily/{asof}.json"
            report_path = stage / d["full_report_path"]
            old = read_json(daily) if daily.exists() else None
            old_report = report_path.read_text(encoding="utf-8") if report_path.exists() else None
            changed = old != d or old_report != report
            if old is not None and changed:
                if not revision_reason or not revision_reason.strip():
                    raise ValueError("same-date revision requires --revision-reason")
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex
                vintage = stage / "data/vintages" / asof / stamp
                vintage.mkdir(parents=True)
                shutil.copy2(daily, vintage / "snapshot.json")
                if report_path.exists():
                    shutil.copy2(report_path, vintage / "report.html")
                write_json(vintage / "revision.json", {"reason": revision_reason, "replaced_at": stamp})
            write_json(daily, d)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            manifest_path = stage / "data/archive.json"
            manifest = read_json(manifest_path) if manifest_path.exists() else {"dates": []}
            dates = sorted(set(manifest["dates"]) | {asof})
            manifest.update(schema_version="0.4", dates=dates, latest=max(dates))
            write_json(manifest_path, manifest)
            write_json(stage / "data/latest.json", read_json(stage / f"data/daily/{max(dates)}.json"))
            hist_path = stage / "data/framework_history.json"
            hist = read_json(hist_path) if hist_path.exists() else []
            existing = {(x.get("date"), x.get("name"), x.get("to")) for x in hist}
            for x in d.get("framework_updates", []):
                key = (asof, x.get("name"), x.get("status"))
                if key not in existing:
                    hist.append({"date": asof, "name": x.get("name"), "from": "UNSPECIFIED",
                                 "to": x.get("status"), "reason": "Daily Intelligence update"})
                    existing.add(key)
            hist.sort(key=lambda x: (x.get("date", ""), x.get("name", "")))
            write_json(hist_path, hist)
            validate_portal(stage)
            # Repository checkout transaction; public visibility is one Git commit.
            backup = portal.parent / ("." + portal.name + ".backup-" + uuid4().hex)
            had_portal = portal.exists()
            if had_portal:
                os.replace(portal, backup)
            try:
                os.replace(stage, portal)
            except BaseException:
                if had_portal:
                    os.replace(backup, portal)
                raise
            if had_portal:
                shutil.rmtree(backup)
        return {"status": "SUCCESS", "asof_date": asof, "archive_count": len(dates),
                "content_changed": changed}
    finally:
        lock.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--narrative", required=True)
    ap.add_argument("--portal-dir", default="intelligence")
    ap.add_argument("--revision-reason")
    args = ap.parse_args()
    print(json.dumps(publish(args.snapshot, args.narrative, args.portal_dir, args.revision_reason), ensure_ascii=False))


if __name__ == "__main__":
    main()
