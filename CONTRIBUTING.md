# Contributing

Use a feature branch and pull request. Run `make check` before submitting. Include the behavior being changed, its source evidence and the checks performed.

Tasks, attribution and provider-independent scoring belong here. Provider adapters, calls, credentials, measured results and report changes belong in Browser Eval. Keep runtime dependencies empty unless a benchmark requirement justifies one.

For new tasks, provide the query, provenance category, original source, derivation and acceptance scope. Preserve original-language dataset text; use English for code and guides. Unknown provenance must be stated explicitly. Do not import another evaluator's judgments as independent labels.

Scoring changes need positive and negative behavior tests. Reference changes need independently observed supporting evidence and paired controls. Update the registry hash whenever a dataset file changes, and explain whether its version must change. Do not rewrite measured evidence.

Never commit secrets, provider outputs, private captures, temporary jobs or generated reports.

Benchmark releases follow [the versioning policy](docs/versions.md). Update the
catalog bindings only for a human-requested release; do not overwrite
published tags or historical dataset snapshots.

Version bumps and release tags are manual, triggered by an explicit human release request. Ordinary fixes and synchronization leave the release catalog unchanged. Inspect development scoring with the `version` command; `unreleased` source changes do not certify a new edition.
