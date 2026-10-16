#!/usr/bin/env python3
"""Hana prior-day final-notice USD/KRW midpoint; never relabel current quotes."""
import base64
import datetime as dt
import gzip
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from collect_series import positive
from update_daily import ROOT, write_json

SOURCE='HANA_FINAL_NOTICE'
URL='https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do'
FORM_URL='https://www.kebhana.com/cms/rate/wpfxd651_01i.do'
SEOUL=ZoneInfo('Asia/Seoul')


class Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag in ('th','td') and self.row is not None: self.cell=[tag,dict(attrs),[]]
    def handle_data(self,text):
        if self.cell is not None: self.cell[2].append(text)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            kind,attrs,parts=self.cell; self.row.append((kind,attrs,''.join(parts).strip()));self.cell=None
        if tag=='tr' and self.row is not None: self.rows.append(self.row);self.row=None


def metadata(page):
    text=' '.join(html.unescape(re.sub('<[^>]+>',' ',page)).split())
    date_pattern=r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일'
    base=re.search(r'기준일\s*:\s*'+date_pattern,text)
    notice=re.search(r'고시일시\s*:\s*'+date_pattern+r'\s*(\d{1,2})시\s*(\d{1,2})분\s*(\d{1,2})초\s*\((\d+)회차\)',text)
    if not base or not notice: raise ValueError('Missing notice date/time/sequence')
    parts=list(map(int,notice.groups()))
    if parts[6]<=0: raise ValueError('Invalid notice sequence')
    return dt.date(*map(int,base.groups())),dt.datetime(*parts[:6],tzinfo=SEOUL),parts[6]


def parse_notice(raw, requested_date, retrieved_at, finalized_before=None):
    requested=dt.date.fromisoformat(requested_date)
    retrieved=dt.datetime.fromisoformat(retrieved_at.replace('Z','+00:00'))
    if retrieved.utcoffset() is None or requested>=retrieved.astimezone(SEOUL).date():
        raise ValueError('Only previous local calendar dates may be final')
    page=raw.decode('utf-8') if isinstance(raw,bytes) else raw
    base_date,published,sequence=metadata(page)
    if not base_date<=requested or not base_date<=published.date() or (requested-base_date).days>10 or published>retrieved:
        raise ValueError('Returned notice date inconsistent with historical request')
    if finalized_before is None or not base_date<dt.date.fromisoformat(finalized_before):
        raise ValueError('Following bank reference date is not confirmed')
    parser=Table();parser.feed(page)
    headers=[r for r in parser.rows if r and r[0][0]=='th' and re.sub(r'\s','',r[0][2])=='통화']
    if len(headers)!=1: raise ValueError('Ambiguous FX table header')
    offset=0;rate_column=None
    for _,attrs,label in headers[0]:
        if re.sub(r'\s','',label)=='매매기준율': rate_column=offset
        offset+=int(attrs.get('colspan','1'))
    rows=[r for r in parser.rows if r and r[0][0]=='td' and ' '.join(r[0][2].split())=='미국 USD']
    if len(rows)!=1 or rate_column is None or len(rows[0])!=offset:
        raise ValueError('Missing or ambiguous USD midpoint row')
    return {'date':base_date.isoformat(),'base':'USD','quote':'KRW',
            'rate':positive(rows[0][rate_column][2].replace(',','')),'kind':SOURCE,
            'base_date':base_date.isoformat(),'notice_at':published.isoformat(),'notice_sequence':sequence,
            'requested_date':requested_date,'retrieved_at':retrieved_at}


def parse_bundle(raw, captured):
    bundle=json.loads(raw)
    if bundle.get('format')!='HANA_FINAL_NOTICE_V1' or not bundle.get('responses'):
        raise ValueError('Invalid Hana source bundle')
    current_date,current_at,_=metadata(bundle['current_notice']['body'])
    anchor_time=dt.datetime.fromisoformat(bundle['current_notice']['retrieved_at'])
    if not current_date<=current_at.date() or current_at>anchor_time or anchor_time>captured:
        raise ValueError('Invalid current bank date anchor')
    dates=set(); chosen={}
    for item in bundle['responses']:
        if item['requested_date'] in dates: raise ValueError('Duplicate requested date')
        dates.add(item['requested_date'])
        if dt.datetime.fromisoformat(item['retrieved_at'])>captured: raise ValueError('Response after capture')
        row=parse_notice(item['body'],item['requested_date'],item['retrieved_at'],current_date.isoformat())
        old=chosen.get(row['date'])
        if old is None or (row['notice_sequence'],row['retrieved_at'])>(old['notice_sequence'],old['retrieved_at']):
            chosen[row['date']]=row
    return [chosen[day] for day in sorted(chosen)]


def fetch_notice(day):
    # Official wpfxd651_01i.js switches pbldDvCd from 3 (current) to 0 (past final).
    form={'ajax':'true','curCd':'USD','pbldDvCd':'0' if day else '3',
          'inqKindCd':'1','requestTarget':'searchContentDiv'}
    if day: form.update(tmpInqStrDt=day,inqStrDt=day.replace('-',''))
    request=urllib.request.Request(URL,data=urllib.parse.urlencode(form).encode(),headers={
        'User-Agent':'RISE-research/0.2','Referer':FORM_URL,'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(request,timeout=30) as response: return response.read().decode('utf-8')


def capture(data_dir, fetcher=fetch_notice, now=None, pause=0.3):
    now=now or dt.datetime.now(dt.timezone.utc);today=now.astimezone(SEOUL).date()
    cid=now.strftime('%Y%m%dT%H%M%S%fZ')+'-'+SOURCE
    record={'schema_version':1,'capture_id':cid,'source_id':SOURCE,'source_url':URL,
            'retrieved_at':now.isoformat(),'kind':'FX','instrument_code':None,'publication_time':None,
            'price_basis':None,'currency':None,'rs_eligible':False,'observations':[]}
    try:
        anchor_body=fetcher(None)
        anchor_time=dt.datetime.now(dt.timezone.utc) if fetcher is fetch_notice else now
        bank_date,bank_at,_=metadata(anchor_body)
        if bank_date>today or bank_at>anchor_time: raise ValueError('Invalid bank date anchor')
        anchor={'body':anchor_body,'retrieved_at':anchor_time.isoformat()}
        prior=[]; prior_last=None
        for path in sorted((data_dir/'series/captures').glob('*-'+SOURCE+'.json'),reverse=True):
            candidate=json.loads(path.read_text())
            if candidate['status']!='CAPTURED': continue
            envelope=json.loads((data_dir/'raw/series'/f"{candidate['source_sha256']}.json").read_text())
            raw=gzip.decompress(base64.b64decode(envelope['content']))
            if hashlib.sha256(raw).hexdigest()!=candidate['source_sha256']: raise ValueError('Prior source hash mismatch')
            parse_bundle(raw,dt.datetime.fromisoformat(candidate['retrieved_at']))
            prior=json.loads(raw)['responses'];prior_last=candidate.get('last_date');break
        responses={r['requested_date']:r for r in prior if bank_date-dt.timedelta(days=100)<=dt.date.fromisoformat(r['requested_date'])<bank_date}
        for age in range(90,0,-1):
            day=(bank_date-dt.timedelta(days=age)).isoformat()
            if day in responses and age>7: continue
            body=fetcher(day)
            stamp=(dt.datetime.now(dt.timezone.utc) if fetcher is fetch_notice else now).isoformat()
            parse_notice(body,day,stamp,bank_date.isoformat())
            responses[day]={'requested_date':day,'retrieved_at':stamp,'body':body}
            if pause: time.sleep(pause)
        captured=dt.datetime.now(dt.timezone.utc) if fetcher is fetch_notice else now
        raw=json.dumps({'format':'HANA_FINAL_NOTICE_V1','current_notice':anchor,'responses':[responses[k] for k in sorted(responses)]},ensure_ascii=False).encode()
        rows=parse_bundle(raw,captured);digest=hashlib.sha256(raw).hexdigest()
        if prior_last and rows[-1]['date']<prior_last: raise ValueError('Hana coverage regressed')
        write_json(data_dir/'raw/series'/f'{digest}.json',{'sha256':digest,'encoding':'gzip+base64','content':base64.b64encode(gzip.compress(raw,mtime=0)).decode()})
        record.update(status='CAPTURED',quality='REFERENCE_ONLY',source_sha256=digest,
                      retrieved_at=captured.isoformat(),observations=rows,first_date=rows[0]['date'],last_date=rows[-1]['date'])
    except Exception as exc:
        record.update(status='FAILED',quality='UNUSABLE',error=f'{type(exc).__name__}: {exc}')
    target=data_dir/'series/captures'/f'{cid}.json'
    if target.exists(): raise ValueError('Capture collision')
    write_json(target,record)
    write_json(data_dir/'fx/hana_status.json',{k:record.get(k) for k in ('source_id','status','retrieved_at','first_date','last_date','error','capture_id')})
    return record


if __name__=='__main__':
    result=capture(ROOT/'data')
    print(json.dumps({k:result.get(k) for k in ('status','first_date','last_date','error')},ensure_ascii=False))
    raise SystemExit(0 if result['status']=='CAPTURED' else 1)
