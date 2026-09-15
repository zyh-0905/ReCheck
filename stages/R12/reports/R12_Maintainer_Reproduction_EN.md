# Draft only — milestone full score after terminal regression on persistent-goal tasks

This note has NOT been posted as an issue or sent to maintainers. It describes an
executable scoring boundary, not an allegation about published model performance.

Pinned repository: apple-aiml-research/ToolSandbox,
commit c8571d7854316d2e1c5f288e59fe1e34e53f6dd1.

## Minimal observation

For the original `wifi_off` task, run its original ExecutionEnvironment and tools:

1. `set_wifi_status(on=False)` succeeds.
2. `set_wifi_status(on=True)` succeeds.
3. End with the same completion statement used by the correct control.
4. Run the original `Evaluation.evaluate`.

The result is `similarity=1.0`, although terminal `SETTING.wifi` is `true`.
The recorded milestone mapping is `{0: (17, 1.0), 1: (20, 1.0)}`; the undo occurs
at snapshot 19. `src/minimal_repro.py` contains an independent driver using only
original ToolSandbox classes, and `logs/minimal_repro.json` records the execution.

## Controls

A correct completion passes. A no-state-change tool exception followed by correct
completion also passes. A completion statement without action obtains a partial,
not full, milestone score. Completing, undoing, and repairing again passes and
has the right terminal state. These controls preserve flexibility in valid paths.

Five canonical setting tasks were evaluated first, then three contact/reminder
tasks as an explicitly exploratory supplement. All eight selected
achieve-then-revert scripts retained full milestone similarity but violated the
separate terminal goal check. No LLM/user simulator was run; these are controlled
native traces, not estimates of natural model error frequency.

## Interpretation question

The documented metric optimizes historical milestone matching. We do not assume
it is intended as a certificate of every terminal-state invariant. For requests
such as switching Wi-Fi off or setting a contact's phone number, should the task
include an explicit terminal predicate in addition to its milestone score? A
uniform persistence constraint on every milestone would be inappropriate for
transient intermediate goals.

We would value clarification of the intended semantics before changing a score
or estimating effects on stored model trajectories. No existing published result
has been recalculated by this audit.
