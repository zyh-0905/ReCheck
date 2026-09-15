# Proposed development-study addendum: live continuation (R9NT1)

Status: audited descriptive evidence, not a new algorithm or a confirmation study. Keep the earlier R7C1/R8 records separate. This text does not update their scores.

## Protocol

We executed 32 primary episodes (16 constructed cells under two instruction settings) and four predesignated repeated episodes through a native structured tool interface. Four templates covered a person's current phone number, an explicit literal number, a reminder identified by its current description, and Wi-Fi preconditions. Each had stable, pre-episode relevant-update, post-read relevant-update and post-read unrelated-update conditions. Updates were injected once at a predefined eligible-read boundary. These are controlled, single-backend interventions, not samples of deployed race frequencies. Both settings had the same tools and a ten-request cap; the verify-confirm setting added a write-preparation and read-back instruction. It was not a novel policy and had no length-matched placebo.

## Results

Both inherited and verify-confirm achieved 14/16 final-goal, final-business-state and trace-safe completions, with two wrong-write episodes each. Tool-success accepted all 32 primary episodes; the other three projections agreed on all 32. Thus this batch demonstrates that tool return success is insufficient, but does **not** demonstrate false acceptance by the specified final-state evaluator. Four repeats reproduced the two failure cells under both settings and are not additional independent tasks.

Inherited required 58 model requests and 52 outer tool calls, versus 66 and 59 for verify-confirm. Primary input/output tokens were 169,400/7,513 and 197,860/7,381 respectively. Including repeats, the batch contained 139 requests, 124 native tool events and 44 environment management operations. Of the responses, 82 contained one tool call, 21 contained two, and 36 ended the episode. All double-call batches contained reads; the first target mutation in every post-read cell occurred in a subsequent model response. No native tool exception occurred. Currency cost was not inferred from tokens or call counts.

## Mechanism observations and boundaries

The failures occurred only in the person and reminder post-read relevant-update cells. In the person case, a message was successfully inserted for the stale number, now assigned to another contact. The verify-confirm agent read back the actual message, including its mismatching recipient-person identifier, but still declared the intended-person task complete. In the reminder case, both settings used the stale identifier and submitted old optional content alongside the requested time. This overwrote the intervening content change and created duplicate matching descriptions. Reading back that same identifier confirmed the newly written values rather than independently resolving the current task target. The intended current reminder remained unchanged.

These observations are behavioral evidence, not an inference from hidden reasoning or a universal claim about confirmation. Four post-hoc native reads exposed the current mismatches without changing business state. Two additional argument ablations omitted optional stale reminder fields; they preserved the visible description conflict but still modified the wrong identifier. Neither analysis is a new live-agent outcome or a successful repair method. The live study does not establish that verify-confirm improves safety, that final-state grading misses the observed errors, or that this mechanism is novel relative to prior work. Broader claims require distinct tasks, same-capability strong controls and a separate novelty review.
