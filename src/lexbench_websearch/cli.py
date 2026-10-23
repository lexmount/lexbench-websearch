"""Offline benchmark inspection, export and deterministic scoring."""

import argparse
import json
from pathlib import Path
from .inputs import load_dataset, registry, digest
from .relevance import query_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("version")
    release = commands.add_parser("release")
    release.add_argument("--dataset", type=Path, required=True)
    release.add_argument("--output", type=Path, required=True)
    release.add_argument("--version", required=True)
    release.add_argument("--scorer-revision", required=True)
    release.add_argument("--previous", type=Path)
    release.add_argument("--change-note")
    compare = commands.add_parser("compare-releases")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    for command in ("validate", "export"):
        sub = commands.add_parser(command)
        sub.add_argument("dataset", choices=list(registry()["datasets"]))
    rebuild = commands.add_parser("rebuild")
    rebuild.add_argument("dataset", choices=["factual-v1"])
    rebuild.add_argument("--csv", type=Path, required=True)
    score = commands.add_parser("score")
    score.add_argument(
        "input", type=Path, help="JSON with ranking, grades and optional cutoff"
    )
    args = parser.parse_args()
    if args.command == "version":
        from .versions import catalog_release

        value = catalog_release()
    elif args.command == "release":
        from .versions import freeze_release

        value = freeze_release(
            args.dataset,
            args.output,
            version=args.version,
            scorer_revision=args.scorer_revision,
            previous=json.loads(args.previous.read_bytes()) if args.previous else None,
            change_note=args.change_note,
        )
    elif args.command == "compare-releases":
        from .versions import compare_releases

        value = compare_releases(
            json.loads(args.left.read_bytes()), json.loads(args.right.read_bytes())
        )
    elif args.command == "list":
        value = registry()
    elif args.command == "rebuild":
        from .simpleqa import rebuild_dataset

        value = rebuild_dataset(args.csv.read_bytes())
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        if digest(raw) != registry()["datasets"][args.dataset]["sha256"]:
            raise ValueError("Rebuilt dataset does not match the registry hash")
        value = {"dataset": args.dataset, "sha256": digest(raw), "valid": True}
    elif args.command == "score":
        packet = json.loads(args.input.read_bytes())
        value = query_metrics(
            packet["ranking"], packet["grades"], packet.get("cutoff", 5)
        )
    else:
        value = load_dataset(args.dataset)
        if args.command == "validate":
            value = {
                "dataset": value["id"],
                "cases": len(value["cases"]),
                "valid": True,
            }
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
