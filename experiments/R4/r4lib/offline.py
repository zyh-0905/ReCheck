"""Finite known-model diagnostics; no live labels, world sampling or model calls."""
from itertools import product
from statistics import mean
from . import protocol
from .model import Solver,METHODS


def coupling_counterexample():
    # Exact arithmetic witness, not a new maximum-coverage theorem.
    return {'channels':[0,1,2],'independent_singleton_costs':[2,2,2],
       'independent_sum':6,'step_cap':4,'independent_all_is_feasible':False,
       'pair_singletons_cost':4,'one_pair_packet_cost':3,
       'pass':6>4 and 3<4,'claim':'Independent actions need a joint feasibility/coverage decision; all methods must receive the same packet catalogue.'}


def preflight(p):
    cells={c['condition']:c for c in p['streams']};rows=[]
    for name,cell in cells.items():
        s=Solver(protocol.spec(cell,p));v={m:mean(s.evaluate(m,p['steps'],(1,1,1),q,p['episode_budget']) for q in range(3)) for m in METHODS}
        actual=tuple([cell['actual_hazard']]*3)
        realized_model={m:mean(s.evaluate(m,p['steps'],(1,1,1),q,p['episode_budget'],actual) for q in range(3)) for m in METHODS}
        rows.append({'condition':name,'assumed_model_expectation_NOT_CURRENCY':v,
            'declared_actual_model_expectation_NOT_LLM':realized_model,
            'matched_exact_dominance':all(v['recheck_joint']<=val+1e-10 for val in v.values()),
            'rollout_base_bound_check':v['bundle_rollout']<=v['age_paced']+1e-10})
    stream_rows=[]
    for c in p['streams']:
        s=Solver(protocol.spec(c,p));types=protocol.task_types(c,p)
        states={m:((1,1,1),p['episode_budget']) for m in p['methods']};dif=0
        for t,q in enumerate(types):
            actions={}
            for m,(ages,b) in states.items():
                a=s.choose(m,p['steps']-t,ages,q,b);actions[m]=a
                states[m]=s.after(ages,b,a)
            dif+=actions['recheck_joint']!=actions['bundle_myopic']
        stream_rows.append({'stream':c['stream'],'condition':c['condition'],'action_differences':dif,
          'credits_remaining':{m:v[1] for m,v in states.items()}})
    witness=coupling_counterexample()
    return {'pass':witness['pass'] and all(r['matched_exact_dominance'] and r['rollout_base_bound_check'] for r in rows),
       'worlds_constructed':False,'new_model_calls':0,'conditions':rows,'streams':stream_rows,
       'counterexample':witness,'note':'Development chosen after R3; structural checks, not a win guarantee or public preregistration.'}


def factorial_report():
    p=protocol.load_protocol();g=p['offline_grid'];out=[]
    for b,h,rho,over in product(g['budgets'],g['hazards'],g['persistence'],g['overlap']):
        cell=dict(overlap=over,persistence=rho,price=.05)
        spec=protocol.spec(cell,p);spec['hazards']=[h]*3;s=Solver(spec)
        for mult in g['actual_multipliers']:
            actual=tuple([min(.5,h*mult)]*3)
            vals={m:mean(s.evaluate(m,p['steps'],(1,1,1),q,b,actual) for q in range(3)) for m in METHODS}
            out.append({'budget':b,'assumed_hazard':h,'actual_hazard':actual[0],'persistence':rho,'overlap':over,'values':vals})
    return {'label':'EXACT_FINITE_MODEL_NOT_LLM','cells':len(out),'all_cells_retained':True,'rows':out}
