#!/usr/bin/env python3
"""Cross-platform entry point. A real endpoint is contacted only by smoke/run."""
from __future__ import annotations
import argparse, getpass, os, sys
from pathlib import Path
from pilot.common import default_config,validate_config,read_json,write_json,freeze_run,utcnow,strict_json_object,run_lock
from pilot.client import JournalClient,RunStopped


def configure(path):
    if path.exists():raise ValueError('Config already exists. Edit it locally or choose --out with a new filename.')
    cfg=default_config()
    print('Do NOT paste an API key here. Only non-secret endpoint/model settings are saved.')
    cfg['base_url']=input('Base URL (usually ends with /v1): ').strip()
    cfg['model']=input('Exact model ID: ').strip()
    label=input('Provider label (optional): ').strip()
    if label:cfg['provider_label']=label
    field=input('Output limit field [max_tokens / max_completion_tokens] (default max_tokens): ').strip()
    if field:cfg['max_tokens_field']=field
    maxout=input('Output token limit (default 1024): ').strip()
    if maxout:cfg['max_output_tokens']=int(maxout)
    cap=input('Hard request cap per run folder (default 300): ').strip()
    if cap:cfg['max_requests']=int(cap)
    currency=input('Billing currency (blank = prices unknown): ').strip()
    if currency:
        cfg['prices']['currency']=currency
        cfg['prices']['input_per_million']=float(input('Input price per 1,000,000 tokens: '))
        cfg['prices']['output_per_million']=float(input('Output price per 1,000,000 tokens: '))
        v=input('Cached-input price per 1,000,000 (blank = use input price estimate): ').strip()
        if v:cfg['prices']['cached_input_per_million']=float(v)
        v=input('Estimated spend stop in that currency (blank = request cap only): ').strip()
        if v:cfg['max_estimated_spend']=float(v)
    if cfg['base_url'].startswith('http://'):
        cfg['local_no_auth']=input('Unauthenticated LOOPBACK endpoint? [y/N]: ').strip().lower()=='y'
    validate_config(cfg);write_json(path,cfg)
    print('Saved non-secret config:',path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('configure');p.add_argument('--out',type=Path,default=Path('config.local.json'))
    p=sub.add_parser('unlock');p.add_argument('--run',type=Path,required=True);p.add_argument('--confirm-stopped',action='store_true')
    p=sub.add_parser('doctor');p.add_argument('--config',type=Path,default=Path('config.local.json'))
    for command in ('smoke','run'):
        p=sub.add_parser(command);p.add_argument('--config',type=Path,default=Path('config.local.json'))
        p.add_argument('--out',type=Path,required=True)
        p.add_argument('--retry-failed-requests',action='store_true')
        p.add_argument('--retry-uncertain',action='store_true')
        if command=='run':
            p.add_argument('--study',choices=['recheck','repairlens-readiness'],required=True)
            p.add_argument('--units',type=int,default=4,help='streams for ReCheck, cases for replay readiness; pilot default 4')
            p.add_argument('--steps',type=int,default=8,help='ReCheck tasks per stream; ignored for replay readiness')
    p=sub.add_parser('summarize');p.add_argument('--run',type=Path,required=True)
    p=sub.add_parser('export');p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.cmd=='configure':configure(args.out);return 0
    if args.cmd=='unlock':
        if not args.confirm_stopped:raise ValueError('First confirm the old process is stopped, then add --confirm-stopped.')
        (args.run/'.run.lock').unlink(missing_ok=True)
        print('Writer lock removed. An interrupted HTTP request may still require --retry-uncertain.');return 0
    if args.cmd=='summarize':
        from pilot.report import summarize
        summarize(args.run);return 0
    if args.cmd=='export':
        from pilot.report import export
        manifest=read_json(args.run/'manifest.json')
        export(args.run,args.out,os.environ.get(manifest['config']['key_env'],''));return 0
    cfg=validate_config(read_json(args.config))
    if args.cmd=='doctor':
        import numpy as np
        from pilot.recheck import protocol
        print('Python:',sys.version.split()[0], '| numpy:',np.__version__)
        print('Protocol: non-streaming Chat Completions only; NO network request sent.')
        print('Configured model:',cfg['model'])
        print('Credential present in named environment variable:',bool(os.environ.get(cfg['key_env'])))
        print('Default ReCheck pilot logical calls:',protocol()['logical_calls'],'; configured hard attempt cap:',cfg['max_requests'])
        print('Default RepairLens READINESS calls: at most 40; not the RepairLens algorithm.')
        print('Prices unknown:',cfg['prices']['input_per_million'] is None)
        if cfg['backend_kind']!='live':print('WARNING: all outputs labelled SOFTWARE_TEST_NOT_RESEARCH.')
        return 0
    if args.cmd=='smoke':study='smoke';spec={'phase':'connectivity_only','logical_calls':1}
    elif args.study=='recheck':
        from pilot import recheck
        if not 1<=args.units<=20 or not 1<=args.steps<=40:raise ValueError('Pilot bound: units 1..20; steps 1..40')
        study='recheck';spec=recheck.protocol(args.units,args.steps)
    else:
        from pilot import readiness
        if not 1<=args.units<=20:raise ValueError('Pilot bound: units 1..20')
        study='repairlens_readiness';spec=readiness.protocol(args.units)
    needed=spec.get('logical_calls',spec.get('max_logical_calls',1))
    if needed>cfg['max_requests']:raise ValueError(f'Planned {needed} logical calls exceed the request cap; reduce pilot size or configure the cap before running.')
    with run_lock(args.out):
        freeze_run(args.out,cfg,study,spec)
        secret=os.environ.get(cfg['key_env'],'')
        if not secret and not cfg['local_no_auth']:
            secret=getpass.getpass('API key for this process only (hidden; not saved): ').strip()
            if not secret:raise ValueError('No credential entered; no request sent.')
        client=JournalClient(cfg,args.out,secret,args.retry_failed_requests,args.retry_uncertain)
        write_json(args.out/'status.json',{'state':'running','updated_utc':utcnow()})
        try:
            if args.cmd=='smoke':
                rec=client.complete('smoke/one',[{'role':'user','content':'Return exactly {"ok":true} as JSON.'}],{'phase':'connectivity'})
                try:ok=strict_json_object(rec['text'])=={'ok':True}
                except ValueError:ok=False
                write_json(args.out/'smoke_result.json',{'json_ok':ok,'requested_model':cfg['model'],
                    'returned_model':rec['response'].get('model'),'usage_present':bool(rec['response'].get('usage')),
                    'finish_reason':rec['response'].get('choices',[{}])[0].get('finish_reason')})
                if not ok:raise RunStopped('HTTP succeeded but the JSON smoke test failed or was truncated. Inspect the response before pilot.')
            elif study=='recheck':recheck.run(client,cfg,args.out,spec)
            else:readiness.run(client,cfg,args.out,spec)
            write_json(args.out/'status.json',{'state':'completed','updated_utc':utcnow(),'budget':client.budget()})
            print('Run completed. Summarize and export this entire directory.');return 0
        except (RunStopped,KeyboardInterrupt) as exc:
            message='KeyboardInterrupt' if isinstance(exc,KeyboardInterrupt) else str(exc)
            write_json(args.out/'status.json',{'state':'paused','updated_utc':utcnow(),'reason':message,'budget':client.budget()})
            print('PAUSED:',message,file=sys.stderr);return 2

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,FileNotFoundError) as exc:
        print('CONFIGURATION ERROR:',str(exc),file=sys.stderr);sys.exit(2)
