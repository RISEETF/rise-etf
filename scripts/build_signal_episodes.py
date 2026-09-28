#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
SIG=ROOT/"data/signals/latest.json"
SIG_HIST=ROOT/"data/signals/history.json"
GCLRI_HIST=ROOT/"data/gclri/history.json"
REG=ROOT/"data/episodes/episode_registry.json"
OUT=ROOT/"data/episodes/latest.json"
HISTORY=ROOT/"data/episodes/history.json"

TRIGGER={"WATCH","ACTIVE_CANDIDATE"}
ACTIVE_STATUSES={"WATCH","ACTIVE","STRENGTHENING","WEAKENING"}

def read(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def observed_date(sig):
    dates=[d.get("observation_date") for d in sig.get("details",[]) if d.get("observation_date")]
    return max(dates) if dates else None

def primary_detail(sig):
    sid=sig.get("strongest_series")
    for d in sig.get("details",[]):
        if d.get("series_id")==sid: return d
    return (sig.get("details") or [{}])[0]

def eligible_for_regime(sig):
    return bool(
      sig.get("signal_state") in TRIGGER
      and sig.get("confidence") in {"MODERATE","HIGH"}
      and all(d.get("data_state")=="CURRENT" for d in sig.get("details",[]) if d.get("zscore") is not None)
      and not sig.get("production_eligible",False)
    )

def cumulative_move(ep,sig,gclri_hist):
    sid=ep.get("primary_series")
    rows=(gclri_hist.get("series") or {}).get(sid,[])
    if not rows: return None
    start=ep.get("initial_observation_date")
    vals=[r for r in rows if r.get("date")>=start] if start else rows
    if not vals: return None
    first=vals[0]["value"]; last=vals[-1]["value"]
    if ep.get("move_basis")=="pct":
        return None if first==0 else last/first-1
    return last-first

def make_episode(sig,run_time):
    d=primary_detail(sig)
    obs=observed_date(sig) or run_time[:10]
    basis="pct" if sig.get("signal_id") in {"SIG-FX-001","SIG-ENERGY-001","SIG-MKT-001"} else "diff"
    z=sig.get("strongest_zscore")
    return {
      "episode_id":f"{sig['signal_id']}::{obs}::{sig.get('direction','UNRESOLVED')}",
      "signal_id":sig["signal_id"],
      "signal_name":sig["name"],
      "signal_governance_status":sig.get("status"),
      "episode_status":"ACTIVE" if sig.get("signal_state")=="ACTIVE_CANDIDATE" else "WATCH",
      "initial_trigger_date":run_time[:10],
      "initial_observation_date":obs,
      "initial_direction":sig.get("direction"),
      "primary_series":sig.get("strongest_series"),
      "move_basis":basis,
      "initial_zscore":z,
      "peak_magnitude_date":obs,
      "peak_abs_zscore":abs(z) if z is not None else None,
      "peak_signed_zscore":z,
      "cumulative_episode_move":0.0,
      "persistence_runs":1,
      "normal_confirmation_runs":0,
      "stress_scope":"UNRESOLVED",
      "policy_intervention_effect":"UNRESOLVED",
      "confirmation_eligible":eligible_for_regime(sig),
      "confidence":sig.get("confidence"),
      "latest_signal_state":sig.get("signal_state"),
      "latest_direction":sig.get("direction"),
      "latest_observation_date":obs,
      "latest_zscore":z,
      "falsification_status":"NOT_TESTED",
      "evidence":[{"date":obs,"evidence_role":"PRIMARY_OBSERVATION","signal_state":sig.get("signal_state"),"zscore":z}],
      "opened_at_utc":run_time,
      "last_updated_utc":run_time,
      "closed_at_utc":None
    }

def update_episode(ep,sig,run_time,gclri_hist,close_n):
    obs=observed_date(sig) or run_time[:10]
    z=sig.get("strongest_zscore")
    ep["last_updated_utc"]=run_time
    ep["latest_signal_state"]=sig.get("signal_state")
    ep["latest_direction"]=sig.get("direction")
    ep["latest_observation_date"]=obs
    ep["latest_zscore"]=z
    ep["confidence"]=sig.get("confidence")
    ep["confirmation_eligible"]=eligible_for_regime(sig)
    ep["persistence_runs"]=int(ep.get("persistence_runs",0))+1
    if z is not None and (ep.get("peak_abs_zscore") is None or abs(z)>ep["peak_abs_zscore"]):
        ep["peak_abs_zscore"]=abs(z); ep["peak_signed_zscore"]=z; ep["peak_magnitude_date"]=obs
    ep["cumulative_episode_move"]=cumulative_move(ep,sig,gclri_hist)

    state=sig.get("signal_state")
    prev=ep.get("episode_status")
    if state in TRIGGER:
        ep["normal_confirmation_runs"]=0
        if state=="ACTIVE_CANDIDATE":
            if prev in {"WATCH","WEAKENING"}: ep["episode_status"]="STRENGTHENING"
            elif prev=="STRENGTHENING": ep["episode_status"]="STRENGTHENING"
            else: ep["episode_status"]="ACTIVE"
        else:
            ep["episode_status"]="WATCH" if prev=="WATCH" else "WEAKENING"
        ep["evidence"].append({"date":obs,"evidence_role":"CONFIRMATION","signal_state":state,"zscore":z})
    elif state=="NORMAL":
        ep["normal_confirmation_runs"]=int(ep.get("normal_confirmation_runs",0))+1
        ep["episode_status"]="WEAKENING"
        ep["evidence"].append({"date":obs,"evidence_role":"CONTRADICTION","signal_state":state,"zscore":z})
        if ep["normal_confirmation_runs"]>=close_n:
            ep["episode_status"]="CLOSED"
            ep["closed_at_utc"]=run_time
            ep["falsification_status"]="NOT_FALSIFIED"
    else:
        ep["episode_status"]="WEAKENING"
        ep["evidence"].append({"date":obs,"evidence_role":"CONTEXT","signal_state":state,"zscore":z})
    ep["evidence"]=ep["evidence"][-100:]
    return ep

def main():
    sig_payload=read(SIG,{})
    gclri_hist=read(GCLRI_HIST,{"series":{}})
    reg=read(REG,{"close_rule":{"normal_confirmation_runs":2}})
    prior=read(OUT,{"episodes":[]})
    episodes=prior.get("episodes",[])
    by_signal={}
    for e in episodes:
        if e.get("episode_status") in ACTIVE_STATUSES:
            by_signal[e["signal_id"]]=e

    now=sig_payload.get("built_at_utc") or datetime.now(timezone.utc).isoformat()
    close_n=int(reg.get("close_rule",{}).get("normal_confirmation_runs",2))
    current_ids=set()
    for sig in sig_payload.get("signals",[]):
        sid=sig["signal_id"]; current_ids.add(sid)
        if sid in by_signal:
            update_episode(by_signal[sid],sig,now,gclri_hist,close_n)
        elif sig.get("signal_state") in TRIGGER:
            ep=make_episode(sig,now); episodes.append(ep); by_signal[sid]=ep

    # If a previously active signal disappears from current payload, do not close it automatically.
    for sid,ep in by_signal.items():
        if sid not in current_ids:
            ep["episode_status"]="WEAKENING"
            ep["confirmation_eligible"]=False
            ep["last_updated_utc"]=now
            ep["evidence"].append({"date":now[:10],"evidence_role":"CONTEXT","signal_state":"MISSING_FROM_PAYLOAD","zscore":None})

    active=[e for e in episodes if e.get("episode_status") in ACTIVE_STATUSES]
    payload={
      "schema_version":"0.8",
      "built_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_signal_built_at_utc":sig_payload.get("built_at_utc"),
      "production_eligible":False,
      "regime_change_authorized":False,
      "active_episode_count":len(active),
      "confirmation_eligible_episode_count":sum(bool(e.get("confirmation_eligible")) for e in active),
      "episodes":episodes,
      "governance":{
        "policy_response_is_not_independent_confirmation":True,
        "one_normal_run_does_not_close":True,
        "stress_scope_default":"UNRESOLVED",
        "policy_intervention_effect_default":"UNRESOLVED"
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    hist=read(HISTORY,{"schema_version":"0.8","runs":[]})
    hist.setdefault("runs",[]).append({
      "built_at_utc":payload["built_at_utc"],
      "source_signal_built_at_utc":payload["source_signal_built_at_utc"],
      "active_episode_count":payload["active_episode_count"],
      "confirmation_eligible_episode_count":payload["confirmation_eligible_episode_count"],
      "episode_states":[{"episode_id":e["episode_id"],"signal_id":e["signal_id"],"status":e["episode_status"],"latest_zscore":e.get("latest_zscore")} for e in episodes]
    })
    hist["runs"]=hist["runs"][-520:]
    HISTORY.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","episodes":len(episodes),"active":len(active)},ensure_ascii=False))

if __name__=="__main__": main()
