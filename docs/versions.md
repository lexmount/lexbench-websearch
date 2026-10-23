# Benchmark editions

The first benchmark edition is **1.0.0**, released as **`bench-1.0.0`** after
its PR merges. Tags use `bench-MAJOR.MINOR.PATCH` and are never moved or replaced.
The Python package version (`0.1.0`) is separate: installing a new package does
not change the benchmark selected by an existing run.

An edition fixes the available datasets, their complete task contracts, frozen
reference qualifications, relevance rubrics and scoring source. Dataset IDs
such as `scenarios-v1` and `scenarios-v2` remain distinct snapshots within the
catalog; the release does not combine them or change historical results.

| Change | Version bump | Result comparison |
| --- | --- | --- |
| Documentation or attribution; measurement unchanged | Patch | Direct, under matching execution controls |
| Reference or scoring correction with the same tasks and requests | Minor | Rescore both saved cohorts under one edition |
| Added or removed tasks, changed queries, request scope or retrieval route | Major | Keep the resulting benchmark series separate |

Version numbers do not establish comparable latency, provider settings or
billing. Those controls belong to the execution harness. A minor correction
preserves the task's purpose; adding a different quality dimension calls for a
major edition even if the automatic fingerprints alone would permit a minor.

## Inspect the installed release

```sh
uv run --frozen lexbench-websearch version
```

This verifies `definitions/benchmark-release.json` against every installed
dataset and the scoring source. The catalog records each dataset separately,
including historical snapshots. It contains no provider results, report text,
credentials or publication targets.

Keep a full Git commit in the harness dependency lock. The tag names a release;
its SHA-256 bindings identify the actual measurement contracts. The catalog's
full `scorer_revision` locates the scoring code, while `scoring_source_sha256`
checks its packaged modules and scoring data independently.

## Freeze a selected dataset

Export the desired dataset and freeze its release sidecar before provider calls:

```sh
uv run --frozen lexbench-websearch export scenarios-v2 > /absolute/inputs/dataset.json
uv run --frozen lexbench-websearch release \
  --dataset /absolute/inputs/dataset.json \
  --output /absolute/inputs/benchmark-release.json \
  --version 1.0.0 --scorer-revision <full-40-character-scorer-commit>
```

Keep run-specific sidecars beside the external inputs. The command refuses to
overwrite an existing sidecar. A successor uses `--previous` and a higher version;
reference or scoring corrections also require `--change-note`.

```sh
uv run --frozen lexbench-websearch compare-releases \
  /absolute/old/benchmark-release.json /absolute/new/benchmark-release.json
```

The result is `direct`, `rescore` or `separate`. Changed tasks or requests within
a major edition, or changed scoring within a minor edition, are rejected.
Historical calls and scores retain their original bindings. A presentation
rebuild does not upgrade them to a newer benchmark edition.

## Publish a tag

After the release PR merges, verify the catalog from the merged commit and
create an annotated `bench-1.0.0` tag at that commit. Push only that tag. Never
publish a release tag from an unmerged PR branch or retarget an existing tag.
