#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from datetime import date

REQ = [
 "asof_date","current_regime","regime_confidence","regime_change_candidate",
 "regime_change_status","top_change","top_risk","macro_absorption_level",
 "macro_absorption_headroom","corporate_absorption_level","corporate_headroom",
 "fiscal_stress","credit_stress_current","credit_stress_forward","market_liquidity",
 "funding_liquidity","energy_stress","energy_reliability","energy_adaptation",
 "flow_state","top_rise_matches","product_candidates","framework_updates",
 "key_triggers","no_action","regime_history_update"
]
FRAMEWORK = {"CANDIDATE","SHADOW","VALIDATED","FROZEN"}
REGIME_CHANGE = {"NONE","WATCH","ACTIVE"}

def validate(d):
    errors=[]
    missing=[k for k in REQ if k not in d]
    if missing: errors.append("missing: "+", ".join(missing))
    try: date.fromisoformat(str(d.get("asof_date","")))
    except Exception: errors.append("asof_date must be YYYY-MM-DD")
    c=d.get("regime_confidence")
    if not isinstance(c,(int,float)) or isinstance(c,bool) or not 0 <= c <= 100: errors.append("regime_confidence must be numeric 0..100")
    if d.get("regime_change_status") not in REGIME_CHANGE: errors.append("regime_change_status invalid")
    if not isinstance(d.get("top_rise_matches"),list) or not d.get("top_rise_matches"): errors.append("top_rise_matches must be non-empty list")
    if not isinstance(d.get("product_candidates"),list): errors.append("product_candidates must be list")
    if not isinstance(d.get("framework_updates"),list): errors.append("framework_updates must be list")
    else:
        for i,x in enumerate(d["framework_updates"]):
            if x.get("status") not in FRAMEWORK: errors.append(f"framework_updates[{i}].status invalid")
    h=d.get("regime_history_update")
    if not isinstance(h,dict): errors.append("regime_history_update must be object")
    else:
        for k in ["prior_state","today_state","transition_gate_crossed"]:
            if k not in h: errors.append(f"regime_history_update.{k} missing")
        if "transition_gate_crossed" in h and not isinstance(h["transition_gate_crossed"],bool): errors.append("transition_gate_crossed must be boolean")
    for k in ["key_triggers","no_action"]:
        if not isinstance(d.get(k),list): errors.append(f"{k} must be list")
    return errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("snapshot"); args=ap.parse_args()
    d=json.loads(Path(args.snapshot).read_text(encoding="utf-8")); errors=validate(d)
    if errors:
        print("INVALID"); [print("- "+e) for e in errors]; return 2
    print("VALID", d["asof_date"], d["current_regime"]); return 0
if __name__=="__main__": raise SystemExit(main())
