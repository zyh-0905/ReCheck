"""Same six legal tools for every arm. Optional guards are standard baselines."""
def obj(props,required):return {'type':'object','properties':props,'required':required,'additionalProperties':False}
def typ(t,description=''):return {'type':t,**({'description':description} if description else {})}
def tool(name,description,props,required):return {'type':'function','function':{'name':name,'description':description,'parameters':obj(props,required)}}
TOOLS=[
 tool('resolve_service','Read the CURRENT route for a service and join its current configuration. Returns record plus selection_token. The route is a separate resource; a configuration row version does not protect it.',{'service':typ('string')},['service']),
 tool('get_config','Read one configuration by exact id. This does NOT resolve a service route.',{'id':typ('string')},['id']),
 tool('update_config','Update only supplied configuration business fields; omitted fields are preserved. No write occurs on a failed precondition. Optional expected_version checks only this row. Optional service+expected_selection_token atomically checks the route and target within the SAME SQLite transaction. It is available to every agent; do not invent tokens.',{
  'id':typ('string'),'max_attempts':typ('integer'),'owner':typ('string'),'note':typ('string'),'label':typ('string'),
  'expected_version':typ('integer'),'service':typ('string'),'expected_selection_token':typ('string')},['id']),
 tool('select_batch','Read the CURRENT READY batch for a lane with units >= min_units, highest priority then ascending id. Returns the chosen record plus selection_token. Selection depends on other rows; the chosen row version alone cannot protect ranking.',{'lane':typ('string'),'min_units':typ('integer')},['lane','min_units']),
 tool('get_batch','Read a batch by exact id. This DOES NOT check if it is still the current eligible selection.',{'id':typ('string')},['id']),
 tool('update_batch','Update only supplied business fields; omitted fields are preserved. Optional expected_version checks only this row. Optional lane_query+min_units_query+expected_selection_token atomically checks the current ranked eligible selection and target in the SAME transaction. A failed precondition writes nothing. Query before retrying; no automatic retry.',{
  'id':typ('string'),'ready_after':typ('integer'),'lane':typ('string'),'state':typ('string'),'priority':typ('integer'),'units':typ('integer'),'carrier':typ('string'),'note':typ('string'),
  'expected_version':typ('integer'),'lane_query':typ('string'),'min_units_query':typ('integer'),'expected_selection_token':typ('string')},['id'])]
SCHEMAS={t['function']['name']:t['function']['parameters'] for t in TOOLS}
# This reporting tool has no database effect and does not inspect hidden scoring.
TOOLS.append(tool('finish_task','Record your own completion assessment and end the episode. This tool does NOT verify the database, approve earlier writes, or reveal scores. Put it last if using a batch. Use completed only if you believe the whole request, including preservation of other fields, was met.',{'status':{'type':'string','enum':['completed','incomplete','uncertain']},'message':typ('string')},['status','message']))
