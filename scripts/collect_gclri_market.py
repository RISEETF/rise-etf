#!/usr/bin/env python3
import csv, io, json, math, urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"data/gclri/series_registry.json"
OUT=ROOT/"data/gclri/latest.json"
HIST=ROOT/"data/gclri/history.json"
UA={"User-Agent":"RISE-ETF-Research/0.6 (+public GitHub research collector)"}

def fetch_csv(series_id):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8-sig","replace")

def parse_series(text, series_id):
    rows=[]
    for row in csv.DictReader(io.StringIO(text)):
        ds=row.get("DATE") or row.get("observation_date")
        raw=row.get(series_id)
        if not ds or raw in (None,"","."):
            continue
        try: v=float(raw)
        except ValueError: continue
        if math.isfinite(v): rows.append({"date":ds,"value":v})
    rows.sort(key=lambda x:x["date"])
    return rows

def main():
    reg=json.loads(REG.read_text(encoding="utf-8"))
    history={}
    latest={}
    errors=[]
    today=date.today()
    for meta in reg["series"]:
        sid=meta["id"]
        try:
            rows=parse_series(fetch_csv(sid),sid)
            if not rows: raise RuntimeError("no numeric observations")
            rows=rows[-800:]
            history[sid]=rows
            last=rows[-1]
            prev=rows[-2] if len(rows)>1 else None
            age=(today-date.fromisoformat(last["date"])).days
            latest[sid]={**meta,
                "observation_date":last["date"],"value":last["value"],
                "prior_observation_date":prev["date"] if prev else None,
                "prior_value":prev["value"] if prev else None,
                "change_1obs":(last["value"]-prev["value"]) if prev else None,
                "age_calendar_days":age,
                "data_state":"CURRENT" if age<=7 else "STALE"
            }
        except Exception as e:
            errors.append({"series_id":sid,"error":type(e).__name__+": "+str(e)[:300]})
            latest[sid]={**meta,"observation_date":None,"value":None,"data_state":"UNAVAILABLE"}
    status="SUCCESS" if not errors else ("PARTIAL" if len(errors)<len(reg["series"]) else "FAILED")
    payload={
      "schema_version":"0.6","built_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":status,"series":latest,"errors":errors,
      "methodology":{
        "raw_not_regime_score":True,
        "no_forward_fill":True,
        "missing_policy":"UNAVAILABLE_OR_STALE_NOT_ZERO",
        "source_note":"FRED distribution endpoints; originating organizations preserved in registry metadata."
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    HIST.write_text(json.dumps({"schema_version":"0.6","series":history},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":status,"series_ok":len(history),"errors":len(errors)},ensure_ascii=False))
    if status=="FAILED": raise SystemExit(2)

if __name__=="__main__": main()
