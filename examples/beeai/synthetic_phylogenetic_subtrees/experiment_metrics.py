from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from anchor.sailor.config import get_ignored_entity_types, get_ignored_tool_names, is_ignored_tool_name
from examples.commons.synthetic_phylogenetic_subtrees.tool_profiles import TOOL_TO_STAGE


def generate_experiment_metrics(
    sqlite_path: Path,
    output_dir: Path,
    condition: str,
    sailor_policy: str,
    sailor_enabled: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs = collect_runs(sqlite_path, condition, sailor_policy, sailor_enabled)

    runs_path = output_dir / "experiment_runs.jsonl"
    with runs_path.open("w", encoding="utf-8") as file:
        for run in runs:
            file.write(json.dumps(run, sort_keys=True) + "\n")

    summary = summarize_runs(runs, condition, sailor_policy, sailor_enabled)
    summary_path = output_dir / "experiment_summary.json"
    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, sort_keys=True)

    return summary


def collect_runs(sqlite_path: Path, condition: str, sailor_policy: str, sailor_enabled: bool) -> list[dict[str, Any]]:
    if not sqlite_path.exists():
        return []

    ignored_tool_names = get_ignored_tool_names()
    ignored_entity_types = get_ignored_entity_types()

    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        workflows = connection.execute(
            """
            SELECT workflow_exec_id, goal, final_output_json, status, started_at, ended_at, error_message
            FROM workflow_executions
            ORDER BY started_at
            """
        ).fetchall()

    runs = []
    for index, workflow in enumerate(workflows, start=1):
        tool_calls = _load_tool_calls(sqlite_path, workflow["workflow_exec_id"])
        domain_tool_calls = [
            call
            for call in tool_calls
            if not is_ignored_tool_name(call["tool_name"], ignored_tool_names)
            and (call.get("entity_type") or "").lower().strip() not in ignored_entity_types
        ]

        stages = _stage_metrics(domain_tool_calls)
        final_output_path = _extract_path(workflow["final_output_json"])
        workflow_duration = _duration_seconds(workflow["started_at"], workflow["ended_at"])
        failed_tool_calls = [call for call in domain_tool_calls if call["status"] == "failed"]
        successful_tool_calls = [call for call in domain_tool_calls if call["status"] == "completed"]

        runs.append(
            {
                "condition": condition,
                "run_index": index,
                "workflow_exec_id": workflow["workflow_exec_id"],
                "workflow_success": workflow["status"] in {"finished", "completed", "success"},
                "workflow_status": workflow["status"],
                "workflow_duration_seconds": workflow_duration,
                "goal": workflow["goal"],
                "error_message": workflow["error_message"],
                "sailor_enabled": sailor_enabled,
                "sailor_policy": sailor_policy,
                "total_tool_calls": len(domain_tool_calls),
                "successful_tool_calls": len(successful_tool_calls),
                "failed_tool_calls": len(failed_tool_calls),
                "fallback_count": _fallback_count(stages),
                "selected_tools_by_stage": {
                    stage: metrics["selected_tool"]
                    for stage, metrics in stages.items()
                },
                "duration_by_stage": {
                    stage: metrics["duration_seconds"]
                    for stage, metrics in stages.items()
                },
                "failed_attempts_by_stage": {
                    stage: metrics["failed_attempts"]
                    for stage, metrics in stages.items()
                },
                "tool_calls_by_stage": {
                    stage: metrics["tool_calls"]
                    for stage, metrics in stages.items()
                },
                "final_output_path": final_output_path,
                "final_output_path_exists": bool(final_output_path and Path(final_output_path).exists()),
            }
        )

    return runs


def summarize_runs(
    runs: list[dict[str, Any]],
    condition: str,
    sailor_policy: str,
    sailor_enabled: bool,
) -> dict[str, Any]:
    tool_usage_by_stage: dict[str, Counter] = defaultdict(Counter)
    failed_attempts_by_stage: dict[str, list[int]] = defaultdict(list)
    durations_by_stage: dict[str, list[float]] = defaultdict(list)

    for run in runs:
        for stage, tool_name in run["selected_tools_by_stage"].items():
            if tool_name:
                tool_usage_by_stage[stage][tool_name] += 1
        for stage, failed_attempts in run["failed_attempts_by_stage"].items():
            failed_attempts_by_stage[stage].append(failed_attempts)
        for stage, duration in run["duration_by_stage"].items():
            if duration is not None:
                durations_by_stage[stage].append(duration)

    workflow_durations = [run["workflow_duration_seconds"] for run in runs if run["workflow_duration_seconds"] is not None]
    return {
        "condition": condition,
        "sailor_enabled": sailor_enabled,
        "sailor_policy": sailor_policy,
        "total_runs": len(runs),
        "successful_runs": sum(1 for run in runs if run["workflow_success"]),
        "workflow_success_rate": _safe_rate(sum(1 for run in runs if run["workflow_success"]), len(runs)),
        "avg_workflow_duration_seconds": _safe_mean(workflow_durations),
        "avg_total_tool_calls": _safe_mean([run["total_tool_calls"] for run in runs]),
        "avg_failed_tool_calls": _safe_mean([run["failed_tool_calls"] for run in runs]),
        "avg_fallback_count": _safe_mean([run["fallback_count"] for run in runs]),
        "tool_usage_by_stage": {
            stage: dict(counter)
            for stage, counter in sorted(tool_usage_by_stage.items())
        },
        "avg_failed_attempts_by_stage": {
            stage: _safe_mean(values)
            for stage, values in sorted(failed_attempts_by_stage.items())
        },
        "avg_duration_by_stage": {
            stage: _safe_mean(values)
            for stage, values in sorted(durations_by_stage.items())
        },
    }


def _load_tool_calls(sqlite_path: Path, workflow_exec_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                i.interaction_id,
                i.timestamp,
                e.name AS tool_name,
                e.type AS entity_type,
                t.status,
                t.started_at,
                t.ended_at,
                t.output_json
            FROM interactions i
            LEFT JOIN entities e ON i.target_entity_id = e.entity_id
            LEFT JOIN task_executions t ON i.related_task_exec_id = t.task_exec_id
            WHERE i.workflow_exec_id = ?
              AND i.type = 'tool_invocation'
            ORDER BY i.timestamp
            """,
            (workflow_exec_id,),
        ).fetchall()
    return [
        {
            "interaction_id": row["interaction_id"],
            "timestamp": row["timestamp"],
            "tool_name": row["tool_name"] or "unknown_tool",
            "entity_type": row["entity_type"],
            "status": row["status"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "duration_seconds": _duration_seconds(row["started_at"], row["ended_at"]),
            "output_json": row["output_json"],
        }
        for row in rows
    ]


def _stage_metrics(tool_calls: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    calls_by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in tool_calls:
        stage = TOOL_TO_STAGE.get(call["tool_name"], "unknown")
        calls_by_stage[stage].append(call)

    metrics = {}
    for stage, calls in calls_by_stage.items():
        successful_calls = [call for call in calls if call["status"] == "completed"]
        selected_tool = successful_calls[-1]["tool_name"] if successful_calls else None
        metrics[stage] = {
            "selected_tool": selected_tool,
            "tool_calls": len(calls),
            "failed_attempts": sum(1 for call in calls if call["status"] == "failed"),
            "duration_seconds": _safe_sum(call["duration_seconds"] for call in calls),
        }
    return metrics


def _fallback_count(stages: dict[str, dict[str, Any]]) -> int:
    return sum(metrics["failed_attempts"] for metrics in stages.values())


def _extract_path(value: str | None) -> str | None:
    if not value:
        return None
    matches = re.findall(r"/[^\s\"']+", value)
    return matches[-1].rstrip(".,)}]") if matches else None


def _duration_seconds(started_at: str | None, ended_at: str | None) -> float | None:
    if not started_at or not ended_at:
        return None
    started = _parse_datetime(started_at)
    ended = _parse_datetime(ended_at)
    if not started or not ended:
        return None
    return max((ended - started).total_seconds(), 0.0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_sum(values) -> float | None:
    values = [value for value in values if value is not None]
    return round(sum(values), 6) if values else None


def _safe_mean(values) -> float | None:
    values = [value for value in values if value is not None]
    return round(mean(values), 6) if values else None


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic phylogenetic experiment metrics from SQLite.")
    parser.add_argument("--sqlite-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--sailor-policy", default="none")
    parser.add_argument("--sailor-enabled", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = generate_experiment_metrics(
        sqlite_path=args.sqlite_path,
        output_dir=args.output_dir,
        condition=args.condition,
        sailor_policy=args.sailor_policy,
        sailor_enabled=args.sailor_enabled,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
