from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from examples.beeai.synthetic_phylogenetic_subtrees.experiment_metrics import generate_experiment_metrics


def run_experiment(
    condition: str,
    runs: int,
    anchor_output_path: Path,
    sailor_policy: str,
    seed_sqlite_from: Path | None = None,
) -> None:
    anchor_output_path.mkdir(parents=True, exist_ok=True)
    sqlite_path = anchor_output_path / "workflow_db.sqlite"

    if seed_sqlite_from:
        shutil.copy2(seed_sqlite_from, sqlite_path)

    sailor_enabled = sailor_policy != "none"
    config = {
        "condition": condition,
        "runs_expected": runs,
        "anchor_output_path": str(anchor_output_path),
        "sailor_enabled": sailor_enabled,
        "sailor_policy": sailor_policy,
        "seed_sqlite_from": str(seed_sqlite_from) if seed_sqlite_from else None,
    }
    with (anchor_output_path / "experiment_config.json").open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, sort_keys=True)

    env = os.environ.copy()
    env["ANCHOR_OUTPUT_PATH"] = str(anchor_output_path)
    env["ANCHOR_PERSISTENCE_BACKEND"] = "sqlite"
    env["ANCHOR_SAILOR_ENABLED"] = "true" if sailor_enabled else "false"
    env["ANCHOR_SAILOR_POLICY"] = "reliability" if sailor_policy == "none" else sailor_policy

    for index in range(1, runs + 1):
        print(f"[{condition}] run {index}/{runs}")
        subprocess.run(
            [sys.executable, "-m", "examples.beeai.synthetic_phylogenetic_subtrees.main"],
            check=True,
            env=env,
        )

    generate_experiment_metrics(
        sqlite_path=sqlite_path,
        output_dir=anchor_output_path,
        condition=condition,
        sailor_policy=sailor_policy,
        sailor_enabled=sailor_enabled,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run synthetic phylogenetic Sailor experiments.")
    parser.add_argument("--condition", required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--anchor-output-path", type=Path, required=True)
    parser.add_argument(
        "--sailor-policy",
        choices=["none", "reliability", "speed", "speed_reliability"],
        default="none",
    )
    parser.add_argument("--seed-sqlite-from", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_experiment(
        condition=args.condition,
        runs=args.runs,
        anchor_output_path=args.anchor_output_path,
        sailor_policy=args.sailor_policy,
        seed_sqlite_from=args.seed_sqlite_from,
    )


if __name__ == "__main__":
    main()
