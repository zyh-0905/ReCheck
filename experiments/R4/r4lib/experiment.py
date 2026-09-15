"""Frozen user-side execution. Gold evaluation is deliberately absent here."""
from pathlib import Path
import copy,json,time
from pilot.common import digest,strict_json_object,read_json,write_json
from . import protocol,worker,environment
from .model import Solver
from .session import write_once


def run(client,cfg,run_dir,p):
    root=Path(run_dir);cases=protocol.make_cases(p)
    write_once(root/'private/recheck_cases.json',cases)
    for cell,case in zip(p['streams'],cases):
        sid=cell['stream'];s=protocol.spec(cell,p)
        world=environment.World(case['rows']);world.set_modes(case['initial_modes'])
        receipts=world.initial_calibration();memory=environment.decode_receipts(receipts)
        prefix={'receipts':receipts,'memory':memory,'startup_channel_checks':3,'startup_credit_equivalent':6,
                'outside_runtime_budget':True,'source':'actual_fixture_calibration_not_LLM'}
        write_once(root/'prefixes'/f'api_{sid:03d}.json',prefix)
        # Separate solver caches prevent one method borrowing another method's planning work.
        states={m:{'ages':(0,0,0),'memory':copy.deepcopy(memory),
           'bank':environment.ProbeBudget(world,s['packets'],p['episode_budget'],s['step_cap']),
           'solver':Solver(s)} for m in p['methods']}
        for t,task in enumerate(case['tasks']):
            world.set_modes(task['modes'])
            for oi,m in enumerate(protocol.order(cell,p,t)):
                st=states[m];ages=tuple(a+1 for a in st['ages']);before=st['bank'].remaining
                tic=time.perf_counter();a=st['solver'].choose(m,p['steps']-t,ages,task['type'],before);pt=time.perf_counter()-tic
                tic=time.perf_counter();rr=st['bank'].read(a.ids);pbt=time.perf_counter()-tic
                st['memory'].update(environment.decode_receipts(rr));st['ages']=tuple(0 if j in a.cover else ages[j] for j in range(3))
                view=worker.make_view(task,st['memory']);messages=[{'role':cfg['instruction_role'],'content':worker.SYSTEM},
                  {'role':'user','content':json.dumps(view,ensure_ascii=False)}]
                reps=['primary','repeat'] if t==p['repeat_step'] and m in p['repeat_methods'] else ['primary']
                for rep in reps:
                    logical=f'r4/api/{sid}/{t}/{m}/{rep}'
                    meta={'study':'r4_recheck','stream':sid,'step':t,'method':m,'replicate':rep,'phase':'compile_workflow','order_index':oi}
                    call=client.complete(logical,messages,meta);plan=strict_json_object(call['text'])
                    tic=time.perf_counter();answer,trace=worker.execute(world,view,plan);tt=time.perf_counter()-tic
                    r={'study':'r4_recheck','stream':sid,'condition':cell['condition'],'step':t,'task_type':task['type'],
                       'method':m,'replicate':rep,'order_index':oi,'prefix_sha256':digest(prefix),'worker_view':view,
                       'memory_audit':copy.deepcopy(st['memory']),'ages_before':list(ages),'packet_ids':list(a.ids),
                       'coverage':list(a.cover),'probe_receipts':rr,'budget_before':before,'budget_after':st['bank'].remaining,
                       'credits_spent':a.cost if rep=='primary' else 0,'probe_count':len(a.ids) if rep=='primary' else 0,
                       'model_probe_cost':s['price']*a.cost if rep=='primary' else 0.,
                       'planning_seconds':pt if rep=='primary' else 0.,'probe_seconds':pbt if rep=='primary' else 0.,'tool_seconds':tt,
                       'task_tool_calls':len(trace),'plan':plan,'plan_schema_valid':worker.valid_plan(plan,view),
                       'tool_trace':trace,'answer':answer,'answer_source':'bounded API workflow and deterministic renderer',
                       'logical_calls':[logical],'repeat_budget_note':'Repeat inherits primary evidence, no additional probe debit'}
                    path=root/'records'/f'api_{sid:03d}_{t:03d}_{m}_{rep}.json'
                    if path.exists():
                        old=read_json(path);ignore={'planning_seconds','probe_seconds','tool_seconds'}
                        if {k:v for k,v in old.items() if k not in ignore}!={k:v for k,v in r.items() if k not in ignore}:raise ValueError('Immutable record changed')
                    else:write_once(path,r)
    if not (root/'controller_metadata.json').exists():
        write_json(root/'controller_metadata.json',{'controller_llm_calls':0,'hard_episode_budget':p['episode_budget'],
          'step_cap':p['step_cap'],'budget_unit':'abstract calibration credits, not currency',
          'timing':'Separate per-method solver caches; setup shared environment not charged as a method speedup.'})
