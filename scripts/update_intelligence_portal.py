#!/usr/bin/env python3
import argparse, json, shutil, html
from pathlib import Path
from datetime import datetime
from validate_intelligence_snapshot import validate

def render_report(snapshot, narrative_text):
    d=dict(snapshot)
    d.setdefault('regime_confidence','미제공')
    d.setdefault('regime_change_candidate','미제공')
    body = "<p>".join(html.escape(x) for x in narrative_text.split("\n\n") if x.strip())
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>RISE Daily Intelligence — {html.escape(d['asof_date'])}</title><style>body{{font-family:system-ui,'Noto Sans KR';max-width:980px;margin:40px auto;padding:0 20px;background:#0b1020;color:#eef3ff;line-height:1.7}}a{{color:#9fc0ff}}.meta{{background:#121a2d;border:1px solid #253451;padding:16px;border-radius:14px}}</style></head><body><p><a href="../index.html">← RISE Intelligence Portal</a></p><h1>RISE Daily Intelligence — {html.escape(d['asof_date'])}</h1><div class="meta"><b>Current Regime:</b> {html.escape(d['current_regime'])}<br><b>Confidence:</b> {html.escape(str(d['regime_confidence']))}{'%' if isinstance(d['regime_confidence'], (int,float)) else ''}<br><b>Regime Change:</b> {html.escape(d['regime_change_status'])} · {html.escape(d['regime_change_candidate'])}<br><b>Top Change:</b> {html.escape(d['top_change'])}</div><hr>{body}</body></html>'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--snapshot",required=True); ap.add_argument("--narrative",required=True); ap.add_argument("--portal-dir",default="intelligence"); args=ap.parse_args()
    snap_path=Path(args.snapshot); narrative_path=Path(args.narrative); portal=Path(args.portal_dir)
    d=json.loads(snap_path.read_text(encoding="utf-8")); errors=validate(d)
    if d.get("snapshot_type") == "SUMMARY_ONLY":
        errors.append("routine Daily publishing requires canonical FULL snapshot; SUMMARY_ONLY is read-only/emergency compatibility")
    if errors: raise SystemExit("snapshot validation failed:\n- "+"\n- ".join(errors))
    daily=portal/"data"/"daily"; reports=portal/"reports"; daily.mkdir(parents=True,exist_ok=True); reports.mkdir(parents=True,exist_ok=True)
    asof=d["asof_date"]; d["full_report_path"]=f"reports/{asof}.html"; daily_path=daily/f"{asof}.json"
    if daily_path.exists():
        old=json.loads(daily_path.read_text(encoding="utf-8"))
        if old != d:
            vintage_dir=portal/"data"/"vintages"/asof; vintage_dir.mkdir(parents=True,exist_ok=True); stamp=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"); shutil.copy2(daily_path,vintage_dir/f"{stamp}_prior.json")
    daily_path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8"); (portal/"data"/"latest.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    manifest_path=portal/"data"/"archive.json"; manifest={"schema_version":"0.4","dates":[],"latest":asof}
    if manifest_path.exists(): manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    dates=set(manifest.get("dates",[])); dates.add(asof); manifest["schema_version"]="0.4"; manifest["dates"]=sorted(dates); manifest["latest"]=max(dates); manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (reports/f"{asof}.html").write_text(render_report(d,narrative_path.read_text(encoding="utf-8")),encoding="utf-8")
    hist_path=portal/"data"/"framework_history.json"; hist=json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []; existing={(x.get("date"),x.get("name"),x.get("to")) for x in hist}
    for x in d.get("framework_updates",[]):
        key=(asof,x.get("name"),x.get("status"))
        if key not in existing: hist.append({"date":asof,"name":x.get("name"),"from":"UNSPECIFIED","to":x.get("status"),"reason":"Daily Intelligence update"})
    hist.sort(key=lambda x:(x.get("date",""),x.get("name",""))); hist_path.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","asof_date":asof,"daily_snapshot":str(daily_path),"latest":str(portal/"data"/"latest.json"),"report":str(reports/f"{asof}.html"),"archive_count":len(manifest["dates"])},ensure_ascii=False))
if __name__=="__main__": main()
