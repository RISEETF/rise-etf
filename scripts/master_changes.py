"""Report official-list membership changes, never infer legal delisting."""
import hashlib
import json
from update_daily import write_json


def record_changes(master_dir, previous, current):
    path=master_dir/'changes.json'
    history=json.loads(path.read_text())['events'] if path.exists() else []
    def members(snapshot):
        return {r.get('detail_id') or r['code']:r for r in snapshot['products']+snapshot.get('pending_products',[])}
    before=members(previous) if previous else {}
    after=members(current)
    events=[]
    if previous:
        for code in sorted(set(after)-set(before)):
            events.append({'kind':'ADDED_TO_OFFICIAL_LIST','code':after[code]['code'],'detail_id':code,'name':after[code]['name'],
                           'listed_on':after[code]['listed_on']})
        for code in sorted(set(before)-set(after)):
            events.append({'kind':'REMOVED_FROM_OFFICIAL_LIST','code':before[code]['code'],'detail_id':code,'name':before[code]['name'],
                           'delisting_confirmed':False})
        for code in sorted(set(before)&set(after)):
            if before[code]['name']!=after[code]['name']:
                events.append({'kind':'NAME_CHANGED','code':after[code]['code'],'detail_id':code,'name':after[code]['name'],
                               'previous_name':before[code]['name']})
            if before[code]['code']!=after[code]['code']:
                events.append({'kind':'CODE_UPDATED','code':after[code]['code'],'detail_id':code,'name':after[code]['name'],
                               'previous_code':before[code]['code']})
    for event in events:
        event.update(detected_at=current['retrieved_at'],source_effective_date=current['effective_date'],
                     previous_source_sha256=previous['source_sha256'],source_sha256=current['source_sha256'])
        event['event_id']=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()
    known={e['event_id'] for e in history}
    history.extend(e for e in events if e['event_id'] not in known)
    result={'status':'OFFICIAL_LIST_CHANGES_NOT_DELISTING_CONFIRMATION',
            'checked_at':current['retrieved_at'],'effective_date':current['effective_date'],
            'source_sha256':current['source_sha256'],'instrument_count':len(current['products']),
            'source_product_count':len(after),
            'previous_count':len(before) if previous else None,'events':history,
            'last_check_change_count':len(events)}
    write_json(path,result)
    return result
