from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from examples.beeai.complex_phylogenetic_subtree.experiment_metrics import generate_experiment_metrics


def run_experiment(
    condition: str,
    runs: int,
    anchor_output_path: Path,
    sailor_policy: str,
    sailor_sqlite_path: Path | None = None,
    seed_sqlite_from: Path | None = None,
    llm: str | None = None,
    sailor_llm: str | None = None,
    time_scale: str | None = None,
    input_path: Path | None = None,
    stop_on_failure: bool = False,
) -> None:
    anchor_output_path.mkdir(parents=True, exist_ok=True)
    logs_dir = anchor_output_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = anchor_output_path / "workflow_db.sqlite"

    if seed_sqlite_from:
        shutil.copy2(seed_sqlite_from, sqlite_path)

    sailor_enabled = sailor_policy != "none"
    config = {
        "condition": condition,
        "runs_expected": runs,
        "anchor_output_path": str(anchor_output_path),
        "logs_dir": str(logs_dir),
        "sailor_enabled": sailor_enabled,
        "sailor_policy": sailor_policy,
        "sailor_sqlite_path": str(sailor_sqlite_path) if sailor_sqlite_path else None,
        "seed_sqlite_from": str(seed_sqlite_from) if seed_sqlite_from else None,
        "llm": llm,
        "sailor_llm": sailor_llm,
        "time_scale": time_scale,
        "input_path": str(input_path) if input_path else None,
        "stop_on_failure": stop_on_failure,
    }
    with (anchor_output_path / "experiment_config.json").open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, sort_keys=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = _with_pythonpath(SRC_PATH, env.get("PYTHONPATH"))
    env["ANCHOR_OUTPUT_PATH"] = str(anchor_output_path)
    env["ANCHOR_PERSISTENCE_BACKEND"] = "sqlite"
    env["ANCHOR_SAILOR_ENABLED"] = "true" if sailor_enabled else "false"
    env["ANCHOR_SAILOR_POLICY"] = "reliability" if sailor_policy == "none" else sailor_policy
    if sailor_sqlite_path:
        env["ANCHOR_SAILOR_SQLITE_PATH"] = str(sailor_sqlite_path)
    else:
        env.pop("ANCHOR_SAILOR_SQLITE_PATH", None)
    if llm:
        env["ANCHOR_LLM"] = llm
    if sailor_llm:
        env["ANCHOR_SAILOR_LLM"] = sailor_llm
    elif llm:
        env["ANCHOR_SAILOR_LLM"] = llm
    if time_scale is not None:
        env["COMPLEX_PHYLO_TIME_SCALE"] = time_scale
    if input_path:
        env["INPUT_PATH"] = str(input_path)

    _check_runtime_dependencies(env)

    process_runs_path = anchor_output_path / "process_runs.jsonl"
    with process_runs_path.open("w", encoding="utf-8") as process_runs_file:
        for index in range(1, runs + 1):
            log_path = logs_dir / f"run_{index:03d}.log"
            started_at = _utc_now()
            started = time.perf_counter()
            print(f"[{condition}] run {index}/{runs} -> {log_path}")

            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write(f"# condition={condition} run={index}/{runs} started_at={started_at}\n")
                log_file.flush()
                completed = subprocess.run(
                    [sys.executable, "-m", "examples.beeai.complex_phylogenetic_subtree.main"],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=env,
                    check=False,
                )

            ended_at = _utc_now()
            duration_seconds = round(time.perf_counter() - started, 6)
            process_run = {
                "condition": condition,
                "run_index": index,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": duration_seconds,
                "return_code": completed.returncode,
                "success": completed.returncode == 0,
                "log_path": str(log_path),
            }
            process_runs_file.write(json.dumps(process_run, sort_keys=True) + "\n")
            process_runs_file.flush()

            print(
                f"[{condition}] run {index}/{runs} finished "
                f"return_code={completed.returncode} duration={duration_seconds}s"
            )
            if completed.returncode != 0 and stop_on_failure:
                raise subprocess.CalledProcessError(completed.returncode, completed.args)

    summary = generate_experiment_metrics(
        sqlite_path=sqlite_path,
        output_dir=anchor_output_path,
        condition=condition,
        sailor_policy=sailor_policy,
        sailor_enabled=sailor_enabled,
    )
    with (anchor_output_path / "experiment_summary.json").open("r+", encoding="utf-8") as file:
        persisted_summary = json.load(file)
        persisted_summary["process_runs_path"] = str(process_runs_path)
        persisted_summary["logs_dir"] = str(logs_dir)
        file.seek(0)
        json.dump(persisted_summary, file, indent=2, sort_keys=True)
        file.truncate()

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"Process run metadata: {process_runs_path}")
    print(f"Terminal logs: {logs_dir}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _with_pythonpath(path: Path, current_pythonpath: str | None) -> str:
    paths = [str(path)]
    if current_pythonpath:
        paths.extend(part for part in current_pythonpath.split(os.pathsep) if part)
    return os.pathsep.join(dict.fromkeys(paths))


def _check_runtime_dependencies(env: dict[str, str]) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mcp, beeai_framework, fastmcp, Bio",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "The Python environment used by this runner is missing BeeAI/MCP dependencies. "
            'Install them with `uv sync --extra beeai` or run with an environment that has the "beeai" extra. '
            f"Python executable: {sys.executable}\n{completed.stdout}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run complex phylogenetic Sailor experiments.")
    parser.add_argument("--condition", required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--anchor-output-path", type=Path, required=True)
    parser.add_argument(
        "--sailor-policy",
        choices=["none", "reliability", "speed", "speed_reliability"],
        default="none",
    )
    parser.add_argument("--seed-sqlite-from", type=Path)
    parser.add_argument(
        "--sailor-sqlite-path",
        type=Path,
        help=(
            "SQLite database that Sailor should read for recommendations. "
            "ANCHOR_OUTPUT_PATH is still used for writing provenance from this experiment."
        ),
    )
    parser.add_argument("--llm", help="LLM used by the workflow agents, e.g. ollama:granite3.3:8b.")
    parser.add_argument(
        "--sailor-llm",
        help="LLM used by the Sailor provenance agent. Defaults to --llm when omitted.",
    )
    parser.add_argument(
        "--time-scale",
        help="Value for COMPLEX_PHYLO_TIME_SCALE, used to scale synthetic tool sleep durations.",
    )
    parser.add_argument("--input-path", type=Path, help="Input FASTA directory passed to the workflow.")
    parser.add_argument("--stop-on-failure", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_experiment(
        condition=args.condition,
        runs=args.runs,
        anchor_output_path=args.anchor_output_path,
        sailor_policy=args.sailor_policy,
        sailor_sqlite_path=args.sailor_sqlite_path,
        seed_sqlite_from=args.seed_sqlite_from,
        llm=args.llm,
        sailor_llm=args.sailor_llm,
        time_scale=args.time_scale,
        input_path=args.input_path,
        stop_on_failure=args.stop_on_failure,
    )


if __name__ == "__main__":
    main()
