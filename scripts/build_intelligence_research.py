#!/usr/bin/env python3
"""Deterministic evidence brief; never an approved FULL report or recommendation."""
from datetime import date
import hashlib
import json
import math
from urllib.parse import quote

from update_intelligence_portal import write_json

# Explicit name matching is a research queue, not holdings/exposure verification.
LINKS = {
    'SIG-RATE-001': ('미국채', '장기 금리 변화에 따른 듀레이션 민감도 설명 준비',
                     '듀레이션·환헤지·파생 구조를 공식 자료로 확인'),
    'SIG-RATE-002': ('국채', '수익률곡선 변화에 따른 만기별 위험 설명 준비',
                     '국가·만기·통화가 해당 신호와 일치하는지 확인'),
    'SIG-CREDIT-001': ('회사채', '신용스프레드 변화와 이자수익의 상충 관계 점검',
                       '신용등급·만기·유동성·국가 차이를 확인'),
}
GAPS = [
    '레짐 신뢰도·흡수력 점수: 승인된 산출 근거가 없어 미산정',
    '투자자 수급: 투자자 유형별 원천·시장폭·집중도·지속성 검증 필요',
    '경쟁상품: 동일 노출의 보수·유동성·추적오차·자금유입 비교 미완료',
    '신상품: 기존 상품 중복·수요·지수 구현·거래비용 검증 전 점수 및 출시 판단 보류',
    '정식 FULL 보고서: 외부 근거와 반론을 검토한 최종 판단 패키지 필요',
]


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def build(inputs):
    today = date.fromisoformat(inputs['asof_date'])
    observations = []
    for key, row in sorted(inputs['market'].get('series', {}).items()):
        try:
            age = (today - date.fromisoformat(row['observation_date'])).days
            fresh = (row.get('data_state') == 'CURRENT' and
                     0 <= age <= inputs['series_registry'][key]['stale_after_days'] and
                     finite(row.get('value')))
        except (KeyError, TypeError, ValueError):
            fresh = False
        observations.append({
            'series_id': key, 'name': row.get('name'),
            'observation_date': row.get('observation_date'),
            'value': row.get('value') if finite(row.get('value')) else None,
            'unit': row.get('unit'), 'fresh_for_report': fresh,
            'source_url': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + quote(key, safe=''),
        })
    observed = {row['series_id']: row for row in observations}
    signals = []
    for signal in inputs['signals'].get('signals', []):
        details = signal.get('details', [])
        # A signal is usable only when all contributing observations match the current source.
        usable = bool(details) and all(
            d.get('series_id') in observed and observed[d['series_id']]['fresh_for_report'] and
            d.get('observation_date') == observed[d['series_id']]['observation_date'] and
            finite(d.get('latest_value')) and d['latest_value'] == observed[d['series_id']]['value']
            for d in details)
        if inputs['publication_blockers']:
            usable = False  # a blocked global vintage cannot support a new marketing conclusion
        signals.append({
            'signal_id': signal['signal_id'], 'state': signal.get('signal_state'),
            'direction': signal.get('direction'), 'strongest_series': signal.get('strongest_series'),
            'usable_for_research': usable, 'production_eligible': False,
        })
    inventory = inputs['rise_inventory']
    matches = []
    try:
        inventory_current = 0 <= (today - date.fromisoformat(inventory['observed_on'])).days <= 5
    except (KeyError, TypeError, ValueError):
        inventory_current = False
    if inventory_current:
        for signal in signals:
            if not signal['usable_for_research'] or signal['state'] not in {'WATCH', 'ACTIVE_CANDIDATE'}:
                continue
            rule = LINKS.get(signal['signal_id'])
            if not rule:
                continue
            token, message, verification = rule
            for product in sorted(inventory.get('products', []), key=lambda x: x['code']):
                if (product.get('status') == 'OBSERVED' and token in product['name'] and
                        product.get('last_observed_on') == inventory['observed_on']):
                    matches.append({'code': product['code'], 'name': product['name'],
                                    'inventory_asof': inventory['observed_on'],
                                    'signal_id': signal['signal_id'], 'matched_name_token': token,
                                    'basis': 'NAME_ONLY_UNVERIFIED_EXPOSURE',
                                    'internal_discussion_topic': message, 'required_check': verification})
    gate = inputs['regime_gate']
    return {
        'schema_version': '1.0', 'document_type': 'RESEARCH_DRAFT',
        'asof_date': inputs['asof_date'], 'production_eligible': False,
        'publication_eligible': False, 'source_hashes': inputs['source_hashes'],
        'publication_blockers': inputs['publication_blockers'],
        'observations': observations, 'signals': signals,
        'gate_observation': {'state': gate.get('gate_state'),
                             'independent_persistent_channels': gate.get('independent_persistent_channel_count'),
                             'usable': not bool(inputs['publication_blockers'])},
        'validation_state': inputs['validation'].get('validation_state'),
        'rise_inventory_current': inventory_current, 'rise_research_candidates': matches,
        'unresolved': GAPS,
        'counterchecks': [
            '같은 원천 시계열을 공유하는 신호는 독립된 시장 확인으로 합산하지 않는다.',
            '금리 하락만으로 성장 둔화와 인플레이션 완화를 구분할 수 없다. 신용·수급 등 독립 근거가 필요하다.',
            '관측 지연·수정과 서로 다른 관측일은 동일 시점 시장 움직임으로 해석하지 않는다.',
        ],
        'next_actions': [
            '차단 원천의 새 관측값을 수집하고 전체 체인을 다시 실행',
            '후보 ETF 공식 투자설명서의 실제 노출·환헤지·듀레이션 확인',
            'FULL 패키지의 수치·외부 근거·반론 검토 후 기존 게시 검증 실행',
        ],
    }


def render(draft):
    lines = [f"# RISE 자동 연구 초안 — {draft['asof_date']}",
             '검토용 · 정식 보고서 아님 · 투자판단 및 외부 마케팅 사용 불가',
             '\n## 게시 차단 사유', *(draft['publication_blockers'] or ['원천 차단 없음; FULL 검토 별도 필요']),
             '\n## 원천 관측 (발행일과 구분)']
    for row in draft['observations']:
        lines.append(f"- {row['series_id']} | {row['observation_date']} | {row['value']} {row['unit']} | "
                     f"{'신선도 통과' if row['fresh_for_report'] else '최신 근거로 사용 불가'} | {row['source_url']}")
    lines += ['\n## 기존 엔진 신호 (새 판단 아님)']
    for row in draft['signals']:
        lines.append(f"- {row['signal_id']}: {row['state']} / {row['direction']} / "
                     f"연구 연결 {'가능' if row['usable_for_research'] else '보류'}")
    lines += [f"관문 원본: {draft['gate_observation']} / 검증: {draft['validation_state']}",
              '\n## RISE 상품 조사 목록 (상품명 일치만 확인; 추천 순위 아님)']
    for row in draft['rise_research_candidates']:
        lines.append(f"- {row['code']} {row['name']} ({row['inventory_asof']}) ← {row['signal_id']}: "
                     f"{row['internal_discussion_topic']}; 필요 확인: {row['required_check']}")
    if not draft['rise_research_candidates']:
        lines.append('현재 검증된 연결 후보 없음. 입력 차단·목록 관측일·신호 상태를 확인한다.')
    for title, key in [('반론·오판 점검', 'counterchecks'), ('미완료 평가', 'unresolved'), ('다음 조치', 'next_actions')]:
        lines += ['\n## ' + title, *('- ' + item for item in draft[key])]
    return '\n'.join(lines) + '\n'


def save(root, draft):
    body = render(draft)
    payload = json.dumps(draft, ensure_ascii=False, sort_keys=True, allow_nan=False)
    fingerprint = hashlib.sha256((payload + '\n' + body).encode()).hexdigest()
    target = root / 'data/intelligence/research' / draft['asof_date'] / fingerprint
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / 'draft.json', draft)
    (target / 'report.md').write_text(body, encoding='utf-8')
    # Content-addressed paths preserve same-date revisions and make identical reruns idempotent.
    result = {'status': 'RESEARCH_DRAFT', 'path': str(target.relative_to(root)), 'sha256': fingerprint}
    write_json(root / 'data/intelligence/research_latest.json', result)
    return result
