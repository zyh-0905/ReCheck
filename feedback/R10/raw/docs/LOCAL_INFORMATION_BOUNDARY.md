# Narrow information boundary: readback can confirm a self-overwrite

Let x be the one business field a user permits changing; y is a protected field. A prior observation is (x0,y0). At write time the environment may have changed y to y1. Resubmitting the cached record while changing x induces

    W_full(x,y) = (x*, y0).

For any y0 != y1, the business-state readback after W_full is identical whether the commit-time y was y0 or y1. But preservation was respected only in the former case. A verifier observing only this post-write business projection cannot distinguish those histories. In contrast, a partial update W_patch(x,y)=(x*,y) preserves the protected field; it does not establish that the selected ID was correct.

This is a direct non-injectivity argument, NOT a new theorem or a claim that all information is erased. A trustworthy version counter, immutable pre-write state/audit log, or a checked compare-and-set can distinguish or prevent the histories. Our row versions are actually retained and offered; we do not remove them to manufacture an impossibility. R10's simple ID readback verifier simply does not use all of those signals. Also, target-only CAS does not protect a changing external route or the eligibility of another row. Existing OCC/transaction and agent-consistency papers already analyze those boundaries.

Keep the claims separate:
1. A script can erase protected business evidence and then pass a narrow readback test.
2. A real model may or may not choose that script when it has a documented patch/conditional interface.
3. Querying the current target after a wrong write can detect failure but does not undo the earlier unauthorized write.
Only (1) is measured by the offline contract table. R9NT1 supplied examples motivating (2), but R10 still requires new model evidence to test transfer.
