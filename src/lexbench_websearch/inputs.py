"""Hash-verified, installed-package benchmark inputs."""

import hashlib
import json
from pathlib import Path

DEFINITIONS = Path(__file__).parent / "definitions"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def definition_path(name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Definition path must be package-relative")
    path = DEFINITIONS / relative
    if path.is_symlink() or not path.resolve().is_relative_to(DEFINITIONS.resolve()):
        raise ValueError("Definition path escapes package")
    return path


def registry():
    return json.loads(definition_path("registry.json").read_bytes())


def load_dataset(identity):
    binding = registry()["datasets"][identity]
    raw = definition_path(binding["path"]).read_bytes()
    if digest(raw) != binding["sha256"]:
        raise ValueError("Benchmark dataset hash mismatch: " + identity)
    dataset = json.loads(raw)
    if dataset["id"] != identity or len(dataset["cases"]) != binding["count"]:
        raise ValueError("Benchmark dataset identity or count mismatch")
    from .contracts import validate_cases

    validate_cases(dataset["cases"])
    return dataset


def resolve_profile(profile):
    """Expand explicit references; retain historical standalone profiles unchanged."""
    profile = dict(profile)
    for field in ("cases", "reference_checks", "reference_artifacts"):
        value = profile.get(field)
        if isinstance(value, dict) and "benchmark_dataset" in value:
            identity = value["benchmark_dataset"]
            if (
                value.get("field") != field
                or value.get("sha256") != registry()["datasets"][identity]["sha256"]
            ):
                raise ValueError("Benchmark field binding mismatch")
            profile[field] = load_dataset(identity)[field]
    return profile


def implementation_sources():
    return {
        "dependencies/lexbench_websearch/" + p.name: p
        for p in sorted(Path(__file__).parent.glob("*.py"))
    }
