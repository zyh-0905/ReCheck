"""A conservative two-stage contact-goal check; no LLM or native execution."""
import re
from corpus_audit import rebuild,goal
BACK=re.compile(r'\b(back|again|restore|revert)\b',re.I)
FRIEND=re.compile(r'\bfriends?\b',re.I)

def phase_check(sample):
 r=rebuild(sample); candidates=[u for u in r['users'] if u['turn']>0 and BACK.search(u['text']) and FRIEND.search(u['text'])]
 if not candidates:return {'boundary':None,'phase1':None,'phase2':None,'scoped_complete':None,'reason':'no_explicit_back_to_friend_user_boundary'}
 boundary=candidates[0]['turn']
 before=[p for p in r['points'] if p['turn']<boundary and p['kind']=='turn_end']
 final=r['points'][-1]['state'] if r['points'] else {}
 a=goal('phase_enemy',before[-1]['state'],r['initial']) if before else None
 b=goal('phase_friend',final,r['initial'])
 return {'boundary':boundary,'phase1':a,'phase2':b,'scoped_complete':None if a is None or b is None else a and b,'reason':'recorded_phase_boundary_only','boundary_text':candidates[0]['text']}
