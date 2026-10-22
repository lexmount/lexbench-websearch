# Harness integration

[Browser Eval](https://github.com/lexmount/browser-eval) installs an immutable Git revision of this package, as it does for LexBench Web Fetch.

| Owner | Responsibilities |
| --- | --- |
| LexBench Web Search | Task definitions, source attribution, reference qualifications, URL/answer rules, pooling and deterministic metrics |
| Browser Eval | Provider-specific requests/adapters, credentials, calls and retries, timings/billing, annotation collection, result audit, report rendering and publication |

Load a task population using `lexbench_websearch.inputs.load_dataset`. It returns a fresh decoded dictionary whose `cases` can be used directly by a harness. `resolve_profile` expands explicit hash-bound dataset field references in execution profiles. It leaves standalone historical profiles unchanged. The harness owns the execution profile and stores the resolved input with each run.

Normalize provider responses to an object with a `results` array. Each result requires an HTTP(S) `url` and may include string `title`, `snippet`, `summary`, `content` and a `date`. Provider envelope parsing belongs in the adapter; `normalize_results` validates the common form. Keep the raw response separately.

Use `candidate_packet(profile, rows)` to produce a blind pool. The minimal profile supplies `cases`, `methods` with IDs, and `protocol.top_k`; each row supplies `case_id`, `method` and normalized `results`. Use `score(profile, rows, plan, labels)` with an exact query/candidate label inventory. See [evaluation](evaluation.md) for meanings and formulas.

The command `lexbench-websearch score INPUT.json` accepts `ranking` (candidate IDs), `grades` (candidate ID to integer 0..3), and optional `cutoff`. It returns deterministic per-query metrics. Collection and report commands remain in Browser Eval.

Frozen measured outputs are external evidence, not package assets. The package's `implementation_sources` function lets a harness bind scorer source bytes along with its own runner sources. Historical receipts retain their original code and input hashes.
