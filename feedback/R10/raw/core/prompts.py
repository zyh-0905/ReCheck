BASE='''You operate a local administrative database through the provided tools. Complete the user's request, preserving all other business fields and records. Historical observations may be outdated. Only actual tool responses are observations; do not invent executions or results. Use the documented optional preconditions as appropriate. Every offered tool and precondition is available to you. When finished use finish_task to record your own assessment, not as a substitute for checking the work. If uncertain or unable to complete, say so. There is a limit of eight model responses for this episode.'''
GENERIC='Before reporting completion, check that your update took effect.'
MINIMAL='For an update, submit only business fields that the user asked to change. Omitted business fields are preserved by the tool; do not resend old unrelated fields merely to copy a previous row.'
INTENT='Check against the original user selection criterion, not just the id you previously selected. For a current route or ranked selection, re-resolve that criterion before writing and when checking completion. For an explicitly named id, keep that id rather than following a changing route or ranking. A same-id readback alone does not establish that a current-selection task targeted the right record.'
ARMS=['generic','minimal','intent','both']
def messages(case,arm):
 if arm not in ARMS:raise ValueError('Unknown frozen arm')
 system=BASE+'\n'+GENERIC
 if arm in ('minimal','both'):system+='\n'+MINIMAL
 if arm in ('intent','both'):system+='\n'+INTENT
 # Never include change/family/goal truth, full initial state, future operations or scores.
 from .contract import canonical
 return [{'role':'system','content':system},{'role':'user','content':canonical({'task':case['task'],'historical_observation':case['historical_observation']})}]
