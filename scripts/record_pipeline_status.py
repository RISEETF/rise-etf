#!/usr/bin/env python3
"""Public workflow receipts, separate from source collection and valid snapshots."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from update_daily import ROOT, write_json


def record(data_dir, pipeline, stages, run_id, attempt='1', now=None):
    if pipeline not in {'master','series'} or not stages:
        raise ValueError('Unknown or empty pipeline')
    if not str(run_id).isdigit() or not str(attempt).isdigit():
        raise ValueError('Invalid workflow identity')
    if any(v not in {'success','failure','cancelled','skipped',''} for v in stages.values()):
        raise ValueError('Invalid step outcome')
    failed=next((k for k,v in stages.items() if v in {'failure','cancelled'}),None)
    complete=all(v=='success' for v in stages.values())
    value={'schema_version':1,'pipeline':pipeline,
           'finished_at':(now or dt.datetime.now(dt.timezone.utc)).isoformat(),
           'status':'SUCCESS' if complete else 'FAILED' if failed else 'INCOMPLETE',
           'failed_stage':failed,'stages':stages,'run_id':str(run_id),'run_attempt':str(attempt),
           'run_url':f'https://github.com/RISEETF/rise-etf/actions/runs/{run_id}',
           'note':'Workflow execution only; consult source status and snapshot effective date separately.'}
    directory=Path(data_dir)/'operations'
    write_json(directory/'runs'/f'{pipeline}-{run_id}-{attempt}.json',value)
    write_json(directory/f'{pipeline}.json',value)
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('pipeline',choices=['master','series'])
    args=parser.parse_args()
    record(ROOT/'data',args.pipeline,json.loads(os.environ['PIPELINE_STAGES']),
           os.environ['GITHUB_RUN_ID'],os.environ.get('GITHUB_RUN_ATTEMPT','1'))
