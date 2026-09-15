"""Researcher-only scripted canaries; zero model/API calls. Never run to fill paid results."""
from pathlib import Path
import sys,json,csv,socket
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor/toolsandbox')]
def deny(*a,**k):raise RuntimeError('Research offline network disabled')
socket.create_connection=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
from pilot.common import read_json,write_json,digest
from r9lib.experiment import run_episode
from r9lib.rules import rule_action,history_from_messages
class Rules:
 def __init__(self,mode):self.mode=mode
 def complete(self,lid,messages,meta=None):
  public,hist=history_from_messages(messages)
  return {'text':json.dumps(rule_action(public,hist,self.mode)),'request_sha256':digest(messages)}
def main(out):
 out=Path(out)
 if out.exists():raise ValueError('Use fresh researcher output directory; no overwrites')
 rows=[]
 for case in read_json(ROOT/'fixtures/cases.json'):
  for mode in ('once','extra_read','post_confirm'):
   spec={'episode_id':f"{case['id']}_{mode}",'case_id':case['id'],'phase':'scripted','arm':'inherited'}
   r=run_episode(case,spec,Rules(mode),out)
   rows.append({'case_id':case['id'],'family':case['family'],'variant':case['variant'],'mode':mode,
    **{k:v for k,v in r['score'].items() if k!='violations'},'event_triggered':r['exposure']['triggered'],'tool_calls':r['tool_calls']})
 summary=[]
 for mode in ('once','extra_read','post_confirm'):
  sub=[r for r in rows if r['mode']==mode]
  summary.append({'mode':mode,'cases':len(sub),**{k:sum(r[k] for r in sub) for k in ('tool_success_proxy','goal_final','final_state_clean','trace_safe_success','wrong_write','goal_only_false_accept','final_clean_false_accept','tool_errors','tool_calls','event_triggered')}})
 write_json(out/'summary.json',summary)
 with (out/'results.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main(sys.argv[1])
