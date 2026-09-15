"""Self-contained JSON decision requests; no private state in messages."""
from .core import canonical,MAX_STEPS
from .native import public_input,tool_docs
BASE='''You are operating a local simulated phone and reminder environment. Complete the user's request using only the listed tools. Tools change simulated state; do not assume a change happened merely because you planned it. Respect exact user intent and avoid unrelated writes. Historical memory and supplied observations are past tool observations, not guaranteed current facts. You may query the available tools. Return exactly one JSON object and no code fence: {"action":"tool","name":"listed_tool_name","arguments":{...}} OR {"action":"finish","summary":"brief factual summary"}. Never execute Python or invent tools. Each tool action is one turn. Finish only when you have enough evidence to report completion or to state you cannot complete it. Total limit is six decisions, including finish. All contacts/messages are synthetic; no real services are connected.'''
VERIFY=''' Before a write addressed by a person's identity or by a reminder description, resolve the currently matching entity with its read tool instead of relying only on an old identifier. When the user explicitly requests a literal phone number, use that number rather than redirecting it to a person's updated number. For settings, use current observations or explicit tool feedback to establish the relevant preconditions; an error or success says only what the tool contract supports.'''
def messages(case,method,history):
 public=public_input(case,method)
 # There is no method label, condition label, private goal, admin event or world snapshot here.
 return [{'role':'system','content':BASE+(VERIFY if method=='memory_verify' else '')},
         {'role':'user','content':canonical({**public,'available_tools':tool_docs(case['family']),
                'action_history':history,'decisions_remaining':MAX_STEPS-len(history)})}]
SMOKE_MESSAGES=[{'role':'system','content':'Return only a JSON object.'},{'role':'user','content':'Return {"ok":true} exactly.'}]
