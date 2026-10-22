# Evaluation protocol

## Unit and candidate pool

A task is one query with its stated site, time and content constraints. Choose the result budget before collection (normally five) and use it for all systems. Pool the systems' returned URLs per query, canonicalize only documented tracking variants, and deduplicate them. Hide system names and original ranks from annotators. `candidate_packet` produces the blind inputs; it does not generate grades.

## Four relevance grades

| Grade | Meaning | Decision rule |
| ---: | --- | --- |
| 0 | Irrelevant | Wrong subject, or violates a required site/time/content condition |
| 1 | Related | About the topic but does not provide useful evidence for the request |
| 2 | Useful | Provides part of the requested evidence or helpful support |
| 3 | Direct | Directly meets the core request |

This adopts the four-grade structure used by [TREC Deep Learning](https://microsoft.github.io/msmarco/TREC-Deep-Learning.html). These are project task-specific definitions; the scenario set is not a TREC dataset. Annotators must record reasons and supporting text. A preview-only assessment describes the returned title/snippet; it does not establish the truth of the entire page. Human or model annotation may be orchestrated externally, but its identity and evidence must be disclosed separately. No labels are supplied as independent human gold in this release.

## Result, query and dataset scores

Each unique query–URL candidate receives one grade. A system's ranked results reuse those grades. Repeated URLs receive no additional gain. Missing positions count as zero.

For each query at cutoff k:

- **nDCG@k:** DCG is the sum of `(2**grade - 1) / log2(rank + 1)` using one-based ranks. Divide by the ideal DCG from the same pooled candidates sorted by grade. If the pool has no positive gain, this project's score is zero and the query remains in the population.
- **Precision@k:** number of distinct returned results graded at least 2, divided by k.
- **Direct-result success@k:** 1 if at least one result is graded 3, otherwise 0.

Dataset scores are the arithmetic mean of each metric over every declared query, including empty responses and all-zero pools. Report the query count and all-zero count with the metric. Do not combine different datasets into one quality score.

For grades `[0, 3, 2]`, DCG is `7/log2(3) + 3/log2(4)`. The ideal order `[3, 2, 0]` gives `7 + 3/log2(3)`. nDCG is about 0.6653. Precision@5 is 2/5 and direct-result success@5 is 1. `query_metrics` exposes each contribution for inspection.

## Other diagnostics

`evaluate` reports known-page hits, reciprocal rank, specified-domain precision and duplicate rate. Unjudged pages are not treated as relevance grade zero when computing reference-based nDCG; incomplete judgment coverage makes that metric unavailable. The pooled graded calculation above instead requires exact label coverage.

Factual probes separately measure exact normalized source-URL matches and lexical answer evidence. Answer rules support documented date/number/name normalization and flag benchmark mirrors. They do not prove semantic correctness or entailment. They do not call a model.

Execution latency and cost are collected by the harness. Declare whether latency includes retries and whether cost counts all billable physical calls. One final logical result per system/query is the scoring sample; a failed-call retry must never select the better response.
