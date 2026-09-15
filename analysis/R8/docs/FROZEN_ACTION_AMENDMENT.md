# R8A2: frozen proposed-action exposure audit
Added after the 120 scripted contract cases, before executing this audit.
Read all 42 primary R7C1 episodes (do not select only failures or successes).
Replay their saved native calls only until the first send/modify action. Keep the
already generated action fixed. Compare unchanged state with one admin binding
replacement immediately before that action. No model continuation is generated.
All first-write actions and all control results are retained. This is 84 transition
checks, NOT 84 new agent episodes or 27 observed live-model failures. It cannot tell
how a model would recover after seeing changed feedback. The primary 14/14 scores
for each arm are unchanged. Altering the action's prestate is an explicit intervention.
