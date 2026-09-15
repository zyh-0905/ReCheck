# R9TQ1 native structured tool qualification
Approved scope: following R9J1 review and user's 'continue', build the previously proposed
native tools/tool_calls interface and a small bounded qualification, not a new research method.
Alternatives: keep patching action JSON (rejected: two concrete failures); strict beta schema
(not chosen: extra endpoint & capability); normal Chat Completion native functions (chosen).
Reuse immutable ToolSandbox source/native bridge. Three cases caps 2+5+5 = 12;
no separate smoke. First read-only echo tests actual receipt chaining, then original complex
phone and reminder task material. No injected state changes. JSON schemas are generated from
actual signatures and frozen. Normal nonstrict function mode, tool_choice auto; do not send
parallel_tool_calls because not listed in reviewed API. Validate full batch of <=4 before
dispatch, preserve IDs, feed actual result as role=tool. Never execute assistant prose.
Read-only tools and simulator writes; no private files/account/network tools. All prior data
remain unchanged. Halt on transport/envelope/identity/schema error or failed qualification,
do not carry unused per-case requests forward. Exports include failed and partial artifacts.
New request label deepseek-flash is an explicit interface qualification change per currently
retrieved docs, not proof of same weights as prior alias. Retain reasoning_content per docs.
Outputs: tested kit, capped user prompt, software evidence, honest readiness status.
