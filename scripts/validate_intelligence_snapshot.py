#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from datetime import date, datetime

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
    if not isinstance(d,dict): return ['snapshot must be object']
    if d.get('snapshot_type') == 'SUMMARY_ONLY':
        required={'snapshot_type','asof_date','current_regime','regime_change_status','top_change','full_report_path','report_generated_at','market_data_asof'}
        if set(d)!=required: errors.append('summary fields must match SUMMARY_ONLY contract')
        for key in ('asof_date','market_data_asof'):
            try: date.fromisoformat(d.get(key,''))
            except (ValueError,TypeError): errors.append(key+' must be YYYY-MM-DD')
        if not errors and d['market_data_asof']>d['asof_date']: errors.append('market date after report date')
        for key in ('current_regime','top_change'):
            if not isinstance(d.get(key),str) or not d[key].strip(): errors.append(key+' must be non-empty text')
        if d.get('regime_change_status') not in REGIME_CHANGE|{'KEEP','CHALLENGE','TRANSITION_CANDIDATE'}: errors.append('summary regime_change_status invalid')
        if d.get('full_report_path')!=f"reports/{d.get('asof_date')}.html": errors.append('summary report path must match date')
        try:
            stamp=datetime.fromisoformat(d.get('report_generated_at','').replace('Z','+00:00'))
            if stamp.utcoffset() is None: raise ValueError()
        except (ValueError,TypeError): errors.append('report_generated_at must include timezone')
        return errors
    if d.get('snapshot_type') not in (None,'FULL'): errors.append('unknown snapshot_type')
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
