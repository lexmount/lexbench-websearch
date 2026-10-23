<div align="center">

<img src="docs/assets/overview.png" alt="LexBench Web Search — Measure what search finds." width="100%">

[Datasets](#datasets) · [Quick start](#quick-start) · [Scoring](#scoring) · [Contributing](CONTRIBUTING.md)

</div>

Versioned search queries, source references and retrieval scoring for Search APIs.

LexBench Web Search owns the benchmark inputs and scoring rules. [Browser Eval](https://github.com/lexmount/browser-eval) runs providers, records latency and billing, and builds comparison reports. This package works offline and has no runtime dependencies, provider adapters, API keys or measured outputs.

## Datasets

| Dataset | Tasks | Content |
| --- | ---: | --- |
| `scenarios-v1` | 149 | General web, named-site and vertical-search queries assembled from public catalogs, community examples and authored controls |
| `scenarios-v2` | 149 | The same queries with qualified reference additions and URL equivalences; recommended for new runs |
| `factual-v1` | 831 | Unchanged SimpleQA Verified questions within the preregistered 128-character input limit, with publisher answers and source URLs |

The scenario set includes 80 queries from Microck/websearch-bench, 7 traceable exact community queries, 28 transcribed screenshot queries whose original author/post is unknown, 14 community-derived queries and 20 curated queries. Every task has an origin and a derivation entry in the source inventory. See [data and sources](docs/data.md), [third-party notices](THIRD_PARTY.md) and the installed `definitions/sources.json` inventory.

The factual set is an adaptation for retrieval diagnostics. It does not reproduce the official SimpleQA Verified evaluation, which tests answers without retrieval tools. The two datasets have different purposes and should be reported separately.

## Quick start

```sh
uv sync --frozen
uv run --frozen lexbench-websearch list
uv run --frozen lexbench-websearch validate scenarios-v2
uv run --frozen lexbench-websearch export scenarios-v2 > /tmp/scenarios.json
make check
```

Install a pinned Git revision in another project:

```sh
uv add 'lexbench-websearch @ git+https://github.com/lexmount/lexbench-websearch.git@<commit>'
```

```python
from lexbench_websearch.inputs import load_dataset
from lexbench_websearch.relevance import query_metrics

cases = load_dataset("scenarios-v2")["cases"]
metrics = query_metrics(["useful", "unrelated"], {"useful": 3, "unrelated": 0}, cutoff=5)
assert metrics["ndcg"] == 1.0
assert metrics["precision"] == 0.2
```

## Scoring

Relevance uses four grades: 0 (irrelevant), 1 (related but insufficient), 2 (useful support), and 3 (directly satisfies the request). The [evaluation protocol](docs/evaluation.md) defines per-result grades, per-query nDCG/precision/success, and the arithmetic mean across queries.

The scorer is deterministic for fixed results and labels. No model is called by this package. Relevance labels must be supplied separately; historical model labels are not bundled as human ground truth. Known-source URL hits and lexical answer matches are separate diagnostics.

Latency, retries and billing belong to the execution harness. See [integration](docs/integration.md) for the boundary and normalized result format.

## References and license

Project code and authored material use the [MIT license](LICENSE). Third-party material retains its source terms; see [THIRD_PARTY.md](THIRD_PARTY.md). Dataset questions keep their original language. Code, tooling and guides use English.

Please cite this repository using [CITATION.cff](CITATION.cff), and cite the original datasets when using their material. The [source guide](docs/data.md) provides pinned upstream links and paper references.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Benchmark editions

The first edition is **1.0.0**, with release tag **`bench-1.0.0`** created after
merge. `uv run --frozen lexbench-websearch version` verifies the installed
catalog, datasets and scoring source. Benchmark editions are independent of
Python package versions. See [versioning](docs/versions.md) for change rules,
frozen input sidecars and comparison compatibility.
