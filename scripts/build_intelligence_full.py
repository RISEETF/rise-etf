#!/usr/bin/env python3
"""Versioned, evidence-bound daily research report; no autonomous rule promotion."""
from copy import deepcopy
from datetime import date
import hashlib
import json

from build_intelligence_research import build as research, finite
from update_intelligence_portal import read_json, write_json

POLICY = 'BOUNDED_RESEARCH_V1'
DATED_POLICY = 'DATED_OBSERVATIONS_V1'
# This is a publication coverage rule, not a modification of source freshness.
# Legacy 1.1 excluded only the dollar. 1.2 displays all valid fetched observations with their dates.
OPTIONAL_CONTEXT = {'DTWEXBGS'}
UNASSESSED = ('macro_absorption_level', 'macro_absorption_headroom',
              'corporate_absorption_level', 'corporate_headroom', 'fiscal_stress',
              'credit_stress_current', 'credit_stress_forward', 'market_liquidity',
              'funding_liquidity', 'energy_stress', 'energy_reliability', 'energy_adaptation', 'flow_state')


def valid_dated_value(row, asof):
    try:
        observed = date.fromisoformat(row['observation_date'])
        return (observed <= date.fromisoformat(asof) and finite(row.get('value')) and
                row.get('data_state') in {'CURRENT', 'STALE'})
    except (KeyError, TypeError, ValueError):
        return False


def basis(series_id):
    # FRED VIXCLS metadata: Daily, Close. Rates, spot oil and macro series are observations.
    return '종가' if series_id == 'VIXCLS' else '관측값'


def dated_context(inputs, rows):
    result=[]
    for item in rows:
        key=item['series_id']; row=inputs['market']['series'][key]
        history=inputs['market_history']['series'][key]
        previous=history[-2] if len(history)>1 else None
        change=None
        if (previous and finite(previous.get('value')) and
                previous.get('date','') < row['observation_date']):
            try:
                date.fromisoformat(previous['date'])
                change={'prior_observation_date': previous['date'], 'prior_value': previous['value'],
                        'change': row['value']-previous['value'], 'unit': row['unit']}
            except ValueError:
                pass
        result.append({**item, 'value': row['value'], 'unit': row['unit'],
                       'asof_label': f"{row['observation_date']} {basis(key)} 기준",
                       'age_calendar_days': (date.fromisoformat(inputs['asof_date'])-date.fromisoformat(row['observation_date'])).days,
                       'use': 'DATED_CONTEXT_ONLY', 'prior_change': change})
    return result


def coverage(inputs, version='1.2'):
    blockers, excluded = [], []
    for error in inputs['publication_blockers']:
        key = error.partition(':')[2]
        row = inputs['market'].get('series', {}).get(key, {})
        try:
            age = (date.fromisoformat(inputs['asof_date']) - date.fromisoformat(row['observation_date'])).days
            permitted = (error == 'STALE_OR_UNAVAILABLE:' + key and key in OPTIONAL_CONTEXT and
                         0 <= age <= 14 and finite(row.get('value')) and
                         row.get('data_state') in {'CURRENT', 'STALE'})
        except (KeyError, ValueError, TypeError):
            permitted = False
        if version == '1.2':
            history = inputs.get('market_history', {}).get('series', {}).get(key, [])
            last = history[-1] if history else {}
            permitted = (error == 'STALE_OR_UNAVAILABLE:' + key and
                         key in inputs['series_registry'] and
                         inputs['market'].get('status') == 'SUCCESS' and not inputs['market'].get('errors') and
                         valid_dated_value(row, inputs['asof_date']) and
                         last.get('date') == row.get('observation_date') and
                         last.get('value') == row.get('value'))
        if permitted:
            excluded.append({'series_id': key, 'observation_date': row['observation_date'],
                             'reason': ('관측 지연: 최신 달러 판단 및 교차확인에서 제외' if version == '1.1' else
                                        '기준일 관측 수준·과거 변화 설명에 사용; 오늘의 신호·동시점 교차확인에는 미사용')})
        else:
            blockers.append(error)
    return blockers, excluded


def compose(inputs, prior, version='1.2'):
    blockers, excluded = coverage(inputs, version)
    scoped = deepcopy(inputs)
    scoped['publication_blockers'] = blockers
    draft = research(scoped)
    excluded_ids = {x['series_id'] for x in excluded}
    usable = {x['signal_id'] for x in draft['signals'] if x['usable_for_research']}
    decisions = []
    for signal in inputs['signals']['signals']:
        if signal['signal_id'] not in usable:
            continue
        changes = []
        for row in signal['details']:
            if row['series_id'] in excluded_ids:
                raise ValueError('excluded series used by decision')
            move = row.get('horizon_move')
            if not finite(move) or not finite(row.get('zscore')):
                continue
            unit = inputs['market']['series'][row['series_id']]['unit']
            magnitude = f"{move * 100:+.2f}bp" if unit == 'Percent' else f"{move:+.6g} (엔진 정의 변화량)"
            changes.append(f"{row['series_id']} {row['observation_date']}: {row['horizon_observations']}관측 변화 {magnitude}, Z={row['zscore']:.2f}")
        if not changes:
            continue
        decisions.append({
            'signal_id': signal['signal_id'], 'status': signal['signal_state'],
            'series_ids': [r['series_id'] for r in signal['details']],
            'what_changed': '; '.join(changes),
            'confidence': '기존 신호 품질 ' + str(signal.get('confidence', 'UNRESOLVED')) + ' · 전망 확률 아님',
            'transmission': '금리 변화에 대한 만기·듀레이션 노출을 우선 점검' if signal['signal_id'].startswith('SIG-RATE') else '해당 채널의 독립 확인 자료와 실제 ETF 노출을 추가 점검',
            'counterargument': '단일 채널 변화는 거시 원인을 식별하지 못한다. 같은 원천을 공유하는 신호는 독립 확인이 아니다.',
            'falsification': '다음 신규 관측에서 같은 방향의 변화가 유지되는지, 반대 방향 변화와 독립 채널의 반증이 나타나는지 확인',
            'routing': '03 매크로 검증 → 04 투자자 수급 → 05 ETF 노출 확인',
        })
    active = [r for r in decisions if r['status'] in {'WATCH', 'ACTIVE_CANDIDATE'}]
    normal = [r['signal_id'] for r in decisions if r['status'] == 'NORMAL']
    counter = ('현재 변화탐지 기준 NORMAL: ' + ', '.join(normal) + '. 동반 급변 신호가 없다는 뜻이며 위험 부재를 뜻하지 않는다.'
               if normal else '독립 정상 채널의 반대증거가 충분하지 않다. 확정적 시장 해석을 보류한다.')
    matches = [{
        'name': r['name'], 'code': r['code'], 'priority': '조사 후보 · 추천 아님',
        'angle': r['internal_discussion_topic'], 'counter': r['required_check'],
        'basis': r['basis'], 'inventory_asof': r['inventory_asof'], 'signal_id': r['signal_id'],
    } for r in draft['rise_research_candidates']]
    reference = prior.get('regime_reference_date', prior['asof_date'])
    snapshot = {
        'schema_version': version, 'snapshot_type': 'FULL', 'report_mode': POLICY if version == '1.1' else DATED_POLICY,
        'asof_date': inputs['asof_date'], 'current_regime': prior['current_regime'],
        'regime_reference_date': reference, 'regime_assessment': 'CARRIED_FORWARD_NOT_RECONFIRMED',
        'regime_confidence': None, 'regime_confidence_reason': '승인된 최신 확률 산출 모형 없음. 과거 점수를 이월하지 않음.',
        'regime_change_candidate': '신규 레짐 판정 보류', 'regime_change_status': 'WATCH' if active else 'NONE',
        'top_change': active[0]['what_changed'] if active else '사용 가능한 기존 신호에서 신규 WATCH/ACTIVE_CANDIDATE 없음. 시장 불변을 뜻하지 않음.',
        'top_risk': '달러 최신 분석 제외; 금리·신용·수급의 독립 확인 전 레짐 전환 판단 보류' if excluded else '신호 변화만으로 거시 원인·투자자 수급·레짐 전환을 확정하지 않음',
        **{k: 'UNRESOLVED' for k in UNASSESSED},
        'assessment_gaps': {k: '해당 종합판단의 승인된 최신 산출 근거가 없어 미산정' for k in UNASSESSED},
        'top_rise_matches': matches, 'rise_match_status': 'NAME_ONLY_RESEARCH' if matches else 'NO_VERIFIED_MATCH',
        'product_candidates': [], 'product_assessment': '수요·경쟁상품 중복·편입 실현가능성 미검증: 신규 제안 및 출시 점수 보류',
        'framework_updates': [], 'production_eligible': False,
        'regime_history_update': {'prior_state': prior['current_regime'], 'today_state': prior['current_regime'], 'transition_gate_crossed': False},
        'key_triggers': draft['next_actions'][:2] + ['새 관측일의 지속성, 신용·자금조달·변동성 채널의 독립 확인'],
        'no_action': ['지연 달러 자료의 최신 증거 사용 금지', '레짐·프레임워크·매매 권한 승격 금지', '상품명 일치만으로 투자 권유 또는 신상품 출시 결정 금지'],
        'coverage': {'policy': POLICY, 'state': 'PARTIAL' if excluded else 'CURRENT_INPUTS', 'excluded': excluded, 'blockers': blockers},
        'observations': draft['observations'], 'decision_board': decisions,
        'rise_inventory_evidence': {k: inputs['rise_inventory'].get(k) for k in ('source_id','observed_on','raw_sha256')},
        'strongest_counterevidence': counter,
        'full_report_path': f"reports/{inputs['asof_date']}.html", 'report_status': 'PUBLISHED',
    }
    if version == '1.2':
        contexts = dated_context(inputs, excluded)
        snapshot['coverage'] = {'policy': DATED_POLICY, 'state': 'DATED_INPUTS' if contexts else 'CURRENT_INPUTS',
                                'excluded': [], 'dated_context': contexts, 'blockers': blockers}
        snapshot['top_risk'] = '자료별 기준일이 다르므로 당일 변화·동시점 교차확인과 구분. 레짐·투자자 수급 판단은 별도 검증 필요.'
        if not active:
            snapshot['top_change'] = ('신선도 기준을 충족한 관측의 WATCH/ACTIVE_CANDIDATE 없음. 기준일 자료와 구분하며 시장 불변을 뜻하지 않음.'
                                      if decisions else '자료별 기준일 관측 수준을 보고합니다. 오늘의 신호 판단은 보류합니다.')
        snapshot['no_action'][0] = '기준일이 지난 자료를 오늘의 변화나 동시점 교차확인으로 해석하지 않음'
        snapshot['key_triggers'][0] = '원천별 새 관측을 확인하고 기준일·변화량 갱신'
        for row in snapshot['observations']:
            row['asof_label'] = f"{row['observation_date']} {basis(row['series_id'])} 기준"
            row['use'] = 'FRESH_RESEARCH' if row['fresh_for_report'] else 'DATED_CONTEXT_ONLY'
    text = render(snapshot)
    references = [{'url': r['source_url'], 'observation_date': r['observation_date'],
                   'claim': f"{r['series_id']} 관측값 {r['value']} {r['unit']}"}
                  for r in snapshot['observations'] if (r['fresh_for_report'] and r['series_id'] not in excluded_ids) or version == '1.2']
    if matches:
        references.append({'url': 'https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd',
                           'observation_date': inputs['rise_inventory']['observed_on'],
                           'claim': 'KRX 관측 RISE 종목코드와 상품명: 실제 보유자산 검증 아님'})
    return snapshot, text, references


def render(s):
    parts = [f"RISE Daily Intelligence — {s['asof_date']}\n자동 연구 보고서 · 투자권유/외부 마케팅 승인 자료 아님",
             '1. 오늘의 판단\n' + s['top_change'] + '\n' + s['top_risk'],
             '2. 근거 범위와 지연 자료\n' + s['coverage']['state'] + '\n' +
             ('\n'.join(f"{r['series_id']} ({r['observation_date']}): {r['reason']}" for r in s['coverage']['excluded']) or '등록 원천 신선도 통과. 분석 모형 검증 완료를 뜻하지 않음.'),
             f"3. 기존 레짐과 판정 경계\n{s['current_regime']}\n{s['regime_reference_date']} 기록 유지; 오늘 재확정한 판단 아님.\n{s['regime_confidence_reason']}\n레짐 전환 및 연구 규칙 승격 없음.",
             '4. 변화·전달경로·반증\n' + '\n\n'.join(
                 f"{r['signal_id']} / {r['status']}\n{r['what_changed']}\n{r['confidence']}\n전달: {r['transmission']}\n반론: {r['counterargument']}\n반증 점검: {r['falsification']}\n연구 경로: {r['routing']}" for r in s['decision_board']),
             '5. 가장 강한 반대증거와 대안 설명\n' + s['strongest_counterevidence'] + '\n금리 하락은 성장 둔화·물가 완화·포지션 조정 등 여러 설명과 양립한다. 현재 자료만으로 원인 우열을 확정하지 않는다.',
             '6. RISE ETF 연결과 기관 미팅 준비\nKRX ETF 일별매매정보 관측 목록 · 원천: https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd\n상품명 기반 조사 목록이며 실제 편입자산과 노출은 미확인. 매수 추천 순위 아님.\n' + ('\n'.join(
                 f"{r['code']} {r['name']} ({r['inventory_asof']}, {r['signal_id']})\n논의 주제: {r['angle']}\n확인 필요: {r['counter']}" for r in s['top_rise_matches']) or '신선한 목록과 사용 가능한 신호로 확인된 조사 후보 없음.'),
             '7. 수급·경쟁상품·신상품\n투자자 유형별 순유입·집중도·지속성 미검증. 가격 신호를 수급으로 대체하지 않음.\n동일 노출 경쟁상품의 보수·유동성·추적오차 비교 미완료.\n' + s['product_assessment'],
             '8. 종합평가 미산정 항목\n' + '\n'.join(f"{k}: {v}" for k,v in s['assessment_gaps'].items()),
             '9. 다음 확인과 하지 않을 일\n' + '\n'.join(s['key_triggers'] + s['no_action']),
             '10. 원천 관측 감사표\n' + '\n'.join(
                 f"{r['series_id']} | {r['observation_date']} | {r['value']} {r['unit']} | "
                 f"{'신선도 통과' if r['fresh_for_report'] else '최신 판단 제외'} | {r['source_url']}" for r in s['observations'])]
    if s['schema_version'] == '1.2':
        context_lines=[]
        for row in s['coverage']['dated_context']:
            line=f"{row['series_id']} — {row['asof_label']}: {row['value']} {row['unit']} (보고일 대비 {row['age_calendar_days']}일 전)"
            previous=row['prior_change']
            if previous:
                delta=(f"{previous['change']*100:+.2f}bp" if row['unit']=='Percent' else
                       f"{previous['change']:+.6g} {row['unit']}")
                line+=f" / 직전 {previous['prior_observation_date']} 관측 대비 {delta}"
            context_lines.append(line+'\n'+row['reason'])
        parts[1]='1. 기준일 자료와 현재 확인 가능한 변화\n'+s['top_change']+'\n'+s['top_risk']
        parts[2]='2. 자료 기준일\n지연 자료도 표시된 기준일의 수준과 과거 변화 설명에 활용합니다. 오늘의 변화로 간주하지 않습니다.\n'+('\n\n'.join(context_lines) or '등록 자료의 신선도 기준 충족. 각 관측일은 아래 감사표에 명시합니다.')
        if not s['decision_board']:
            parts[4]='4. 최신 신호 판단\n신선도와 원천 정합성을 함께 충족하는 판단 자료 없음. 기준일 관측 수준은 위에 제시합니다.'
        parts[-1]='10. 원천 관측 감사표\n'+'\n'.join(
            f"{r['series_id']} | {r['asof_label']} | {r['value']} {r['unit']} | "
            f"{'신선도 기준 충족' if r['fresh_for_report'] else '기준일 자료로 활용'} | {r['source_url']}" for r in s['observations'])
    return '\n\n'.join(parts) + '\n'


def generate(root, inputs):
    prior = read_json(root / 'intelligence/data/latest.json')
    snapshot, text, refs = compose(inputs, prior)
    # Semantic report content excludes run timestamps; identical evidence/analysis is unchanged.
    key = hashlib.sha256((json.dumps(snapshot, sort_keys=True, ensure_ascii=False, allow_nan=False) + text).encode()).hexdigest()
    package = root / 'data/intelligence/generated' / inputs['asof_date'] / key
    write_json(package / 'snapshot.json', snapshot)
    (package / 'report.txt').write_text(text, encoding='utf-8')
    write_json(package / 'evidence.json', {
        'asof_date': inputs['asof_date'], 'source_hashes': inputs['source_hashes'],
        'content_hashes': {n: hashlib.sha256((package/n).read_bytes()).hexdigest() for n in ('snapshot.json','report.txt')},
        'external_evidence': refs, 'revision_reason': '자동 보고서: 새 관측·신호·자료 범위 또는 작성 규칙 변경 반영; 이전 본문 보존',
    })
    return package
