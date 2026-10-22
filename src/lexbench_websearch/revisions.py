"""Explicit, evidence-backed identity corrections without repeating provider calls."""

from copy import deepcopy
import json

from .scoring import canonical_url, evaluate, normalize_results as normalize
from .contracts import validate_cases
from .inputs import definition_path, digest
from .answer_rules import POLICY_NAME, match_reference_answer


def validate_regressions(record):
    """Execute paired controls before accepting correction provenance."""
    registry = json.loads(definition_path("scoring-regressions.json").read_text())
    ids = record.get("regression_ids")
    if (
        not record.get("root_cause")
        or not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, str) for i in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError("Correction requires cause and unique regression provenance")
    for identity in ids:
        if identity not in registry:
            raise ValueError("Unknown scoring regression: " + str(identity))
        controls = registry[identity]
        if {c["expected"] for c in controls} != {True, False}:
            raise ValueError(
                "Scoring regression requires paired positive and negative controls"
            )
        for control in controls:
            if control["kind"] == "answer":
                actual = match_reference_answer(control["answer"], control["text"])
            elif control["kind"] == "anchor":
                actual = bool(
                    evaluate(
                        control["case"],
                        normalize({"results": [{"url": control["url"]}]}),
                    )["anchor_hit_5"]
                )
            elif control["kind"] == "benchmark_page":
                from .evidence_quality import is_benchmark_page

                actual = is_benchmark_page(control["result"], case=control["case"])
            elif control["kind"] == "relevance_source":
                from .relevance import source_rule_control

                actual = source_rule_control(control)
            elif control["kind"] == "source":
                from .relevance import candidate_packet

                case = control["case"]
                packet, _ = candidate_packet(
                    {
                        "cases": [case],
                        "methods": [{"id": "control"}],
                        "protocol": {"top_k": 5},
                    },
                    [
                        {
                            "case_id": case["id"],
                            "method": "control",
                            "results": [{"url": control["url"]}],
                        }
                    ],
                    {case["id"]: control.get("requirements", {})},
                )
                actual = packet["blind_candidate_packets"][0]["candidates"][0][
                    "source_eligible"
                ]
            elif control["kind"] == "annotation":
                profile = {"cases": [{"id": "q"}]}
                rows = [
                    {
                        "id": "control",
                        "case_id": "q",
                        "results": [],
                        "elapsed_ms": 123,
                        "cost": 7,
                        "metrics": evaluate(profile["cases"][0], []),
                    }
                ]
                revision = {
                    "schema": "web-search-assessment-revision/1",
                    "provider_calls": 0,
                    "root_cause": "Independent annotation qualification",
                    "regression_ids": ["unqualified-reference-rejected"],
                    "cases": [control["item"]],
                }
                try:
                    revised, updated, _ = apply_report_revision(profile, rows, revision)
                    actual = (
                        revised != profile
                        and updated[0]["results"] == rows[0]["results"]
                        and updated[0]["elapsed_ms"] == 123
                        and updated[0]["cost"] == 7
                        and not profile["cases"][0].get("anchors")
                    )
                except ValueError:
                    actual = False
            elif control["kind"] == "qualification":
                actual = _qualified(control["item"])
            elif control["kind"] == "equivalence":
                actual = _equivalent(control["left"], control["right"])
            else:
                raise ValueError("Unsupported scoring regression control")
            if actual != control["expected"]:
                raise ValueError("Scoring regression failed: " + identity)


def _qualified(item):
    anchors, sources = item.get("anchors", []), item.get("sources", [])
    observed = set()
    for source in sources:
        if source.get("title") and source.get("excerpt") and source.get("verified_at"):
            observed.add(source["url"])
            if (
                source.get("observation_kind") == "direct_official_source_http"
                and source.get("http_status") == 200
            ):
                observed.add(source.get("final_url"))
            if source.get("observation_kind") == "official_publisher_canonical_link":
                observed.add(source.get("qualifying_link"))
    return bool(anchors and sources and item.get("qualification")) and all(
        a.startswith("https://") and a in observed for a in anchors
    )


def _equivalent(a, b):
    if a.get("error") or b.get("error"):
        return False
    return bool(
        any(
            a.get(k) and b.get(k) and canonical_url(a[k]) == canonical_url(b[k])
            for k in ("final", "canonical")
        )
        or (a.get("text_sha256") and a["text_sha256"] == b.get("text_sha256"))
    )


def normalization_regressions(expected_sha256, normalizer):
    """Exercise frozen projection controls through the execution owner's adapter."""
    path = definition_path("native-normalization-regressions.json")
    if digest(path.read_bytes()) != expected_sha256:
        raise ValueError("Normalization regression binding mismatch")
    if not callable(normalizer):
        raise ValueError("Native normalization requires the execution adapter")
    for group in json.loads(path.read_bytes())["regressions"]:
        for control in group["controls"]:
            try:
                results = normalizer(
                    control["payload"],
                    control["method"],
                    control["protocol"],
                    control["request"],
                )
            except ValueError:
                if control["error"]:
                    continue
                raise
            if (
                control["error"]
                or [r["url"] for r in results] != control["expected_urls"]
            ):
                raise ValueError("Normalization regression failed: " + control["id"])
            metrics = evaluate(control["case"], results)
            if any(metrics[k] != v for k, v in control["expected_metrics"].items()):
                raise ValueError("Task metric regression failed: " + control["id"])


def validate_revision_controls(revision, normalizer=None):
    if not revision.get("normalization"):
        validate_regressions(revision)
        return
    native = {"relative-serp-links", "unsafe-serp-links", "top-five-boundary"}
    ids = revision.get("regression_ids", [])
    if (
        revision["normalization"] != "request-url/1"
        or not native.issubset(ids)
        or len(ids) != len(set(ids))
        or not revision.get("root_cause")
    ):
        raise ValueError(
            "Native normalization revision needs paired URL and cutoff controls"
        )
    shared = [i for i in ids if i not in native]
    if shared:
        validate_regressions(dict(revision, regression_ids=shared))
    normalization_regressions(revision.get("regressions_sha256"), normalizer)


def apply_report_revision(profile, rows, revision, *, artifacts=None, normalizer=None):
    """Add independently observed reference annotations to immutable saved calls."""
    if revision.get("schema") != "web-search-assessment-revision/1":
        raise ValueError("Unsupported assessment revision")
    validate_revision_controls(revision, normalizer)
    if revision.get("provider_calls") != 0:
        raise ValueError("An annotation revision cannot introduce provider calls")
    revised = deepcopy(profile)
    normalization = revision.get("normalization")
    if normalization:
        revised["protocol"]["result_url_resolution"] = normalization
    cases = {c["id"]: c for c in revised["cases"]}
    seen = set()
    for item in revision.get("cases", []):
        cid = item["case_id"]
        if cid in seen or cid not in cases:
            raise ValueError("Duplicate or unknown annotated case")
        seen.add(cid)
        if cases[cid].get("anchors"):
            raise ValueError("Additional annotations cannot replace existing anchors")
        anchors = item.get("anchors", [])
        if not _qualified(item):
            raise ValueError("Unqualified source anchor")
        cases[cid]["anchors"] = anchors
        cases[cid]["reference_annotation"] = item
    if revision.get("answer_match_rule"):
        if revision["answer_match_rule"] != POLICY_NAME:
            raise ValueError("Unsupported answer matching rule")
        for case in cases.values():
            if case.get("reference_answer"):
                case["answer_match_rule"] = revision["answer_match_rule"]
    if revision.get("answer_match_rule") == POLICY_NAME:
        from .answer_rules import RULE_VERSION, reference_rule

        annotated = any(
            "annotation_cleanup" in reference_rule(c["reference_answer"])
            for c in cases.values()
            if "reference_answer" in c
        )
        if annotated and (
            revision.get("answer_annotation_rule") != RULE_VERSION
            or "published-answer-citation-metadata" not in revision["regression_ids"]
        ):
            raise ValueError(
                "Reference citation cleanup requires a bound scoring revision"
            )
    exclusions = []
    for item in revision.get("reference_adjudications", []):
        cid = item["case_id"]
        case = cases.get(cid, {})
        if (
            cid in exclusions
            or "reference_answer" not in case
            or item.get("query") != case.get("query")
            or item.get("reference_answer") != case["reference_answer"]
            or item.get("quality_excluded") is not True
            or not item.get("reason")
            or not item.get("evidence")
        ):
            raise ValueError(
                "Reference adjudication does not bind the unchanged factual case"
            )
        exclusions.append(cid)
    if exclusions:
        revised["factual_quality_exclusions"] = sorted(exclusions)
        revised["reference_adjudications"] = revision["reference_adjudications"]
    updated, changes = [], []
    for row in rows:
        new = dict(row)
        if (
            normalization
            and row["http_status"] == 200
            and not row.get("transport_exit")
        ):
            path = row["evidence"]["path"]
            if (
                artifacts is None
                or path not in artifacts
                or digest(artifacts[path]) != row["evidence"]["sha256"]
            ):
                raise ValueError("Native artifact binding mismatch")
            try:
                method = next(m for m in revised["methods"] if m["id"] == row["method"])
                new["results"] = normalizer(
                    json.loads(artifacts[path]),
                    method,
                    revised["protocol"],
                    row.get("request"),
                )
                new["error"] = ""
            except (ValueError, TypeError, AttributeError, KeyError):
                # Preserve the original failed response and its unchanged evidence.
                new = dict(row)
        new["metrics"] = evaluate(cases[row["case_id"]], new["results"])
        if (
            new["metrics"] != row["metrics"]
            or new["results"] != row["results"]
            or new.get("error") != row.get("error")
        ):
            change = {
                "id": row["id"],
                "before": row["metrics"],
                "after": new["metrics"],
            }
            if normalization:
                change["normalization"] = {
                    "before_sha256": digest(
                        json.dumps(
                            row["results"], sort_keys=True, ensure_ascii=False
                        ).encode()
                    ),
                    "after_sha256": digest(
                        json.dumps(
                            new["results"], sort_keys=True, ensure_ascii=False
                        ).encode()
                    ),
                    "before_count": len(row["results"]),
                    "after_count": len(new["results"]),
                    "before_error": row.get("error"),
                    "after_error": new.get("error"),
                }
            changes.append(change)
        updated.append(new)
    return revised, updated, changes


def collected_projection(profile, rows, artifacts, normalizer):
    """Reconstruct collection projections through the frozen execution adapter."""
    cases = {c["id"]: c for c in profile["cases"]}
    methods = {m["id"]: m for m in profile["methods"]}
    restored = []
    for row in rows:
        original = dict(row, results=[])
        if row["http_status"] == 200 and not row.get("transport_exit"):
            path = row["evidence"]["path"]
            if (
                path not in artifacts
                or digest(artifacts[path]) != row["evidence"]["sha256"]
            ):
                raise ValueError("Native artifact binding mismatch")
            try:
                original["results"] = normalizer(
                    json.loads(artifacts[path]),
                    methods[row["method"]],
                    profile["protocol"],
                    row.get("request"),
                )
                original["error"] = ""
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                original["error"] = str(exc)
        original["metrics"] = evaluate(cases[row["case_id"]], original["results"])
        restored.append(original)
    return restored


def apply_identity_correction(profile, rows, correction):
    validate_regressions(correction)
    observations = {x["url"]: x for x in correction["observations"]}
    revised = deepcopy(profile)
    cases = {c["id"]: c for c in revised["cases"]}
    for cid, aliases in correction["aliases"].items():
        case = cases[cid]
        for alias, target in aliases.items():
            a, b = observations[alias], observations[target]
            if not _equivalent(a, b):
                raise ValueError("Unproven equivalent page")
            if target not in case.get("anchors", []):
                raise ValueError("Correction must retain the original known target")
        case["identity_aliases"] = dict(aliases)
    validate_cases(
        revised["cases"],
        reference_checks=revised.get("reference_checks"),
        reference_scope=revised.get("protocol", {}).get("reference_scope"),
    )
    updated, changes = [], []
    for row in rows:
        new = dict(row)
        new["metrics"] = evaluate(cases[row["case_id"]], row["results"])
        if new["metrics"] != row["metrics"]:
            changes.append(
                {"id": row["id"], "before": row["metrics"], "after": new["metrics"]}
            )
        updated.append(new)
    return revised, updated, changes


REVISION_AUTHORITY_PATH = definition_path("assessment-revisions.json")


def validate_revision_binding(revision, *, normalizer=None):
    """Reader prose cannot introduce or modify an approved scoring revision."""
    from .inputs import digest

    authority = REVISION_AUTHORITY_PATH
    registered = json.loads(authority.read_text())
    identity = digest(
        json.dumps(
            revision, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    if identity not in registered["approved_sha256"]:
        raise ValueError(
            "Assessment revision is not bound by the versioned scoring authority"
        )
    validate_revision_controls(revision, normalizer)
