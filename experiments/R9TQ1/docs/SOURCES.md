# Official interface references (read 2026-09-13)
1. DeepSeek Tool Calls — https://api-docs.deepseek.com/guides/tool_calls/
2. DeepSeek Thinking Mode — https://api-docs.deepseek.com/guides/thinking_mode/
3. DeepSeek Chat Completions API — https://api-docs.deepseek.com/api/create-chat-completion/

Observed documentation at this review:
- tools/function definitions, assistant.tool_calls, matched role=tool replies are the native flow.
- Tools-bearing subsequent requests preserve the returned reasoning_content; it is not rewritten as user/tool evidence.
- tool_choice=required and a forced function are documented as unsupported in thinking mode.
  Therefore use auto, not forced or required.
- strict schema is a separate beta configuration; this qualification does not use it.
- The current model enum/example lists deepseek-flash. This is an EXPLICIT new request label
  relative to prior deepseek-v4-flash; neither returned strings nor fingerprints authenticate weights.
- No parallel_tool_calls flag is sent (not present in the read Chat Completions reference).
- JSON mode is removed: assistant content is normal narrative, never a source of executable actions.
The docs do not certify this user's endpoint behavior. Qualification has not run on their endpoint.
Only parsed, named, schema-checked native calls are dispatched. More than four, duplicate IDs,
malformed arguments, unknown names or response metadata drift pause before dispatch.
We preserve all parts of a returned assistant message needed by the documented flow, including
content/reasoning_content/tool_calls. We do not synthesize assistant tool invocations.
