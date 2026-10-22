import json

import pytest

from lexbench_websearch import inputs
from lexbench_websearch.relevance import query_metrics, summary
from lexbench_websearch.contracts import validate_cases


def test_every_dataset_has_unique_tasks_and_exact_attribution_coverage():
    attribution = json.loads(inputs.definition_path("sources.json").read_bytes())
    sources = attribution["sources"]
    attributed = [cid for source in sources for cid in source["case_ids"]]
    tasks = []
    for identity, binding in inputs.registry()["datasets"].items():
        data = inputs.load_dataset(identity)
        assert len(data["cases"]) == binding["count"]
        assert all(
            c.get("origin")
            and attribution["task_derivations"][c["id"]]
            and c.get("provenance_kind")
            for c in data["cases"]
        )
        tasks.extend(c["id"] for c in data["cases"])
    assert len(tasks) == len(set(tasks)) == len(attributed) == len(set(attributed))
    assert set(tasks) == set(attributed)


def test_missing_or_changed_dataset_bytes_fail_before_use(tmp_path, monkeypatch):
    definitions = inputs.DEFINITIONS
    (tmp_path / "registry.json").write_bytes(
        (definitions / "registry.json").read_bytes()
    )
    (tmp_path / "datasets").mkdir()
    for name in (definitions / "datasets").glob("*.json"):
        (tmp_path / "datasets" / name.name).write_bytes(name.read_bytes() + b" ")
    monkeypatch.setattr(inputs, "DEFINITIONS", tmp_path)
    with pytest.raises(ValueError, match="hash mismatch"):
        inputs.load_dataset("scenarios-v1")


def test_profile_projection_requires_exact_dataset_and_field_binding():
    binding = inputs.registry()["datasets"]["scenarios-v1"]
    reference = {
        "benchmark_dataset": "scenarios-v1",
        "sha256": binding["sha256"],
        "field": "cases",
    }
    standalone = {"cases": [{"id": "local"}]}
    assert inputs.resolve_profile(standalone) == standalone
    assert (
        len(inputs.resolve_profile({"cases": reference})["cases"]) == binding["count"]
    )
    for change in ({"sha256": "bad"}, {"field": "reference_checks"}):
        with pytest.raises(ValueError, match="binding mismatch"):
            inputs.resolve_profile({"cases": dict(reference, **change)})
    for path in ("../private", "/private"):
        with pytest.raises(ValueError):
            inputs.definition_path(path)


def test_dataset_validation_rejects_duplicate_ids_and_missing_reference_checks():
    with pytest.raises(ValueError):
        validate_cases([{"id": "q"}, {"id": "q"}])
    case = {"id": "q", "anchors": ["https://example.org/"]}
    with pytest.raises(ValueError, match="publisher assertions"):
        validate_cases([case], reference_scope="identity")
    validate_cases(
        [case],
        reference_scope="identity",
        reference_checks={
            "https://example.org/": {
                "url": "https://example.org/",
                "contains": ["Example"],
            }
        },
    )


def test_graded_metrics_cover_missing_duplicate_and_zero_gain_results():
    metrics = query_metrics(
        ["bad", "direct", "support", "direct"], {"bad": 0, "direct": 3, "support": 2}, 5
    )
    assert metrics["ndcg"] == pytest.approx(0.665315246)
    assert metrics["precision"] == 0.4
    assert metrics["success"] == 1
    assert query_metrics([], {}, 5)["ndcg"] == 0
    assert query_metrics(["zero"], {"zero": 0}, 5)["ndcg"] == 0
    for invalid in (-1, 4, True, 2.5):
        with pytest.raises(ValueError, match="grades"):
            query_metrics(["a"], {"a": invalid})
    with pytest.raises(ValueError, match="Cutoff"):
        query_metrics([], {}, 0)
    rows = [
        {"method": "a", "ndcg": value, "precision": value, "success": value}
        for value in (0.0, 1.0)
    ]
    assert summary(rows, ["a"])["a"] == {
        "n": 2,
        "ndcg": 0.5,
        "precision": 0.5,
        "success": 0.5,
    }


def test_public_cli_exports_installed_definitions_and_scores(tmp_path):
    import subprocess
    import sys

    call = lambda *args: subprocess.run(
        [sys.executable, "-m", "lexbench_websearch.cli", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    result = call("export", "scenarios-v1")
    assert result.returncode == 0 and len(json.loads(result.stdout)["cases"]) == 149
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({"ranking": ["a"], "grades": {"a": 3}}))
    result = call("score", str(packet))
    assert result.returncode == 0 and json.loads(result.stdout)["precision"] == 0.2
    packet.write_text(json.dumps({"ranking": ["a"], "grades": {"a": 4}}))
    assert call("score", str(packet)).returncode != 0
