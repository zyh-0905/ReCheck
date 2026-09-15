"""Reproduce original execution-test failures, without enabling external services."""
import json
from pathlib import Path
import native_study as ns
from tool_sandbox.common.execution_context import ExecutionContext,new_context,get_current_context,DatabaseNamespace as DB
from tool_sandbox.roles.execution_environment import ExecutionEnvironment
from tests.roles import execution_environment_test as original
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.common.execution_context import RoleType as R
from tool_sandbox.roles.base_role import BaseRole


def diagnostics():
 output={}
 for name in ('test_execution_environment_syntax_error','test_invalid_parallel_tool_call'):
  with new_context(ExecutionContext()):
   env=ExecutionEnvironment();failed=False
   try:getattr(original,name)(env)
   except AssertionError:failed=True
   output[name]={'original_assertion_failed':failed,'last_messages':[dict(sender=str(x.sender),recipient=str(x.recipient),content=x.content,tool_call_exception=x.tool_call_exception,tool=x.openai_function_name) for x in env.get_messages()[-2:]]}
 s=ns.NativeSession(ns.definitions()['multi']['turn_on_wifi_low_battery_mode'],allowed=ns.WALKTHROUGH_TOOLS)
 BaseRole.add_messages([
  Message(sender=R.AGENT,recipient=R.EXECUTION_ENVIRONMENT,content='print(repr(set_low_battery_mode_status(on=False)))',openai_function_name='set_low_battery_mode_status'),
  Message(sender=R.AGENT,recipient=R.EXECUTION_ENVIRONMENT,content='print(repr(set_wifi_status(on=True)))',openai_function_name='set_wifi_status')])
 s.env.respond()
 msgs=BaseRole.get_messages()[-2:]
 output['local_parallel_dependency']={'response_tools':[m.openai_function_name for m in msgs],'errors':[m.tool_call_exception for m in msgs],
     'settings':s.rows(DB.SETTING),'first_failed':bool(msgs[0].tool_call_exception),'first_tool':msgs[0].openai_function_name}
 return output
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(diagnostics(),indent=2))
