"""Software fixtures; never model research data."""
import json,copy
from pathlib import Path
from nt.common import read,write,sha,source_paths,digest
from nt.journal import Client
ROOT=Path(__file__).resolve().parents[1]
CASES=read(ROOT/'fixtures/cases.json');TOOLS=read(ROOT/'fixtures/tools.json');CONFIG=read(ROOT/'config.json')
def case(family='person',variant='stable'):
 return copy.deepcopy(next(c for c in CASES if c['family']==family and c['variant']==variant))
def spec(c,arm='inherited',phase='primary'):
 return {'episode_id':f'{phase}_{c["id"]}_{arm}','phase':phase,'case_id':c['id'],'arm':arm}
def native_call(name,args,ident='x'):
 return {'id':ident,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}
def reply(n,calls=None,final='Completed.',fingerprint='local_fixture'):
 return {'id':f'fixture_{n}','model':'deepseek-flash','system_fingerprint':fingerprint,'object':'chat.completion',
 'choices':[{'index':0,'finish_reason':'tool_calls' if calls else 'stop',
 'message':{'role':'assistant','content':None if calls else final,'reasoning_content':f'local fixture {n}, not model evidence','tool_calls':calls}}],
 'usage':{'prompt_tokens':100,'completion_tokens':30,'total_tokens':130,'completion_tokens_details':{'reasoning_tokens':12}}}
class SequenceWire:
 def __init__(self,sequence):self.seq=sequence;self.payloads=[];self.n=0
 def __call__(self,p):
  self.n+=1;self.payloads.append(copy.deepcopy(p));item=self.seq(self.n,p) if callable(self.seq) else self.seq[self.n-1]
  if isinstance(item,tuple):return item
  calls=None if item is None else [native_call(x[0],x[1],f'c{self.n}_{i}') for i,x in enumerate(item)]
  return 200,json.dumps(reply(self.n,calls)).encode()
def client(root,wire):return Client(CONFIG,root,TOOLS,'local-fixture-key-not-real',exchange=wire)
def freeze(root):write(root/'SOURCE_MANIFEST.json',{'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in source_paths(root)}})
