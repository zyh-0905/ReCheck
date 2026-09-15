
"""R2 online experiment. This module never imports the offline evaluator."""
import copy,time
from pathlib import Path
import numpy as np
from pilot.common import digest,read_json,write_json
from pilot.recheck import World,public_task,valid_plan,ask
from .protocol import make_cases,solution,choose,policy_spec
from .session import write_once

def run(client,cfg,root,spec):
    root=Path(root);cases=make_cases(spec)
    write_once(root/"private/recheck_cases.json",cases)
    public_spec=policy_spec(spec);dps={};build=[]
    for cell in spec["streams"]:
        key=tuple(cell["probe_price"])
        if key not in dps:
            tic=time.perf_counter();dps[key]=solution({"probe_price":cell["probe_price"]},public_spec)
            build.append({"probe_price":list(key),"dp_build_seconds":time.perf_counter()-tic})
    if not (root/"controller_metadata.json").exists():
        write_json(root/"controller_metadata.json",{"dp_build":build,"label":"local controller construction, not API cost"})
    for case,cell in zip(cases,spec["streams"]):
        sid=case["stream"];world=World(case["cents"]);world.set_modes(case["initial_modes"])
        try:
            receipts=[world.probe(j) for j in range(2)]
            initial,error,icall=ask(client,cfg,f"r2/rc/{sid}/shared_initial","memory_write",{
              "calibration":receipts,"instructions":'The amount calibration is one major currency unit. Its raw amount is either 1 or 100. The only time calibration row has time 0. count_before(0) includes it iff the upper endpoint is inclusive. Write {"amount_divisor":1 or 100,"endpoint_inclusive":true or false}.'},
              {"study":"r2_recheck","stream":sid,"phase":"shared_prefix"})
            from pilot.common import is_number
            ok=(isinstance(initial,dict) and set(initial)=={"amount_divisor","endpoint_inclusive"}
                and is_number(initial.get("amount_divisor")) and initial["amount_divisor"] in (1,100)
                and type(initial.get("endpoint_inclusive")) is bool)
            memory={"amount_divisor":initial.get("amount_divisor") if ok else None,
                    "endpoint_inclusive":initial.get("endpoint_inclusive") if ok else None,"checked_at":[0,0]}
            prefix={"initial_writer":initial,"initial_parse_error":error,"schema_valid":ok,
                    "calibration":receipts,"writer_logical_id":icall["logical_id"],"initial_probe_count":2}
            write_once(root/"prefixes"/f"rc_{sid}.json",prefix)
            states={m:{"ages":np.zeros(2,int),"memory":copy.deepcopy(memory)} for m in spec["methods"]}
            permutation=np.random.default_rng(spec["order_seed"]+sid).permutation(spec["methods"]).tolist()
            dp=dps[tuple(cell["probe_price"])]
            for t,task in enumerate(case["tasks"]):
                world.set_modes(task["modes"])
                shift=t%len(permutation);order=permutation[shift:]+permutation[:shift]
                for order_index,m in enumerate(order):
                    st=states[m];st["ages"]+=1;before=st["ages"].copy();tic=time.perf_counter()
                    refresh=choose(m,st["ages"],task["type"],spec["steps"]-t,dp,{"probe_price":cell["probe_price"]},public_spec)
                    planning=time.perf_counter()-tic;receipts=[];tic=time.perf_counter()
                    for j in np.flatnonzero(refresh):
                        j=int(j);rc=world.probe(j);receipts.append(rc)
                        if j==0:st["memory"]["amount_divisor"]=int(rc["raw_amount"])
                        else:st["memory"]["endpoint_inclusive"]=bool(rc["returned_count"])
                        st["memory"]["checked_at"][j]=t+1;st["ages"][j]=0
                    probing=time.perf_counter()-tic
                    path=root/"records"/f"rc_{sid:03d}_{t:03d}_{m}.json"
                    if path.exists():continue
                    stem=f"r2/rc/{sid}/{t}/{m}"
                    view={"task":public_task(task),"memory":copy.deepcopy(st["memory"]),"current_round":t+1,
                      "tool_descriptions":{"sum_amount":"Returns raw sum; divide by the remembered amount_divisor to obtain major units.",
                      "count_before":"Counts rows relative to integer bound. Use remembered endpoint_inclusive. Desired cutoff is inclusive.",
                      "count_all":"Counts all orders. No argument."},
                      "instructions":'Return {"amount_divisor":1 or 100 or null,"time_bound":integer or null}. Use null for unused fields. Do not request extra probes.'}
                    plan,pe,pc=ask(client,cfg,stem+"/plan","plan",view,
                        {"study":"r2_recheck","stream":sid,"step":t,"method":m,"phase":"plan","order_index":order_index})
                    tic=time.perf_counter();tool,ntool=world.execute(task,plan);tool_seconds=time.perf_counter()-tic
                    ans,ae,ac=ask(client,cfg,stem+"/answer","answer",{
                      "task":public_task(task),"memory":copy.deepcopy(st["memory"]),"executed_plan":plan,"tool_result":tool,
                      "instructions":'Return {"total":number or null,"count":integer or null}. Include both keys; unused values must be null. On tool error return both null. For totals divide the raw sum using the executed plan.'},
                      {"study":"r2_recheck","stream":sid,"step":t,"method":m,"phase":"answer","order_index":order_index})
                    write_once(path,{"study":"r2_recheck","stream":sid,"step":t,"method":m,"order_index":order_index,
                       "task_type":task["type"],"prefix_sha256":digest(prefix),"worker_view":view,"worker_view_sha256":digest(view),
                       "ages_before":before.tolist(),"probed_channels":np.flatnonzero(refresh).tolist(),"probe_receipts":receipts,
                       "probe_count":len(receipts),"model_probe_cost":float(sum(np.array(cell["probe_price"])[refresh])),
                       "planning_seconds":planning,"probe_seconds":probing,"tool_seconds":tool_seconds,"task_tool_calls":ntool,
                       "plan":plan,"plan_json_error":pe,"plan_schema_valid":valid_plan(plan,task),
                       "tool_result":tool,"answer":ans,"answer_json_error":ae,"logical_calls":[pc["logical_id"],ac["logical_id"]]})
        finally:world.close()
