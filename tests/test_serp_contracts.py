"""Shared contracts must preserve saved SERP evidence across package migration."""

import pytest

from lexbench_websearch.answer_rules import reference_rule
from lexbench_websearch.inputs import registry, resolve_profile
from lexbench_websearch.relevance import candidate_packet


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
