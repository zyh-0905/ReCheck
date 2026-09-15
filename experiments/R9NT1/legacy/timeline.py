"""One fixed external update at a declared observable boundary, not answer-adaptive.
After first qualifying successful pre-write read returns, update occurs before the
next model turn. The read's genuine return stays unchanged. Never inject after a
first primary write when the actor skipped that read; record unexposed cases.
"""
from .native import NativeSession,jcopy
class Timeline:
 def __init__(self,case,replay_events=None):
  self.case=case;self.session=NativeSession(case['snapshot']);self.events=[]
  self.fired=False;self.missed=False;self.replay_events=replay_events
  if case['variant']=='pre_relevant':self._fire()
 def world(self):return self.session.world()
 def snapshot(self):return self.session.snapshot()
 def _replay_context(self):
  from contextlib import nullcontext
  if self.replay_events is None:return nullcontext()
  from .replay import replay_nondeterminism
  if len(self.events)>=len(self.replay_events):raise ValueError('Unexpected replay event')
  return replay_nondeterminism(self.replay_events[len(self.events)])
 def _fire(self):
  if self.fired or self.missed:return
  ops=self.case['unrelated_operations'] if self.case['variant']=='post_unrelated' else self.case['relevant_operations']
  for name,args in ops:
   before=self.world()
   with self._replay_context():value=self.session.admin(name,args)
   self.events.append({'scope':'environment','tool':name,'arguments':jcopy(args),
    'response':{'ok':True,'value':value,'error':None},'before_world':before,'after_world':self.world()})
  self.fired=True
 def _qualifies(self,name,args,response):
  if name not in self.case['anchors'] or not response['ok']:return False
  if self.case['family']=='person':
   return type(response['value']) is list and any(r.get('name')==self.case['contract']['name'] for r in response['value'])
  if self.case['family']=='reminder':
   return type(response['value']) is list and any(r.get('content')==self.case['contract']['title'] for r in response['value'])
  return True
 def call(self,name,args):
  pending=self.case['variant'].startswith('post_') and not self.fired and not self.missed
  with self._replay_context():r=self.session.call(name,args)
  self.events.append(self.session.events[-1])
  if pending:
   # Even a failed primary mutation closes this scheduled pre-write opportunity.
   if name==self.case['primary_mutator']:self.missed=True
   elif self._qualifies(name,args,r):self._fire()
  return r
 def exposure(self):
  return {'scheduled':self.case['variant']!='stable','triggered':self.fired,
   'missed_before_primary_write':self.missed,
   'reason':'triggered' if self.fired else ('control' if self.case['variant']=='stable' else ('write_before_anchor' if self.missed else 'no_qualifying_read'))}
