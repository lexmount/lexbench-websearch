"""Shared contracts must preserve saved SERP evidence across package migration."""

import copy
import json
from urllib.parse import urljoin

import pytest

from lexbench_websearch.answer_rules import reference_rule
from lexbench_websearch.inputs import definition_path, digest, registry, resolve_profile
from lexbench_websearch.relevance import candidate_packet
from lexbench_websearch.revisions import apply_report_revision
from lexbench_websearch.scoring import evaluate, normalize_results


def test_composed_datasets_preserve_order_and_reject_duplicate_or_changed_inputs():
    bindings = [
        {"id": key, "sha256": registry()["datasets"][key]["sha256"]}
        for key in ("scenarios-v1", "factual-v1")
    ]
    profile = {"cases": {"field": "cases", "benchmark_datasets": bindings}}
    resolved = resolve_profile(profile)
    assert len(resolved["cases"]) == 980
    assert len({c["id"] for c in resolved["cases"]}) == 980
    for altered in (bindings + bindings[:1], [{**bindings[0], "sha256": "0" * 64}]):
        with pytest.raises(ValueError):
            resolve_profile(
                {"cases": {"field": "cases", "benchmark_datasets": altered}}
            )


@pytest.mark.parametrize(
    "reference,answer",
    [
        ("42[7]", "42"),
        ("Adahttps://source.test/page", "Ada"),
        ("https://source.test/page", "https://source.test/page"),
    ],
)
def test_citation_cleanup_preserves_original_answers_and_url_answers(reference, answer):
    rule = reference_rule(reference)
    assert rule["reference"] == reference
    assert rule["alternatives"] == [answer]


def test_reference_quarantine_applies_to_all_methods_without_changing_calls():
    case = {
        "id": "fact",
        "family": "factual",
        "query": "How many?",
        "reference_answer": "42",
        "reference_urls": [],
    }
    profile = {"cases": [case]}
    rows = [
        {
            "id": method,
            "case_id": "fact",
            "results": [],
            "elapsed_ms": 17,
            "cost": 1,
            "metrics": evaluate(case, []),
        }
        for method in ("a", "b")
    ]
    original = copy.deepcopy((profile, rows))
    decision = {
        "case_id": "fact",
        "query": "How many?",
        "reference_answer": "42",
        "quality_excluded": True,
        "reason": "Independent source contradicts the reference",
        "evidence": [{"url": "https://reference.test/", "excerpt": "43"}],
    }
    revision = {
        "schema": "web-search-assessment-revision/1",
        "provider_calls": 0,
        "root_cause": "Incorrect factual reference",
        "regression_ids": ["unqualified-reference-rejected"],
        "reference_adjudications": [decision],
    }
    revised, updated, _ = apply_report_revision(profile, rows, revision)
    assert revised["factual_quality_exclusions"] == ["fact"]
    assert updated == rows
    assert (profile, rows) == original
    for key, value in (
        ("query", "Another query"),
        ("reference_answer", "43"),
        ("evidence", []),
    ):
        changed = copy.deepcopy(revision)
        changed["reference_adjudications"][0][key] = value
        with pytest.raises(ValueError):
            apply_report_revision(profile, rows, changed)


def test_serp_packet_preserves_optional_native_text_and_explicit_source_scope():
    case = {
        "id": "official",
        "family": "web",
        "query": "Official documentation",
        "domains": ["diagnostic.test"],
    }
    profile = {"cases": [case], "methods": [{"id": "a"}], "protocol": {"top_k": 5}}
    rows = [
        {
            "case_id": "official",
            "method": "a",
            "results": [
                {"url": "https://official.test/manual", "title": None, "snippet": None}
            ],
        }
    ]
    packet, _ = candidate_packet(
        profile,
        rows,
        {"official": {"domains": ["official.test"]}},
        packet_format="serp/1",
    )
    candidate = packet["blind_candidate_packets"][0]["candidates"][0]
    assert candidate["source_eligible"]
    assert candidate["previews"] == [{"title": "", "snippet": ""}]
    assert packet["blind_candidate_packets"][0]["required_domains"] == []


def test_native_revision_requires_adapter_and_rejects_incorrect_projection():
    revision = {
        "schema": "web-search-assessment-revision/1",
        "provider_calls": 0,
        "root_cause": "Native URL projection correction",
        "normalization": "request-url/1",
        "regression_ids": [
            "relative-serp-links",
            "unsafe-serp-links",
            "top-five-boundary",
        ],
        "regressions_sha256": digest(
            definition_path("native-normalization-regressions.json").read_bytes()
        ),
    }
    with pytest.raises(ValueError, match="execution adapter"):
        apply_report_revision({"protocol": {}, "cases": []}, [], revision)
    with pytest.raises(ValueError, match="Normalization regression failed"):
        apply_report_revision(
            {"protocol": {}, "cases": []}, [], revision, normalizer=lambda *_: []
        )


def test_native_correction_preserves_calls_and_checks_artifacts(tmp_path, monkeypatch):
    from lexbench_websearch import revisions

    case = {"id": "q", "family": "web", "anchors": ["https://source.test/answer"]}
    protocol = {"result_url_resolution": "request-url/1"}
    request = {"url": "https://source.test/search"}
    method = {"id": "a"}
    payload = {"results": [{"url": "/answer"}]}
    raw = json.dumps(payload).encode()

    def project(value, _method, policy, source):
        assert policy["result_url_resolution"] == "request-url/1"
        return normalize_results(
            {
                "results": [
                    dict(item, url=urljoin(source["url"], item["url"]))
                    for item in value["results"]
                ]
            }
        )

    control = {
        "id": "relative-link",
        "payload": payload,
        "method": method,
        "protocol": protocol,
        "request": request,
        "case": case,
        "error": False,
        "expected_urls": ["https://source.test/answer"],
        "expected_metrics": {"anchor_hit_5": 1},
    }
    controls = tmp_path / "controls.json"
    controls.write_text(json.dumps({"regressions": [{"controls": [control]}]}))
    original_path = revisions.definition_path
    monkeypatch.setattr(
        revisions,
        "definition_path",
        lambda name: (
            controls
            if name == "native-normalization-regressions.json"
            else original_path(name)
        ),
    )
    revision = {
        "schema": "web-search-assessment-revision/1",
        "provider_calls": 0,
        "root_cause": "Request-relative URL",
        "normalization": "request-url/1",
        "regression_ids": [
            "relative-serp-links",
            "unsafe-serp-links",
            "top-five-boundary",
        ],
        "regressions_sha256": digest(controls.read_bytes()),
    }
    row = {
        "id": "q-a",
        "case_id": "q",
        "method": "a",
        "http_status": 200,
        "error": "Result URL must be absolute",
        "results": [],
        "request": request,
        "elapsed_ms": 123,
        "cost": 7,
        "evidence": {"path": "call.json", "sha256": digest(raw)},
        "metrics": evaluate(case, []),
    }
    profile = {"cases": [case], "methods": [method], "protocol": {}}
    original = copy.deepcopy((profile, row))
    _, updated, changes = apply_report_revision(
        profile, [row], revision, artifacts={"call.json": raw}, normalizer=project
    )
    assert updated[0]["metrics"]["anchor_hit_5"] == 1
    assert updated[0]["error"] == ""
    assert updated[0]["elapsed_ms"] == 123 and updated[0]["cost"] == 7
    assert updated[0]["evidence"] == row["evidence"]
    assert changes[0]["normalization"]["before_count"] == 0
    assert (profile, row) == original
    for artifacts in (None, {}, {"call.json": b"changed"}):
        with pytest.raises(ValueError, match="artifact"):
            apply_report_revision(
                profile, [row], revision, artifacts=artifacts, normalizer=project
            )
    invalid = b'{"results": [{"url": "javascript:invalid"}]}'
    bad_row = copy.deepcopy(row)
    bad_row["evidence"]["sha256"] = digest(invalid)
    _, preserved, _ = apply_report_revision(
        profile,
        [bad_row],
        revision,
        artifacts={"call.json": invalid},
        normalizer=project,
    )
    assert preserved == [bad_row]


def test_sequential_reference_quarantines_preserve_prior_decisions():
    cases = [
        {"id": cid, "query": cid, "reference_answer": "42"} for cid in ("a", "b", "c")
    ]
    profile = {"cases": cases}
    revision = {
        "schema": "web-search-assessment-revision/1",
        "provider_calls": 0,
        "root_cause": "Incorrect references",
        "regression_ids": ["unqualified-reference-rejected"],
    }
    decisions = [
        {
            "case_id": c["id"],
            "query": c["query"],
            "reference_answer": "42",
            "quality_excluded": True,
            "reason": "Contradicted by source",
            "evidence": [{"url": "https://reference.test/", "excerpt": "43"}],
        }
        for c in cases[:2]
    ]
    first, _, _ = apply_report_revision(
        profile, [], {**revision, "reference_adjudications": decisions[:1]}
    )
    second, _, _ = apply_report_revision(
        first, [], {**revision, "reference_adjudications": decisions[1:]}
    )
    assert second["factual_quality_exclusions"] == ["a", "b"]
    assert second["reference_adjudications"] == decisions
    assert [
        c["id"]
        for c in second["cases"]
        if c["id"] not in second["factual_quality_exclusions"]
    ] == ["c"]
    replay, _, _ = apply_report_revision(
        second, [], {**revision, "reference_adjudications": decisions}
    )
    assert replay == second
    assert "factual_quality_exclusions" not in profile
    for invalid in (
        [decisions[0], decisions[0]],
        [{**decisions[0], "reason": "Changed decision"}],
    ):
        with pytest.raises(ValueError, match="Duplicate or conflicting"):
            apply_report_revision(
                second, [], {**revision, "reference_adjudications": invalid}
            )
