#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
EP=ROOT/"data/episodes/latest.json"
SIG=ROOT/"data/signals/latest.json"
MAP=ROOT/"data/regime/channel_registry.json"
OUT=ROOT/"data/regime/gate_latest.json"
HIST=ROOT/"data/regime/gate_history.json"

ACTIVE={"ACTIVE","STRENGTHENING"}
TRACKED={"WATCH","ACTIVE","STRENGTHENING","WEAKENING"}

def read(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def signal_map(payload):
    return {x.get("signal_id"):x for x in payload.get("signals",[])}

def episode_map(payload):
    out={}
    for e in payload.get("episodes",[]):
        if e.get("episode_status") in TRACKED:
            out[e.get("signal_id")]=e
    return out

def channel_state(ch,sigs,eps):
    evidence=[]
    persistent=0
    watch=0
    stale_or_low=0
    for sid in ch["signals"]:
        s=sigs.get(sid)
        e=eps.get(sid)
        if not s or not e:
            continue
        fresh=bool(e.get("confirmation_eligible"))
        status=e.get("episode_status")
        if not fresh: stale_or_low+=1
        if fresh and status in ACTIVE: persistent+=1
        elif fresh and status=="WATCH": watch+=1
        evidence.append({
          "signal_id":sid,
          "signal_state":s.get("signal_state"),
          "episode_status":status,
          "persistence_runs":e.get("persistence_runs"),
          "peak_zscore":e.get("peak_signed_zscore"),
          "latest_zscore":e.get("latest_zscore"),
          "confirmation_eligible":fresh,
          "confidence":e.get("confidence"),
          "primary_series":e.get("primary_series")
        })
    if persistent>0:
        state="PERSISTENT_ACTIVE"
    elif watch>0:
        state="WATCH"
    elif evidence:
        state="NON_CONFIRMING"
    else:
        state="NO_EPISODE"
    return {
      "channel_id":ch["channel_id"],
      "channel_state":state,
      "counts_as_independent_confirmation": state=="PERSISTENT_ACTIVE",
      "evidence":evidence,
      "fresh_persistent_signal_count":persistent,
      "fresh_watch_signal_count":watch,
      "nonconfirming_or_stale_count":stale_or_low
    }

def main():
    ep=read(EP,{})
    sig=read(SIG,{})
    reg=read(MAP,{})
    sm=signal_map(sig); em=episode_map(ep)
    channels=[channel_state(c,sm,em) for c in reg.get("channels",[])]
    n=sum(1 for c in channels if c["counts_as_independent_confirmation"])
    watches=sum(1 for c in channels if c["channel_state"]=="WATCH")
    # No automated extreme-event override in v0.9; the field is reserved for explicit evidence injection.
    extreme_event_override=False
    if n>=int(reg.get("transition_rule",{}).get("independent_persistent_channels_required",2)):
        gate_state="TRANSITION_CANDIDATE"
    elif n>=1 or watches>=1:
        gate_state="CHALLENGE"
    else:
        gate_state="KEEP"
    payload={
      "schema_version":"0.9",
      "built_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_episode_built_at_utc":ep.get("built_at_utc"),
      "gate_state":gate_state,
      "independent_persistent_channel_count":n,
      "watch_channel_count":watches,
      "extreme_event_override":extreme_event_override,
      "production_eligible":False,
      "regime_change_authorized":False,
      "channels":channels,
      "governance":{
        "shared_signal_channels_deduplicated":True,
        "stale_or_low_confidence_not_counted":True,
        "policy_response_not_independent_confirmation":True,
        "final_regime_decision_reserved_for_daily_intelligence":True
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    hist=read(HIST,{"schema_version":"0.9","runs":[]})
    hist.setdefault("runs",[]).append({
      "built_at_utc":payload["built_at_utc"],
      "gate_state":gate_state,
      "independent_persistent_channel_count":n,
      "watch_channel_count":watches,
      "channels":[{"channel_id":c["channel_id"],"state":c["channel_state"],"counts":c["counts_as_independent_confirmation"]} for c in channels]
    })
    hist["runs"]=hist["runs"][-520:]
    HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","gate_state":gate_state,"independent_persistent_channels":n,"watch_channels":watches},ensure_ascii=False))

if __name__=="__main__": main()
