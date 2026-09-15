"""Conservative net-cost guard. It is NOT the RepairLens active scheduler.
A deployment must obtain upper/lower bounds without peeking at final repair costs.
"""
from pathlib import Path
import math
from pilot.common import read_json
ROOT=Path(__file__).resolve().parents[1]

def select_route(diagnosis_upper,remaining_repair_upper,direct_lower):
 for x in [diagnosis_upper,remaining_repair_upper,direct_lower]:
  if x is not None and (isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0):raise ValueError('Nonnegative finite costs required')
 if any(x is None for x in [diagnosis_upper,remaining_repair_upper,direct_lower]):return {'route':'direct_recompute','reason':'cost_bounds_unknown'}
 gain=direct_lower-diagnosis_upper-remaining_repair_upper
 return {'route':'diagnose_then_repair' if gain>0 else 'direct_recompute','certified_savings_under_supplied_bounds':gain,
         'reason':'Only conditional on externally valid cost bounds; not a learned efficacy claim'}

def prior_diagnostic():
 d=read_json(ROOT/'regression/repair_cost_inputs.json');g=d['groups'];f=g['full_regeneration/repair'];p=g['llm_selected_patch/repair'];s=g['llm_selected_patch/selection']
 return {'label':'RETROSPECTIVE_PRIOR_READINESS_NOT_NEW_REPAIRLENS_RESULTS','new_llm_calls':0,
         'currency_route':select_route(s['legacy_flat_USD_estimate'],p['legacy_flat_USD_estimate'],f['legacy_flat_USD_estimate']),
         'latency_route':select_route(s['latency_seconds'],p['latency_seconds'],f['latency_seconds']),
         'selection_cost_over_avoided_regeneration':s['legacy_flat_USD_estimate']/(f['legacy_flat_USD_estimate']-p['legacy_flat_USD_estimate']),
         'limitations':'Historical measured point costs are NOT prospective valid bounds. This diagnoses why the old route loses; it does not claim deployment safety, current prices, or new experimental improvement.'}
