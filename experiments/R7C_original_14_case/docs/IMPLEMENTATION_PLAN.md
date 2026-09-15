# R7C implementation and test plan
Goal: a finite real-model problem diagnosis on pinned native ToolSandbox state.
Scope approved by the ongoing user task: complete local work here, hand off only paid calls.
No R1-R6 reruns; no claims of method superiority.

## Design frozen before native study outcomes
14 matched case initializations: three language goals x four variants, plus two explicit-error cases.
Three arms: stateless, inherited, inherited + general pre-write resolve instruction.
The two inherited arms receive identical non-instruction information.
Stateless omits pre-task memory and observations by definition; it is not a token-matched control.
42 primary episodes; repeat c02 and c10 once in each arm = 6 diagnostic episodes.
One JSON action per call, 8-turn cap including termination, 384+1 total call bound.
Repeats have the exact same initial snapshot but independent endpoint calls; never best-of-two.
Stable and irrelevant-change cases retained. Only first execution of an episode is primary.
No drift during an episode: this does not validate TOCTOU safety.
Native tools and data live solely in isolated simulated storage; no personal connectors.

## Files / work items
1. tests/test_native.py RED -> native.py, cases.py, goals.py GREEN.
   Check intent distinction, reused identifiers, observed evidence, no wrong writes, whitelist.
2. tests/test_protocol.py RED -> prompts.py, experiment.py GREEN.
   Check arm information boundaries, cap, repeat order, no oracle labels in prompt.
3. tests/test_transport.py RED -> transport.py, artifacts.py, r7c.py GREEN.
   Check immutable starts/responses, pause on errors, no retry, secret exclusion,
   source/config binding, completed no-op, safe export and early-pause audit.
4. Run native scripted fixed cases, official local-tool subset tests, record failures.
5. Run end-to-end LOCAL HTTP fixture (SOFTWARE_TEST_NOT_RESEARCH); audit exported archive.
6. Fresh extract test and source verification; package only clean code/config + offline evidence.
Native scripts are interface/solvability controls, not a new algorithm or LLM benchmark score.
