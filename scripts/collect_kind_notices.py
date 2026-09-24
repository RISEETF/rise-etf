"""Read KIND lifecycle notices; never infer current legal status from absence."""
import datetime as dt
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

HOST = 'https://kind.krx.co.kr'
SEARCH = HOST + '/disclosure/disclosurebystocktype.do'
VIEWER = HOST + '/common/disclsviewer.do'


def plain(value):
    value = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', value, flags=re.S|re.I)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', value)).split())


def decode(raw):
    try:return raw.decode('utf-8')
    except UnicodeDecodeError:return raw.decode('cp949')


def parse_page(page, expected_page):
    count = re.search(r'전체\s*<em>([\d,]+)</em>건\s*:\s*<strong>(\d+)</strong>/(\d+)', page)
    if not count or int(count[2]) != expected_page:
        raise ValueError('KIND_PAGINATION_INVALID')
    total, _, pages = [int(v.replace(',', '')) for v in count.groups()]
    if pages > 20 or (total and not pages):raise ValueError('KIND_PAGE_LIMIT')
    rows=[]
    for block in re.findall(r'<tr\b[^>]*>(.*?)</tr>', page, re.S):
        notice=re.search(r'openDisclsViewer\(\s*[\'"](\d{14})[\'"]', block)
        if not notice:continue
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>', block, re.S)
        if len(cells)!=5:raise ValueError('KIND_ROW_FORMAT')
        date=plain(cells[1]);dt.datetime.strptime(date,'%Y-%m-%d %H:%M')
        stock=re.search(r'etfisusummary_open\([\'"]([0-9A-Z]+)[\'"]',cells[2])
        if not stock:raise ValueError('KIND_STOCK_ID_MISSING')
        rows.append({'receipt_id':notice[1], 'kind_stock_id':stock[1],
                     'published_at':date.replace(' ','T')+':00+09:00',
                     'name':plain(cells[2]),'title':plain(cells[3]),'publisher':plain(cells[4])})
    if len(rows)!=min(100,max(0,total-(expected_page-1)*100)):
        raise ValueError('KIND_INCOMPLETE_PAGE')
    return rows,total,max(1,pages)


def category(title):
    if any(word in title for word in ('정정','취소','철회')):return 'REVISION_REVIEW'
    if title.startswith('신규상장('):return 'LISTING_NOTICE'
    if title.startswith('상장폐지('):return 'DELISTING_NOTICE'
    if '상장폐지' in title:return 'DELISTING_REVIEW'
    return None  # 기준가격 안내 and quantity changes are not lifecycle decisions.


def viewer_fields(page, receipt):
    ids=re.findall(r'name="acptNo"[^>]*value="(\d{14})"',page)
    if not ids or any(v!=receipt for v in ids):raise ValueError('KIND_RECEIPT_MISMATCH')
    heading=re.search(r'<h1\b[^>]*>(.*?)</h1>',page,re.S)
    code=re.search(r'\(([0-9A-Z]{6})\)\s*$',plain(heading[1])) if heading else None
    select=re.search(r'<select\b[^>]*id="mainDoc"[^>]*>(.*?)</select>',page,re.S)
    options=re.findall(r'<option\b[^>]*value=[\'"](\d{14})\|[^\'"]*[\'"][^>]*>(.*?)</option>',select[1],re.S) if select else []
    if not code or not options:raise ValueError('KIND_VIEWER_IDENTITY_MISSING')
    return code[1], options


def document_fields(body, kind, code):
    text=plain(body)
    codes=set(re.findall(r'(?:단축코드|종목코드)\s*[:：]?\s*A?([0-9A-Z]{6})(?![0-9A-Z])',text))
    if codes!={code}:return None,'BODY_IDENTITY_REVIEW'
    if kind not in ('LISTING_NOTICE','DELISTING_NOTICE'):return None,'NOTICE_REVIEW_REQUIRED'
    label='상장일' if kind=='LISTING_NOTICE' else '상장폐지일'
    dates=re.findall(r'(?<![가-힣])'+label+r'\s*[:：]?\s*(\d{4})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})',text)
    normalized={dt.date(int(y),int(m),int(d)).isoformat() for y,m,d in dates}
    if len(normalized)!=1:return None,'EFFECTIVE_DATE_REVIEW'
    return normalized.pop(),'NOTICE_CODE_DATE_VERIFIED'


def fetch(url, directory, data=None):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.netloc!='kind.krx.co.kr':raise ValueError('KIND_URL_INVALID')
    request=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode() if data else None,
                                  headers={'User-Agent':'RISE-Research-Collector/1.0'})
    with urllib.request.urlopen(request,timeout=25) as response:
        if urllib.parse.urlparse(response.geturl()).netloc!='kind.krx.co.kr':raise ValueError('KIND_REDIRECT_INVALID')
        raw=response.read()
    digest=hashlib.sha256(raw).hexdigest()
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/(digest+'.html')
    if not path.exists():path.write_bytes(raw)
    return decode(raw),{'url':url,'request':data,'sha256':digest}


def collect(asof, previous=None, raw_dir='var/kind-raw'):
    now=dt.datetime.now(dt.timezone.utc).isoformat(); start=asof-dt.timedelta(days=30)
    if (previous or {}).get('window_end','')>asof.isoformat():raise ValueError('KIND_DATE_REGRESSION')
    evidence=[]; found={}
    for term in ['신규상장','상장폐지']:
        page=1; expected_total=None; seen=set()
        while True:
            query={'method':'searchDisclosureByStockTypeEtfSub','forward':'disclosurebystocktype_etf_sub',
                   'currentPageSize':'100','pageIndex':str(page),'fromDate':start.isoformat(),
                   'toDate':asof.isoformat(),'etfIsuSrtNm':'RISE','reportNm':term,'orderMode':'','orderStat':''}
            content,source=fetch(SEARCH,raw_dir,query);evidence.append(source)
            rows,total,pages=parse_page(content,page)
            if expected_total is not None and total!=expected_total:raise ValueError('KIND_TOTAL_CHANGED')
            expected_total=total
            for row in rows:
                key=row['receipt_id']+':'+row['kind_stock_id']
                if key in seen:raise ValueError('KIND_DUPLICATE_PAGE_ROW')
                seen.add(key)
                if not start.isoformat()<=row['published_at'][:10]<=asof.isoformat():raise ValueError('KIND_DATE_OUTSIDE_QUERY')
                if not row['name'].startswith('RISE '):raise ValueError('KIND_BRAND_FILTER_MISMATCH')
                kind=category(row['title'])
                if kind:found[key]={**row,'kind':kind,'search_sha256':source['sha256']}
            if page>=pages:
                if len(seen)!=total:raise ValueError('KIND_TOTAL_MISMATCH')
                break
            page+=1
    events={r['event_id']:dict(r) for r in (previous or {}).get('events',[])}
    for key,row in found.items():
        viewer_url=VIEWER+'?'+urllib.parse.urlencode({'method':'search','acptno':row['receipt_id']})
        viewer,source=fetch(viewer_url,raw_dir);code,options=viewer_fields(viewer,row['receipt_id'])
        if row['kind_stock_id'] != code[:5]:raise ValueError('KIND_STOCK_ID_MISMATCH')
        sources=[source]; effective=None; status='DOCUMENT_HISTORY_REVIEW'
        if len(options)==1:
            doc=options[0][0]
            path,source=fetch(VIEWER+'?'+urllib.parse.urlencode({'method':'searchContents','docNo':doc}),raw_dir);sources.append(source)
            links=re.findall(r'https://kind\.krx\.co\.kr/external/[^\'"<>\s]+\.htm',path)
            if len(set(links))!=1:raise ValueError('KIND_BODY_LINK_INVALID')
            body,source=fetch(links[0],raw_dir);sources.append(source)
            effective,status=document_fields(body,row['kind'],code)
            if row['publisher']!='유가증권시장본부':effective,status=None,'NOTICE_REVIEW_REQUIRED'
        old=events.get(key,{})
        history=old.get('versions', [])[:]
        if old and any(old.get(k)!=v for k,v in [('code',code),('effective_date',effective),('verification',status),('sources',sources)]):
            history.append({k:old.get(k) for k in ['code','effective_date','verification','sources','last_checked_at']})
        events[key]={**row,'event_id':key,'code':code,'effective_date':effective,
                     'verification':status,'viewer_url':viewer_url,'sources':sources,
                     'first_seen_at':old.get('first_seen_at',now),'last_checked_at':now,'versions':history}
    for key,event in events.items():
        event['in_latest_search']=key in found
    return {'status':'SUCCESS','attempted_at':now,'last_success_at':now,
            'window_start':start.isoformat(),'window_end':asof.isoformat(),
            'scope':'RISE_TITLE_SEARCH_ROLLING_30_DAYS_NOT_FULL_LIFECYCLE',
            'current_legal_status':'NOT_AUTOMATICALLY_ASSIGNED',
            'search_sources':evidence,'events':sorted(events.values(),key=lambda e:(e['published_at'],e['event_id']),reverse=True)}


def refresh(asof, previous=None, raw_dir='var/kind-raw'):
    try:return collect(asof,previous,raw_dir)
    except Exception as exc:
        return {**(previous or {}),'status':'FAILED','attempted_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                'reason':type(exc).__name__,'events':(previous or {}).get('events',[])}
