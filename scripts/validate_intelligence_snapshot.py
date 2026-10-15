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
SUMMARY_REQUIRED = {'snapshot_type','asof_date','current_regime','regime_change_status','top_change','full_report_path','report_generated_at','market_data_asof'}
SUMMARY_OPTIONAL = {'schema_version','top_risk','flow_state','top_rise_matches','product_candidates','framework_updates','key_triggers','no_action','daily_intelligence_gate_decision','validation_state','production_eligible','internal_data_asof','report_status'}
PENDING_REPORT = {'SUMMARY_ONLY_FULL_REPORT_PENDING','HTML_PUBLISH_BLOCKED'}
REPORT_STATUS = PENDING_REPORT | {'PUBLISHED','PUBLISHED_INTERNAL_RECOVERY'}

def validate_summary(d):
    errors=[]
    missing=SUMMARY_REQUIRED-set(d)
    unknown=set(d)-SUMMARY_REQUIRED-SUMMARY_OPTIONAL
    if missing: errors.append('summary missing: '+', '.join(sorted(missing)))
    if unknown: errors.append('summary unsupported fields: '+', '.join(sorted(unknown)))
    for key in ('asof_date','market_data_asof','internal_data_asof'):
        if key=='internal_data_asof' and key not in d: continue
        try:
            value=d.get(key)
            if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value: raise ValueError()
        except (ValueError,TypeError): errors.append(key+' must be YYYY-MM-DD')
    if not errors and d['market_data_asof']>d['asof_date']: errors.append('market date after report date')
    for key in ('current_regime','top_change','top_risk','flow_state','daily_intelligence_gate_decision','validation_state'):
        if key not in SUMMARY_REQUIRED and key not in d: continue
        if not isinstance(d.get(key),str) or not d[key].strip(): errors.append(key+' must be non-empty text')
    if d.get('regime_change_status') not in REGIME_CHANGE|{'KEEP','CHALLENGE','TRANSITION_CANDIDATE'}: errors.append('summary regime_change_status invalid')
    if 'production_eligible' in d and d['production_eligible'] is not False: errors.append('summary cannot be production eligible')
    if 'report_status' in d and d['report_status'] not in REPORT_STATUS: errors.append('report_status invalid')
    path=d.get('full_report_path')
    if path is None:
        if d.get('report_status') not in PENDING_REPORT: errors.append('null report path requires explicit pending status')
    elif path!=f"reports/{d.get('asof_date')}.html" or d.get('report_status') in PENDING_REPORT:
        errors.append('summary report path/status must match date and publication state')
    try:
        stamp=datetime.fromisoformat(d.get('report_generated_at','').replace('Z','+00:00'))
        if stamp.utcoffset() is None: raise ValueError()
    except (ValueError,TypeError,AttributeError): errors.append('report_generated_at must include timezone')
    for key in ('key_triggers','no_action'):
        if key in d and (not isinstance(d[key],list) or any(not isinstance(x,str) or not x.strip() for x in d[key])): errors.append(key+' must be text list')
    for key in ('top_rise_matches','product_candidates','framework_updates'):
        if key not in d: continue
        if not isinstance(d[key],list):
            errors.append(key+' must be list'); continue
        for i,row in enumerate(d[key]):
            if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not row['name'].strip():
                errors.append(f'{key}[{i}] requires name'); continue
            if any(not isinstance(v,str) for v in row.values()): errors.append(f'{key}[{i}] values must be text')
            if key=='framework_updates' and row.get('status') not in FRAMEWORK|{'RESEARCH_REQUIRED'}: errors.append(f'{key}[{i}].status invalid')
    return errors

def validate(d):
    errors=[]
    if not isinstance(d,dict): return ['snapshot must be object']
    if d.get('schema_version','1.0') != '1.0': errors.append('unsupported schema_version')
    if d.get('snapshot_type') == 'SUMMARY_ONLY':
        return errors+validate_summary(d)
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
            if not isinstance(x,dict) or x.get("status") not in FRAMEWORK: errors.append(f"framework_updates[{i}].status invalid")
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
