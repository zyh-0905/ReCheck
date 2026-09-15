# Analysis amendment, before interval computation

The ReCheck generator intentionally reused base RNG seeds across six regimes. Consequently, its 384 configured streams are not 384 independent sampling units. The analysis clusters all regimes AND all three prices by the 64 independent base seeds. This is more conservative than treating all stream labels independently. No policy, parameter, raw result or sample is changed. Results are descriptive conditional on the declared generator, not a registered confirmatory study.

Main experiment data was inspected for execution sanity before this correction. This document is a transparent analysis amendment, not a claim of external preregistration.
