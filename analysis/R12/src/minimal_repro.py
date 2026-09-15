"""Independent tiny driver using original ToolSandbox classes, no LLM or helper."""
import copy,json,attrs
from tool_sandbox.common.execution_context import DatabaseNamespace as DB,ExecutionContext,RoleType,set_current_context
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.roles.base_role import BaseRole
from tool_sandbox.roles.execution_environment import ExecutionEnvironment
from tool_sandbox.scenarios.single_tool_call_scenarios import named_single_tool_call_scenarios

def run():
    scenario=copy.deepcopy(named_single_tool_call_scenarios(ToolBackend.DEFAULT)['wifi_off'])
    ctx=ExecutionContext.from_dict(scenario.starting_context.to_dict(serialize_console=False))
    set_current_context(ctx);execution=ExecutionEnvironment()
    rows=ctx.get_database(DB.SANDBOX,get_all_history_snapshots=True,drop_sandbox_message_index=False).to_dicts()
    for row in rows:
        if row['sender']==RoleType.SYSTEM and row['recipient']==RoleType.EXECUTION_ENVIRONMENT:
            execution.respond(ending_index=row['sandbox_message_index'])
    events=[]
    for code in ('set_wifi_status(on=False)','set_wifi_status(on=True)'):
        BaseRole.add_messages([Message(sender=RoleType.AGENT,recipient=RoleType.EXECUTION_ENVIRONMENT,content=code)])
        execution.respond();reply=BaseRole.get_messages()[-1]
        assert reply.tool_call_exception is None,reply.tool_call_exception
        events.append({'code':code,'setting':ctx.get_database(DB.SETTING).to_dicts()[0]})
    BaseRole.add_messages([Message(sender=RoleType.AGENT,recipient=RoleType.USER,content='Wifi is turned off'),
                         Message(sender=RoleType.USER,recipient=RoleType.AGENT,content='Done.',conversation_active=False)])
    score=attrs.asdict(scenario.evaluation.evaluate(ctx,max_turn_count=scenario.max_messages))
    final=ctx.get_database(DB.SETTING).to_dicts()[0]
    assert score['similarity']==1.0
    assert final['wifi'] is True
    result={'kind':'SCRIPTED_REPRO_NOT_MODEL','official_evaluation':score,'final_wifi':final['wifi'],'terminal_goal_holds':False,'events':events}
    print(json.dumps(result,indent=2));return result
