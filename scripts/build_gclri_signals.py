#!/usr/bin/env python3
import json, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/"data/gclri/history.json"
LATEST=ROOT/"data/gclri/latest.json"
REG=ROOT/"data/signals/signal_registry.json"
OUT=ROOT/"data/signals/latest.json"
HISTORY=ROOT/"data/signals/history.json"

def pct_change(a,b):
    if a is None or b in (None,0): return None
    return (a/b)-1.0

def horizon_change(rows,h):
    if len(rows)<=h: return None
    return rows[-1]["value"]-rows[-1-h]["value"]

def horizon_pct_change(rows,h):
    if len(rows)<=h: return None
    return pct_change(rows[-1]["value"],rows[-1-h]["value"])

def zscore_current(rows,h,win,mode="diff"):
    if len(rows) < h + win + 1: return None
    def move_at(i):
        a=rows[i]["value"]; b=rows[i-h]["value"]
        return (a-b) if mode=="diff" else pct_change(a,b)
    cur=move_at(len(rows)-1)
    prior=[]
    start=max(h, len(rows)-1-win)
    for i in range(start,len(rows)-1):
        x=move_at(i)
        if x is not None and math.isfinite(x): prior.append(x)
    if len(prior)<20: return None
    sd=statistics.pstdev(prior)
    if not sd or not math.isfinite(sd): return None
    return (cur-statistics.mean(prior))/sd

def classify(z,method):
    if z is None: return "INSUFFICIENT_DATA"
    a=abs(z)
    if a>=float(method.get("active_candidate_abs_z",999)): return "ACTIVE_CANDIDATE"
    if a>=float(method.get("watch_abs_z",999)): return "WATCH"
    return "NORMAL"

def series_state(latest,sid):
    x=(latest.get("series") or {}).get(sid,{})
    return x.get("data_state","UNAVAILABLE")

def build_one(sig, hist, latest):
    ids=sig["source_series"]; m=sig["methodology"]; h=int(m.get("primary_horizon_observations",m.get("horizon_observations",5))); win=int(m.get("normalization_window_observations",60))
    metric_mode="pct" if sig["signal_id"] in {"SIG-FX-001","SIG-ENERGY-001","SIG-MKT-001"} else "diff"
    details=[]
    for sid in ids:
        rows=(hist.get("series") or {}).get(sid,[])
        z=zscore_current(rows,h,win,"pct" if metric_mode=="pct" else "diff")
        move=horizon_pct_change(rows,h) if metric_mode=="pct" else horizon_change(rows,h)
        details.append({
          "series_id":sid,
          "observation_date":rows[-1]["date"] if rows else None,
          "latest_value":rows[-1]["value"] if rows else None,
          "horizon_observations":h,
          "horizon_move":move,
          "zscore":z,
          "data_state":series_state(latest,sid)
        })
    usable=[x for x in details if x["zscore"] is not None and x["data_state"]!="UNAVAILABLE"]
    if not usable:
        return {**{k:sig[k] for k in ["signal_id","name","status"]},"signal_state":"INSUFFICIENT_DATA","direction":"UNRESOLVED","confidence":"LOW","details":details}
    # Aggregation is intentionally conservative: choose strongest standardized move only for alerting.
    strongest=max(usable,key=lambda x:abs(x["zscore"]))
    state=classify(strongest["zscore"],m)
    direction="UP" if strongest["horizon_move"] is not None and strongest["horizon_move"]>0 else ("DOWN" if strongest["horizon_move"] is not None and strongest["horizon_move"]<0 else "FLAT")
    stale=any(x["data_state"]=="STALE" for x in usable)
    confidence="LOW" if stale else ("HIGH" if len(usable)>=2 else "MODERATE")
    # Breadth/confirmation metadata: never auto-promote to regime change.
    confirmation=sum(1 for x in usable if (x["horizon_move"] or 0)>0)
    return {
      **{k:sig[k] for k in ["signal_id","name","status"]},
      "signal_state":state,
      "direction":direction,
      "strongest_series":strongest["series_id"],
      "strongest_zscore":strongest["zscore"],
      "confidence":confidence,
      "confirmation_count":confirmation,
      "details":details,
      "production_eligible":False
    }

def main():
    hist=json.loads(HIST.read_text(encoding="utf-8"))
    latest=json.loads(LATEST.read_text(encoding="utf-8"))
    reg=json.loads(REG.read_text(encoding="utf-8"))
    signals=[build_one(s,hist,latest) for s in reg["signals"]]
    payload={
      "schema_version":"0.7",
      "built_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_gclri_built_at_utc":latest.get("built_at_utc"),
      "production_eligible":False,
      "regime_change_authorized":False,
      "signals":signals,
      "methodology":{
        "no_forward_fill":True,
        "raw_signal_not_regime_change":True,
        "hysteresis_rule":"Regime transition requires >=2 independent persistent channels or an extreme event changing market functioning/funding/policy/physical supply."
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    old={"schema_version":"0.7","runs":[]}
    if HISTORY.exists():
        try: old=json.loads(HISTORY.read_text(encoding="utf-8"))
        except Exception: pass
    old.setdefault("runs",[]).append(payload)
    old["runs"]=old["runs"][-260:]
    HISTORY.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","signals":len(signals),"alerts":sum(x["signal_state"] in ("WATCH","ACTIVE_CANDIDATE") for x in signals)},ensure_ascii=False))

if __name__=="__main__": main()
