#!/usr/bin/env python3
"""Independent post-run reviewer for an LLM_Pilot_Kit run directory.

Implements the RETURN_REVIEW checklist against a completed run:
  1. export/code-snapshot hash consistency
  2. attempt/record/call accounting (including failures and uncertain attempts)
  3. hidden-answer leakage scan over every byte actually sent to the model
  4. shared-prefix identity and absence of cross-method answer reuse
  5. requested vs returned model, reasoning tokens, finish_reason
  6. per-method / per-regime error decomposition (cache-semantics error vs model error)

Read-only. Writes nothing into the run directory.
"""
from __future__ import annotations
import hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "LLM_Pilot_Kit"))
from pilot.report import recheck_correct  # noqa: E402

RUN = Path(sys.argv[1]).resolve()
fail: list[str] = []
warn: list[str] = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fail.append(msg)
    return cond


def note(cond, msg):
    print(("  ok    " if cond else "  WARN  ") + msg)
    if not cond:
        warn.append(msg)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


print(f"=== reviewing {RUN.name} ===")
manifest = load(RUN / "manifest.json")
spec = manifest["spec"]
study = manifest["study"]
print(f"study={study} label={manifest['evidence_label']}")
print(f"config.model={manifest['config']['model']} output_cap={manifest['config']['max_output_tokens']} "
      f"max_tokens_field={manifest['config']['max_tokens_field']} temperature={manifest['config']['temperature']} "
      f"extra_body={manifest['config']['extra_body']}")

# ---------------------------------------------------------------- 1. hashes
print("\n[1] snapshot / export integrity")
bad = [rel for rel, sha in manifest["source_hashes"].items()
       if not (RUN / "code_snapshot" / rel).exists()
       or hashlib.sha256((RUN / "code_snapshot" / rel).read_bytes()).hexdigest() != sha]
ok(not bad, f"code_snapshot matches manifest.source_hashes ({len(manifest['source_hashes'])} files)"
   + (f" mismatches={bad}" if bad else ""))
if (RUN / "status.json").exists():
    st = load(RUN / "status.json")
    print(f"  status={st.get('state')} budget={json.dumps(st.get('budget'), ensure_ascii=False)}")

# ------------------------------------------------------------ 2. accounting
print("\n[2] accounting")
starts = sorted((RUN / "attempts").glob("*_start.json"))
results = sorted((RUN / "attempts").glob("*_result.json"))
calls = sorted((RUN / "calls").glob("*.json"))
start_ids = {load(p)["attempt"] for p in starts}
res_ids = {load(p)["attempt"] for p in results}
print(f"  attempts_started={len(starts)} attempts_finished={len(results)} completed_logical_calls={len(calls)}")
ok(len(starts) == len(results), "no interrupted/uncertain attempts (start without result)")
ok(start_ids == res_ids, "attempt index sets agree")
res = [load(p) for p in results]
print(f"  statuses={dict(Counter(r['status'] for r in res))}")
recs = sorted((RUN / "records").glob("*.json"))
expected = (spec["streams"] * spec["steps"] * len(spec["methods"])) if study == "recheck" else spec["cases"] * len(spec["methods"])
ok(len(recs) == expected, f"records complete {len(recs)}/{expected}")
missing_usage = [r for r in res if r["status"] == "ok" and not r.get("response", {}).get("usage")]
ok(not missing_usage, f"every successful response carries usage (missing={len(missing_usage)})")
if study == "recheck":
    planned = spec["logical_calls"]
    print(f"  planned_logical_calls={planned} actual={len(calls)}")
    ok(len(calls) == planned, "logical call count equals frozen protocol value")
    ok(spec["streams"] == 4 and spec["steps"] == 8, "default pilot size 4 streams x 8 steps")

# --------------------------------------------------------------- 3. leakage
print("\n[3] hidden-answer leakage scan of transmitted payloads")
sent = [(p, load(p)["payload"]) for p in starts]
if study == "recheck":
    cases = load(RUN / "private" / "recheck_cases.json")
    for c in cases:
        c["_blob"] = json.dumps(c, ensure_ascii=False)
    leaks = []
    for p, payload in sent:
        blob = json.dumps(payload, ensure_ascii=False)
        # 'hidden' is deliberately excluded: the kit's own system prompt contains
        # the phrase "Never assume access to hidden evaluation or files".
        for token in ("gold", "evaluator_rules", "hidden_mode", "modes", "initial_modes",
                      "no_drift", "hidden_drift", "correct_answer", "regime", "seed"):
            if re.search(token, blob, re.I):
                leaks.append((p.name, token))
        for c in cases:  # exact hidden-state numbers must not appear
            for m in (c["initial_modes"], *(t["modes"] for t in c["tasks"])):
                if f'"modes": {m}' in blob:
                    leaks.append((p.name, f"modes={m}"))
    ok(not leaks, f"no hidden-state field or value in any of {len(sent)} transmitted payloads"
       + (f" leaks={leaks[:5]}" if leaks else ""))
    # every payload must be a JSON object with only sanctioned keys
    keysets = Counter(tuple(sorted(x[1])) for x in sent)
    print(f"  payload key sets: {dict(keysets)}")
    ok(set(keysets) <= {("max_tokens", "messages", "model", "stream")}, "no unexpected request parameters")
    xb = json.dumps([x[1] for x in sent], ensure_ascii=False).lower()
    ok(not any(k in xb for k in ("enable_thinking", "reasoning_effort", "temperature")),
       "no hidden thinking/temperature override smuggled into requests")
else:  # repairlens_readiness: same scan against generator-private ground truth
    cases = load(RUN / "private" / "readiness_cases.json")
    leaks = []
    for p, payload in sent:
        blob = json.dumps(payload, ensure_ascii=False)
        if re.search("evaluator_rules", blob, re.I):
            leaks.append((p.name, "evaluator_rules"))
        for c in cases:
            # the private evaluator arithmetic must never appear; the specs, the
            # source values and the correction text are intentionally public.
            for rule in c["evaluator_rules"]:
                if f'"multiplier": {rule["multiplier"]}' in blob or \
                   f'"threshold": {rule["threshold"]}' in blob:
                    leaks.append((p.name, f"private rule {rule}"))
    ok(not leaks, f"no generator-private evaluator rule in any of {len(sent)} transmitted payloads"
       + (f" leaks={leaks[:5]}" if leaks else ""))
    print("  note: specifications, old/new source values and the correction text are public by design")

# ------------------------------------------------------------- 4. prefixes
print("\n[4] shared prefix + no cross-method answer reuse")
if study == "recheck":
    by_stream = defaultdict(list)
    for p in recs:
        r = load(p)
        by_stream[r["stream"]].append(r)
    same = all(len({r["prefix_sha256"] for r in rs}) == 1 for rs in by_stream.values())
    ok(same, "all four methods in each stream share one identical prefix hash")
    pref_calls = [load(p) for p in calls if load(p).get("metadata", {}).get("phase") == "shared_prefix"]
    ok(len(pref_calls) == spec["streams"], f"exactly one shared-prefix model call per stream ({len(pref_calls)})")
    # identical inputs across methods must still be distinct logical calls
    logical = [c["logical_id"] for c in (load(p) for p in calls)]
    ok(len(logical) == len(set(logical)), "logical call IDs are unique (no answer shared across methods)")

# ---------------------------------------------------- 5/6. model + errors
print("\n[5] provider identity and decoding")
comp = [load(p) for p in calls]
ret = Counter(str(c.get("response", {}).get("model")) for c in comp)
print(f"  requested={manifest['config']['model']} returned={dict(ret)}")
ok(set(ret) <= {manifest["config"]["model"]}, "returned model matches requested model for every call")
fps = Counter(str(c.get("response", {}).get("system_fingerprint")) for c in comp)
print(f"  system_fingerprints={dict(fps)}")
note(len(fps) == 1, "single serving fingerprint across the run (no silent backend switch)")
fr = Counter(c.get("response", {}).get("choices", [{}])[0].get("finish_reason") for c in comp)
print(f"  finish_reasons={dict(fr)}")
ok(fr.get("length", 0) == 0, f"no truncated responses (length={fr.get('length', 0)})")
rt = [((c.get("response", {}).get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0 for c in comp]
pt = [(c.get("response", {}).get("usage") or {}).get("prompt_tokens", 0) or 0 for c in comp]
ct = [(c.get("response", {}).get("usage") or {}).get("completion_tokens", 0) or 0 for c in comp]
hit = [(c.get("response", {}).get("usage") or {}).get("prompt_cache_hit_tokens", 0) or 0 for c in comp]
print(f"  prompt_tokens={sum(pt)} completion_tokens={sum(ct)} of which reasoning={sum(rt)} cache_hit_input={sum(hit)}")
est = [r.get("estimated_cost") for r in res]
print(f"  estimated_cost total = {sum(x for x in est if x is not None):.6f} {manifest['config']['prices']['currency']}"
      f"  (unknown-attempt cost entries={sum(x is None for x in est)})")

print("\n[6] error decomposition")
if study == "recheck":
    rows = [load(p) for p in recs]
    by_logical = {c["logical_id"]: c for c in comp}
    cases = {c["stream"]: c for c in load(RUN / "private" / "recheck_cases.json")}
    # an empty/absent answer after a normally-finished call is a model failure,
    # not a cap artifact; keep those two causes separate.
    causes = Counter()
    for r in rows:
        for phase, lid in zip(("plan", "answer"), r["logical_calls"]):
            c = by_logical.get(lid, {})
            fr_ = (c.get("response", {}).get("choices", [{}])[0] or {}).get("finish_reason")
            empty = not (c.get("text") or "").strip()
            causes[(phase, fr_, "empty" if empty else "text")] += 1
    for k, v in sorted(causes.items(), key=lambda x: str(x[0])):
        print(f"  {k[0]:6} finish={str(k[1]):8} {k[2]:5} n={v}")
    agg = defaultdict(lambda: Counter(n=0))
    for r in rows:
        c = cases[r["stream"]]
        a = agg[(r["method"], c["regime"])]
        a["n"] += 1
        a["correct"] += int(recheck_correct(r, c))
        a["plan_invalid"] += int(not r["plan_schema_valid"])
        a["answer_json_err"] += int(r["answer_json_error"] is not None)
        a["answer_schema_bad"] += int(not (isinstance(r["answer"], dict) and set(r["answer"]) == {"total", "count"}))
        mem = r["worker_view"]["memory"]
        md = mem["amount_divisor"]
        a["mem_divisor_known"] += int(md in (1, 100))
        a["mem_endpoint_known"] += int(isinstance(mem["endpoint_inclusive"], bool))
    print(f"  {'method':8} {'regime':13} {'n':>3} {'correct':>8} {'plan_bad':>9} {'json_err':>9} "
          f"{'schema_bad':>10} {'mem_div_ok':>10} {'mem_ep_ok':>10}")
    for (m, rg), a in sorted(agg.items()):
        print(f"  {m:8} {rg:13} {a['n']:3d} {a['correct']:8d} {a['plan_invalid']:9d} {a['answer_json_err']:9d} "
              f"{a['answer_schema_bad']:10d} {a['mem_divisor_known']:10d} {a['mem_endpoint_known']:10d}")
    # cache-semantics vs model-execution separation: rows whose plan was valid
    # and whose remembered semantics were fully known
    good = [r for r in rows if r["plan_schema_valid"]
            and r["worker_view"]["memory"]["amount_divisor"] in (1, 100)
            and isinstance(r["worker_view"]["memory"]["endpoint_inclusive"], bool)]
    print(f"\n  rows with valid plan AND fully-known semantics: {len(good)}/{len(rows)}"
          f" -> correctness {sum(recheck_correct(r, cases[r['stream']]) for r in good)}/{len(good)}")

    # correctness by task type: separates "needs amount" from "needs endpoint" tasks
    print(f"\n  {'task_type':>9} {'n':>4} {'correct':>8}  needs")
    needs = {0: "amount", 1: "endpoint", 2: "amount+endpoint", 3: "none"}
    tt = defaultdict(Counter)
    for r in rows:
        tt[r["task_type"]]["n"] += 1
        tt[r["task_type"]]["c"] += int(recheck_correct(r, cases[r["stream"]]))
    for k in sorted(tt):
        print(f"  {k:9d} {tt[k]['n']:4d} {tt[k]['c']:8d}  {needs[k]}")

    # semantic-cache error (a channel still unknown when it was needed) vs
    # model execution error (all needed semantics known, yet the row is wrong)
    print(f"\n  {'method':8} {'needed_semantics_unknown':>25} {'wrong_with_semantics_known':>27}")
    for m in spec["methods"]:
        rs = [r for r in rows if r["method"] == m]
        unknown = wrong_known = 0
        for r in rs:
            mem = r["worker_view"]["memory"]
            q = r["task_type"]
            need_div = q in (0, 2)
            need_ep = q in (1, 2)
            sem_known = (not need_div or mem["amount_divisor"] in (1, 100)) and \
                        (not need_ep or isinstance(mem["endpoint_inclusive"], bool))
            if not sem_known:
                unknown += 1
            elif not recheck_correct(r, cases[r["stream"]]):
                wrong_known += 1
        print(f"  {m:8} {unknown:25d} {wrong_known:27d}")

    # per-phase token/latency profile
    print(f"\n  {'phase':14} {'n':>4} {'prompt_tok':>11} {'compl_tok':>11} {'reason_tok':>11} {'mean_lat_s':>11}")
    prof = defaultdict(lambda: {"n": 0, "p": 0, "c": 0, "r": 0, "t": 0.0})
    for r in rows:
        for phase, lid in zip(("plan", "answer"), r["logical_calls"]):
            c = by_logical.get(lid)
            if not c:
                continue
            u = c.get("response", {}).get("usage") or {}
            d = prof[phase]
            d["n"] += 1
            d["p"] += u.get("prompt_tokens", 0) or 0
            d["c"] += u.get("completion_tokens", 0) or 0
            d["r"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0
            d["t"] += c.get("latency_seconds", 0.0)
    for phase in ("plan", "answer"):
        d = prof[phase]
        if d["n"]:
            print(f"  {phase:14} {d['n']:4d} {d['p']:11d} {d['c']:11d} {d['r']:11d} {d['t'] / d['n']:11.2f}")
elif study == "repairlens_readiness":
    rows = [load(p) for p in recs]
    cases = {c["case"]: c for c in load(RUN / "private" / "readiness_cases.json")}
    print(f"  {'method':20} {'n':>3} {'selection_invalid':>18} {'mean_selected':>14}")
    for m in spec["methods"]:
        rs = [r for r in rows if r["method"] == m]
        print(f"  {m:20} {len(rs):3d} {sum(r['selection_error'] is not None for r in rs):18d} "
              f"{sum(len(r['selected_artifacts']) for r in rs) / max(len(rs), 1):14.2f}")

print("\n=== verdict ===")
print(f"hard failures: {len(fail)}")
for f_ in fail:
    print("  - " + f_)
print(f"warnings: {len(warn)}")
for w in warn:
    print("  - " + w)
sys.exit(1 if fail else 0)
