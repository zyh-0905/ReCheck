"""Real file-backed SQLite operations, two connections, explicit one-event scheduler.

Environment actions are controlled fixtures, not a measured production race.
Only tool-return values, NEVER full-world snapshots/labels, enter model messages.
"""
import copy,sqlite3,time
from pathlib import Path
from .contract import schema_check,ContractError
from .common import digest
from .schema import SCHEMAS

CONFIG_FIELDS=('label','max_attempts','owner','note')
BATCH_FIELDS=('lane','state','priority','units','ready_after','carrier','note')

class Store:
 def __init__(self,case,path):
  self.case=copy.deepcopy(case);self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  if self.path.exists():raise ValueError('Refuse to overwrite an existing database')
  self.agent=sqlite3.connect(self.path,isolation_level=None);self.agent.row_factory=sqlite3.Row
  self.environment=sqlite3.connect(self.path,isolation_level=None);self.environment.row_factory=sqlite3.Row
  self.agent.executescript('''CREATE TABLE routes(service TEXT PRIMARY KEY,config_id TEXT NOT NULL,version INTEGER NOT NULL);
   CREATE TABLE configs(id TEXT PRIMARY KEY,label TEXT NOT NULL,max_attempts INTEGER NOT NULL,owner TEXT NOT NULL,note TEXT NOT NULL,version INTEGER NOT NULL);
   CREATE TABLE batches(id TEXT PRIMARY KEY,lane TEXT NOT NULL,state TEXT NOT NULL,priority INTEGER NOT NULL,units INTEGER NOT NULL,ready_after INTEGER NOT NULL,carrier TEXT NOT NULL,note TEXT NOT NULL,version INTEGER NOT NULL);''')
  c=self.case;ids=[c['target_id'],c['alternate_id'],c['other_id']]
  if c['family']=='routing':
   for j,i in enumerate(ids):self.agent.execute('INSERT INTO configs VALUES(?,?,?,?,?,?)',(i,f'profile-{j}',2+j,'operator-old',f'keep-config-{j}',1))
   self.agent.execute('INSERT INTO routes VALUES(?,?,?)',(c['key'],ids[0],1))
  else:
   for j,i in enumerate(ids):self.agent.execute('INSERT INTO batches VALUES(?,?,?,?,?,?,?,?,?)',(i,c['key'],'READY' if j<2 else 'HELD',30-10*j if j<2 else 100,8,1800100000+j*60,'carrier-old',f'keep-batch-{j}',1))
  self.events=[];self.triggered=False;self.opportunity_closed=False;self.initial=self.world()
 def close(self):
  self.agent.close();self.environment.close()
 def world(self):
  return {t:[dict(r) for r in self.agent.execute(f'SELECT * FROM {t} ORDER BY '+('service' if t=='routes' else 'id'))] for t in ('routes','configs','batches')}
 def _one(self,conn,table,i):
  r=conn.execute(f'SELECT * FROM {table} WHERE id=?',(i,)).fetchone();return dict(r) if r else None
 def _route(self,conn,service):
  r=conn.execute('SELECT * FROM routes WHERE service=?',(service,)).fetchone()
  if r is None:return None
  r=dict(r);record=self._one(conn,'configs',r['config_id'])
  return {'service':service,'selection_token':digest({'service':service,'config_id':r['config_id'],'route_version':r['version']}),'record':record}
 def _selection(self,conn,lane,minimum):
  rows=[dict(r) for r in conn.execute("SELECT * FROM batches WHERE lane=? AND state='READY' AND units>=? ORDER BY priority DESC,id ASC",(lane,minimum))]
  if not rows:return None
  token=digest({'lane':lane,'min_units':minimum,'candidates':[{k:r[k] for k in ('id','lane','state','priority','units')} for r in rows]})
  return {'lane':lane,'min_units':minimum,'selection_token':token,'record':rows[0]}
 def _read(self,name,a):
  if name=='resolve_service':return self._route(self.agent,a['service'])
  if name=='select_batch':return self._selection(self.agent,a['lane'],a['min_units'])
  return self._one(self.agent,'configs' if name=='get_config' else 'batches',a['id'])
 def _update(self,name,a):
  table='configs' if name=='update_config' else 'batches';fields=CONFIG_FIELDS if table=='configs' else BATCH_FIELDS
  changes={k:a[k] for k in fields if k in a}
  if not changes:return {'ok':False,'error':'NO_FIELDS','value':None}
  # No transaction is held open while the model generates.
  self.agent.execute('BEGIN IMMEDIATE')
  try:
   row=self._one(self.agent,table,a['id'])
   if row is None:out={'ok':False,'error':'NOT_FOUND','value':None}
   elif 'expected_version' in a and row['version']!=a['expected_version']:out={'ok':False,'error':'ROW_VERSION_CONFLICT','value':None}
   else:
    related=('service','expected_selection_token') if table=='configs' else ('lane_query','min_units_query','expected_selection_token')
    present=[x in a for x in related];err=None
    if any(present) and not all(present):err='INCOMPLETE_PRECONDITION'
    elif all(present):
     sel=self._route(self.agent,a['service']) if table=='configs' else self._selection(self.agent,a['lane_query'],a['min_units_query'])
     if sel is None or sel['record']['id']!=a['id'] or sel['selection_token']!=a['expected_selection_token']:err='SELECTION_CONFLICT'
    if err:out={'ok':False,'error':err,'value':None}
    else:
     query=f'UPDATE {table} SET '+','.join(k+'=?' for k in changes)+',version=version+1 WHERE id=?'
     self.agent.execute(query,tuple(changes.values())+(a['id'],))
     out={'ok':True,'error':None,'value':{'id':a['id'],'version':row['version']+1,'updated_fields':sorted(changes)}}
   self.agent.execute('COMMIT');return out
  except BaseException:
   self.agent.execute('ROLLBACK');raise
 def _qualifying(self,name,a,value):
  if self.triggered or self.opportunity_closed or self.case['change']=='stable' or value is None:return False
  c=self.case
  return (name=='resolve_service' and c['family']=='routing' and a['service']==c['key']) or (name=='select_batch' and c['family']=='dispatch' and a['lane']==c['key'] and a['min_units']==4) or (name==('get_config' if c['family']=='routing' else 'get_batch') and a['id']==c['target_id'])
 def _change(self,anchor):
  c=self.case;before=self.world();con=self.environment;table='configs' if c['family']=='routing' else 'batches'
  con.execute('BEGIN IMMEDIATE')
  try:
   if c['change']=='irrelevant':con.execute(f'UPDATE {table} SET note=?,version=version+1 WHERE id=?',('unrelated-new-note',c['other_id']))
   elif c['change']=='protected':
    field,new=('owner','operator-new') if table=='configs' else ('carrier','carrier-new')
    con.execute(f'UPDATE {table} SET {field}=?,version=version+1 WHERE id=?',(new,c['target_id']))
   elif c['change']=='selection':
    if table=='configs':con.execute('UPDATE routes SET config_id=?,version=version+1 WHERE service=?',(c['alternate_id'],c['key']))
    else:con.execute('UPDATE batches SET priority=45,version=version+1 WHERE id=?',(c['alternate_id'],))
   else:raise ValueError('Unknown frozen event')
   con.execute('COMMIT')
  except BaseException:con.execute('ROLLBACK');raise
  self.triggered=True
  self.events.append({'index':len(self.events),'kind':'environment','after_read_index':anchor,'before':before,'after':self.world(),'change':c['change']})
 def call(self,name,args):
  before=self.world();t=time.perf_counter()
  try:
   if name not in SCHEMAS:raise ContractError('Unknown tool')
   schema_check(args,SCHEMAS[name])
   if name.startswith('update_'):
    self.opportunity_closed=True;out=self._update(name,args)
   else:
    val=self._read(name,args);out={'ok':val is not None,'error':None if val is not None else 'NOT_FOUND','value':val}
  except ContractError:out={'ok':False,'error':'ARGUMENT_SCHEMA','value':None}
  after=self.world();idx=len(self.events)
  self.events.append({'index':idx,'kind':'tool','name':name,'arguments':copy.deepcopy(args),'result':copy.deepcopy(out),'before':before,'after':after,'elapsed_seconds':time.perf_counter()-t})
  if out['ok'] and not name.startswith('update_') and self._qualifying(name,args,out['value']):self._change(idx)
  return out
