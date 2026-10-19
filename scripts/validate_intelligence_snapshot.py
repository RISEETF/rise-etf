#!/usr/bin/env python3
import argparse, json, math
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

def validate_dated_coverage(d):
    errors=[]
    coverage=d.get('coverage',{})
    if (not isinstance(coverage,dict) or coverage.get('policy')!='DATED_OBSERVATIONS_V1' or
        coverage.get('state') not in {'DATED_INPUTS','CURRENT_INPUTS'} or coverage.get('blockers')!=[] or
        coverage.get('excluded')!=[] or not isinstance(coverage.get('dated_context'),list)):
        return ['invalid dated-data coverage'],set()
    rows=d.get('observations',[])
    if not isinstance(rows,list): return ['invalid observation list'],set()
    observed={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('series_id'),str):
            errors.append('invalid dated observation'); continue
        key=row['series_id']
        if key in observed: errors.append('duplicate observation')
        observed[key]=row
        try:
            ds=date.fromisoformat(row['observation_date'])
            if ds>date.fromisoformat(d['asof_date']): raise ValueError()
            value=row['value']
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value): raise ValueError()
            label=f"{row['observation_date']} {'종가' if key=='VIXCLS' else '관측값'} 기준"
            if row.get('asof_label')!=label: raise ValueError()
            if row.get('fresh_for_report') not in (True,False) or type(row.get('fresh_for_report')) is not bool: raise ValueError()
            if row.get('use')!=('FRESH_RESEARCH' if row['fresh_for_report'] else 'DATED_CONTEXT_ONLY'): raise ValueError()
        except (KeyError,TypeError,ValueError): errors.append('invalid dated observation: '+key)
    contextual=set()
    for row in coverage['dated_context']:
        if not isinstance(row,dict) or row.get('series_id') not in observed:
            errors.append('unknown context observation'); continue
        key=row['series_id']; original=observed[key]
        if key in contextual: errors.append('duplicate dated context')
        contextual.add(key)
        if (original.get('fresh_for_report') is not False or row.get('use')!='DATED_CONTEXT_ONLY' or
            not row.get('reason') or any(row.get(k)!=original.get(k) for k in ('value','unit','observation_date','asof_label'))):
            errors.append('context differs from observation')
        try:
            age=(date.fromisoformat(d['asof_date'])-date.fromisoformat(row['observation_date'])).days
            if type(row.get('age_calendar_days')) is not int or row['age_calendar_days']!=age or age<0: raise ValueError()
            previous=row.get('prior_change')
            if previous is not None:
                if not isinstance(previous,dict) or previous.get('unit')!=row['unit']: raise ValueError()
                if date.fromisoformat(previous['prior_observation_date'])>=date.fromisoformat(row['observation_date']): raise ValueError()
                for value in (previous['prior_value'],previous['change']):
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value): raise ValueError()
                if not math.isclose(row['value']-previous['prior_value'],previous['change'],rel_tol=1e-12,abs_tol=1e-12): raise ValueError()
        except (KeyError,TypeError,ValueError): errors.append('invalid dated context change/age')
    if contextual!={k for k,r in observed.items() if r.get('fresh_for_report') is False}:
        errors.append('dated observations must be explicitly covered')
    if bool(contextual)!=(coverage['state']=='DATED_INPUTS'): errors.append('dated coverage label mismatch')
    return errors,contextual


def validate_bounded(d):
    # 1.0 remains unchanged. 1.1 explicitly represents unassessed judgments.
    errors=[]
    dated = d.get('schema_version') == '1.2'
    if d.get('snapshot_type') != 'FULL' or d.get('report_mode') != ('DATED_OBSERVATIONS_V1' if dated else 'BOUNDED_RESEARCH_V1'):
        errors.append('1.1 requires bounded FULL research report')
    if d.get('regime_confidence') is not None or not d.get('regime_confidence_reason'):
        errors.append('bounded confidence must be null with reason')
    if d.get('production_eligible') is not False or d.get('regime_assessment') != 'CARRIED_FORWARD_NOT_RECONFIRMED':
        errors.append('bounded report cannot promote or reconfirm regime')
    try:
        if date.fromisoformat(d['regime_reference_date']) > date.fromisoformat(d['asof_date']): raise ValueError()
    except (KeyError, TypeError, ValueError): errors.append('invalid regime reference date')
    for field in REQ[7:20]:
        gaps=d.get('assessment_gaps')
        if d.get(field) != 'UNRESOLVED' or not isinstance(gaps,dict) or not isinstance(gaps.get(field),str) or not gaps[field].strip():
            errors.append('bounded unassessed field requires reason: '+field)
    if d.get('framework_updates') != [] or d.get('product_candidates') != [] or not d.get('product_assessment'):
        errors.append('bounded report cannot invent framework/product judgments')
    gate=d.get('regime_history_update',{})
    if (not isinstance(gate,dict) or gate.get('transition_gate_crossed') is not False or
        gate.get('prior_state') != d.get('current_regime') or gate.get('today_state') != d.get('current_regime') or
        d.get('regime_change_status') not in {'NONE','WATCH'}):
        errors.append('bounded regime transition prohibited')
    if dated:
        dated_errors, excluded = validate_dated_coverage(d)
        errors.extend(dated_errors)
    else:
        coverage=d.get('coverage',{})
        if (not isinstance(coverage,dict) or coverage.get('policy') != 'BOUNDED_RESEARCH_V1' or
            coverage.get('state') not in {'PARTIAL','CURRENT_INPUTS'} or coverage.get('blockers') != [] or
            not isinstance(coverage.get('excluded'),list)):
            errors.append('invalid report coverage')
            coverage={'excluded':[]}
        excluded=set()
        for row in coverage.get('excluded',[]):
            if not isinstance(row,dict) or row.get('series_id') != 'DTWEXBGS' or not row.get('reason'):
                errors.append('invalid coverage exclusion')
            else: excluded.add(row['series_id'])
        if coverage.get('state') in {'PARTIAL','CURRENT_INPUTS'} and bool(excluded)!=(coverage['state']=='PARTIAL'):
            errors.append('coverage label mismatch')
    observations=d.get('observations')
    if not isinstance(observations,list) or not observations:
        errors.append('bounded report requires observations')
    else:
        for row in observations:
            if not isinstance(row,dict) or row.get('series_id') in excluded and row.get('fresh_for_report') is not False:
                errors.append('excluded observation cannot be fresh')
    decisions=d.get('decision_board')
    if not isinstance(decisions,list) or (not dated and not decisions):
        errors.append('bounded report requires decision board')
    else:
        for row in decisions:
            if not isinstance(row,dict) or not isinstance(row.get('series_ids'),list):
                errors.append('invalid decision row'); continue
            if excluded.intersection(row['series_ids']): errors.append('excluded series in decision')
            for key in ('signal_id','what_changed','confidence','transmission','counterargument','falsification','routing'):
                if not isinstance(row.get(key),str) or not row[key].strip(): errors.append('decision field missing: '+key)
    for key in ('strongest_counterevidence','rise_match_status'):
        if not isinstance(d.get(key),str) or not d[key].strip(): errors.append(key+' missing')
    for row in d.get('top_rise_matches',[]) if isinstance(d.get('top_rise_matches'),list) else []:
        if not isinstance(row,dict) or row.get('basis') != 'NAME_ONLY_UNVERIFIED_EXPOSURE': errors.append('unverified ETF exposure must be explicit')
    return errors

def validate(d):
    errors=[]
    if not isinstance(d,dict): return ['snapshot must be object']
    version = d.get('schema_version', '1.0')
    if version not in {'1.0', '1.1', '1.2'}: errors.append('unsupported schema_version')
    if version in {'1.1', '1.2'}: errors.extend(validate_bounded(d))
    if d.get('snapshot_type') == 'SUMMARY_ONLY':
        return errors+validate_summary(d)
    if d.get('snapshot_type') not in (None,'FULL'): errors.append('unknown snapshot_type')
    missing=[k for k in REQ if k not in d]
    if missing: errors.append("missing: "+", ".join(missing))
    try: date.fromisoformat(str(d.get("asof_date","")))
    except Exception: errors.append("asof_date must be YYYY-MM-DD")
    c=d.get("regime_confidence")
    if version not in {'1.1', '1.2'} and (not isinstance(c,(int,float)) or isinstance(c,bool) or not 0 <= c <= 100): errors.append("regime_confidence must be numeric 0..100")
    if d.get("regime_change_status") not in REGIME_CHANGE: errors.append("regime_change_status invalid")
    if not isinstance(d.get("top_rise_matches"),list) or (version not in {"1.1", "1.2"} and not d.get("top_rise_matches")): errors.append("top_rise_matches must be non-empty list")
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
