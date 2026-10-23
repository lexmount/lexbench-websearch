# Data and sources

## Scenario queries

`definitions/datasets/scenarios-v1.json` contains 149 frozen cases. `definitions/sources.json` maps every case ID to its original source, provenance category and attribution status. Case fields `origin` and `provenance_kind`, and the source inventory's `task_derivations`, distinguish original text from adaptations. Original `derivation` fields are retained where supplied. Counts are:

| Provenance | Count | Attribution |
| --- | ---: | --- |
| Public catalog | 80 | [Microck/websearch-bench queries](https://github.com/Microck/websearch-bench/blob/7714e86b1b8d7b943037c38b04d4f6ba65566d5b/data/queries.jsonl), MIT; pinned commit `7714e86b1b8d7b943037c38b04d4f6ba65566d5b` |
| Exact community query | 7 | Individual post/article URL retained per case |
| User screenshot transcription | 28 | Original author and post not established; do not attribute these to a verified X post |
| Community-derived query | 14 | Inspired by cited examples; wording/constraints may differ |
| Curated query | 20 | Authored controls and selected service/documentation queries; source retained |

One community source is [Arcadia_Bao's comparison](https://x.com/Arcadia_Bao/status/2111711040757006401). Its claims and scores are not benchmark labels. The inventory also cites other posts, papers and pages individually. Screenshots, third-party page bodies and upstream provider judgments are not redistributed.

Known-page references are deliberately incomplete. They can test whether a selected page was found, but are not exhaustive relevance judgments of the web. `scenarios-v1` preserves the original task definitions. `scenarios-v2` adds thirty qualified reference pages and four supported URL equivalences, including their source observations and publisher assertions. Each version is independently hash-bound; new runs should use `registry.current.scenarios`. Paired regression controls live alongside the definitions.

## Factual retrieval probes

Source: [SimpleQA Verified dataset card](https://huggingface.co/datasets/google/simpleqa-verified/blob/ed392714d14fa5225b07c2b456453983bc75f690/README.md), revision `ed392714d14fa5225b07c2b456453983bc75f690`.

The publisher CSV SHA-256 is `fb990cca0fae8515ae2f51b794d5fa791d095c1f919ecdbe22d0c1642e9ab966`. The original 1,000 questions were filtered before collection by the shared API limit of 128 Unicode characters, retaining 831 in publisher order. Questions, answers and source URLs remain unchanged apart from removing unmatched closing parentheses from URL parsing. `lexbench_websearch.simpleqa.rebuild_dataset` verifies the original CSV hash before rebuilding the selection.

SimpleQA Verified is by Lukas Haas, Gal Yona, Giovanni D'Antonio, Sasha Goldshtein and Dipanjan Das: [paper](https://arxiv.org/abs/2509.07968). It builds on OpenAI's [SimpleQA](https://arxiv.org/abs/2411.04368). Its dataset card declares MIT. This repository measures retrieval diagnostics on that material, not the original answer-generation benchmark.

## Versioning

`registry.json` binds dataset IDs to counts and exact file hashes. Loaders reject changed bytes. `provenance.json` lists the packaged dataset identities and source inventory. Per-case attributions link to original public sources. Execution profiles and report approvals are external inputs owned by the consuming harness.

No provider results, model grades, captures, secrets or private run directories are included. New references require independently observed source evidence and positive/negative scoring controls. Altering a definition requires a new hash and an explicit version decision.

## Rebuilding the factual selection

Download the exact CSV named by `definitions/factual-source.json`, then run `lexbench-websearch rebuild factual-v1 --csv /path/to/publisher.csv`. The command verifies both the publisher hash and the rebuilt dataset hash. The source manifest owns the query-length selection and expected counts.

## Topic composition

Thirteen scenario queries mention DeepSeek, including product documentation and community examples. These are provenance-driven coverage cases, not a balanced sample of all search topics. Consumers should publish the selected composition and may break down results by topic; changing the queries requires a new dataset version.

The screenshot transcriptions have no established public source. Their original attribution remains unknown; image hashes inherited in the historical definitions are not independently verifiable public citations. No author or usage license is inferred from those hashes.
