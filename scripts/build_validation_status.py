#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
SIG_H=ROOT/"data/signals/history.json"
EP_H=ROOT/"data/episodes/history.json"
GATE_H=ROOT/"data/regime/gate_history.json"
OUT=ROOT/"data/validation/v1_status.json"

def read(p,default):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return default

def main():
    sig=read(SIG_H,{"runs":[]}); ep=read(EP_H,{"runs":[]}); gate=read(GATE_H,{"runs":[]})
    ns=len(sig.get("runs",[])); ne=len(ep.get("runs",[])); ng=len(gate.get("runs",[]))
    req_signal=60; req_episode=40; req_gate=40
    sufficient = ns>=req_signal and ne>=req_episode and ng>=req_gate
    checks=[
      {"name":"Signal history depth","value":ns,"required":req_signal,"status":"PASS" if ns>=req_signal else "INSUFFICIENT_HISTORY"},
      {"name":"Episode history depth","value":ne,"required":req_episode,"status":"PASS" if ne>=req_episode else "INSUFFICIENT_HISTORY"},
      {"name":"Gate history depth","value":ng,"required":req_gate,"status":"PASS" if ng>=req_gate else "INSUFFICIENT_HISTORY"}
    ]
    payload={
      "schema_version":"1.0",
      "built_at_utc":datetime.now(timezone.utc).isoformat(),
      "validation_state":"READY_FOR_HISTORICAL_CALIBRATION" if sufficient else "INSUFFICIENT_HISTORY",
      "production_eligible":False,
      "framework_promotion_authorized":False,
      "checks":checks,
      "promotion_gate":{
        "incremental_explanatory_value_required":True,
        "non_redundancy_required":True,
        "observable_data_required":True,
        "lead_lag_usefulness_required":True,
        "decision_relevance_required":True
      },
      "notes":[
        "No signal, episode, or regime-gate rule is promoted to VALIDATED solely from current live runs.",
        "Historical false-positive / false-negative testing is required before promotion.",
        "Framework additions that fail parsimony checks should be downgraded or removed."
      ]
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","validation_state":payload["validation_state"],"signal_runs":ns,"episode_runs":ne,"gate_runs":ng},ensure_ascii=False))

if __name__=="__main__": main()
