# Pilot results

Study: recheck
Evidence label: REAL_ENDPOINT_CONTROLLED_PILOT_NOT_CONFIRMATORY

**Development pilot only. Do not use these results as final paper evidence.**

Completed records: 128/128; HTTP attempts: 260.

```json
{
  "study": "recheck",
  "evidence_label": "REAL_ENDPOINT_CONTROLLED_PILOT_NOT_CONFIRMATORY",
  "phase": "development_pilot",
  "expected_records": 128,
  "completed_records": 128,
  "request_attempts": 260,
  "completed_logical_calls": 260,
  "request_errors": 0,
  "uncertain_interrupted_attempts": 0,
  "unknown_cost_attempts": 0,
  "known_estimated_spend": 0.2502598559999999,
  "currency": "USD",
  "returned_model_ids": [
    "deepseek-flash"
  ],
  "source_snapshot_mismatches": [],
  "methods": [
    {
      "method": "always",
      "completed_records": 32,
      "independent_units": 4,
      "success_rate": 0.96875,
      "llm_calls_excluding_shared_prefix": 64,
      "llm_attempts_excluding_shared_prefix": 64,
      "llm_latency_seconds_excluding_shared_prefix": 238.1146304171998,
      "estimated_cost_excluding_shared_prefix": 0.06157477199999999
    },
    {
      "method": "myopic",
      "completed_records": 32,
      "independent_units": 4,
      "success_rate": 1.0,
      "llm_calls_excluding_shared_prefix": 64,
      "llm_attempts_excluding_shared_prefix": 64,
      "llm_latency_seconds_excluding_shared_prefix": 270.3595762848854,
      "estimated_cost_excluding_shared_prefix": 0.07166547599999999
    },
    {
      "method": "recheck",
      "completed_records": 32,
      "independent_units": 4,
      "success_rate": 1.0,
      "llm_calls_excluding_shared_prefix": 64,
      "llm_attempts_excluding_shared_prefix": 64,
      "llm_latency_seconds_excluding_shared_prefix": 238.81919787591323,
      "estimated_cost_excluding_shared_prefix": 0.058521972000000005
    },
    {
      "method": "ttl",
      "completed_records": 32,
      "independent_units": 4,
      "success_rate": 0.96875,
      "llm_calls_excluding_shared_prefix": 64,
      "llm_attempts_excluding_shared_prefix": 64,
      "llm_latency_seconds_excluding_shared_prefix": 229.3116458291188,
      "estimated_cost_excluding_shared_prefix": 0.056678435999999985
    }
  ],
  "shared_prefix_resources": {
    "llm_calls": 4,
    "llm_attempts": 4,
    "llm_latency_seconds": 8.60579941677861,
    "estimated_cost": 0.0018192,
    "prompt_tokens": 836,
    "completion_tokens": 1307,
    "missing_usage_calls": 0
  },
  "limitations": [
    "Pilot only; no confirmatory p values or manuscript updates.",
    "Token totals exclude missing usage; missing_usage_calls must be inspected.",
    "Provider invoice overrides all local list-price estimates.",
    "Shared prefix paid once in this run; include its cost in each strategy for deployment comparisons, but do not sum those attributed costs into the actual invoice.",
    "Synthetic task generation; no natural-failure or public-benchmark claim."
  ],
  "initial_calibration_probes_actual": 8
}
```
