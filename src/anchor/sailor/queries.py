"""SQLite queries for provenance reuse recommendations."""

from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from anchor.sailor.config import get_ignored_entity_types, get_ignored_tool_names, is_ignored_tool_name


DEFAULT_SQLITE_FILENAME = "workflow_db.sqlite"
TOOL_INVOCATION_TYPE = "tool_invocation"
INVALID_RECOMMENDATION_TOOL_NAMES = {"error", "unknown_tool"}
FAILED_STATUSES = {"failed", "error", "errored"}
SUCCESS_STATUSES = {"completed", "success", "succeeded"}
DEFAULT_POLICY = "reliability"
SUPPORTED_POLICIES = {"reliability", "speed", "speed_reliability"}


def default_sqlite_path() -> Path:
    """Return Anchor's default SQLite provenance path."""

    return Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor")) / DEFAULT_SQLITE_FILENAME


def get_tool_performance(
    sqlite_path: str | os.PathLike[str] | None = None,
    tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    purpose: str | None = None,
    ignored_tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    ignored_entity_types: str | list[str] | tuple[str, ...] | set[str] | None = None,
    policy: str | None = None,
) -> dict[str, Any]:
    """Summarize historical tool invocation performance from Anchor SQLite provenance."""

    if type(tool_names) == list:
        for tool in tool_names:
            if tool.lower() == "mafft":
                tool = "mafft_sequence_alignment"
            if tool.lower() == "clustalomega" or tool.lower() == "clustalw":
                tool = "clustalw_sequence_alignment"
            if tool.lower() == "muscle":
                tool = "muscle_sequence_alignment"

    resolved_path = _resolve_sqlite_path(sqlite_path)
    if not resolved_path.exists():
        return _no_data_response(resolved_path, "SQLite provenance database was not found.")

    rows = _load_tool_invocations(
        resolved_path,
        tool_names=tool_names,
        purpose=purpose,
        ignored_tool_names=ignored_tool_names,
        ignored_entity_types=ignored_entity_types,
    )
    if not rows:
        return _no_data_response(resolved_path, "No matching tool invocation history was found.")

    summaries = [_summarize_tool(tool_name, tool_rows) for tool_name, tool_rows in _group_by_tool(rows).items()]
    resolved_policy = _resolve_policy(policy)
    summaries.sort(key=lambda summary: _ranking_key(summary, resolved_policy))

    # print("===================================== AQUI")
    # print({
    #     "sqlite_path": str(resolved_path),
    #     "has_data": True,
    #     "tool_count": len(summaries),
    #     "policy": resolved_policy,
    #     "tools": summaries,
    # }
# )

    return {
        "sqlite_path": str(resolved_path),
        "has_data": True,
        "tool_count": len(summaries),
        "policy": resolved_policy,
        "tools": summaries,
    }


def get_tool_failures(
    sqlite_path: str | os.PathLike[str] | None = None,
    tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    limit: int = 20,
    ignored_tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    ignored_entity_types: str | list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, Any]:
    """Return recent failed tool invocations from Anchor SQLite provenance."""

    resolved_path = _resolve_sqlite_path(sqlite_path)
    if not resolved_path.exists():
        return _no_data_response(resolved_path, "SQLite provenance database was not found.")

    rows = [
        row
        for row in _load_tool_invocations(
            resolved_path,
            tool_names=tool_names,
            ignored_tool_names=ignored_tool_names,
            ignored_entity_types=ignored_entity_types,
        )
        if _is_failure(row)
    ]
    rows.sort(key=lambda row: _timestamp_sort_value(row.get("timestamp")), reverse=True)

    failures = [
        {
            "tool_name": row["tool_name"],
            "status": row.get("status"),
            "timestamp": row.get("timestamp"),
            "interaction_id": row.get("interaction_id"),
            "task_exec_id": row.get("task_exec_id"),
            "input_snippet": _snippet(row.get("input")),
            "output_snippet": _snippet(row.get("output")),
            "payload_snippet": _snippet(row.get("payload")),
        }
        for row in rows[: max(limit, 0)]
    ]

    return {
        "sqlite_path": str(resolved_path),
        "has_data": bool(failures),
        "failure_count": len(failures),
        "failures": failures,
        "message": None if failures else "No failed tool invocations were found.",
    }


def compare_tools(
    sqlite_path: str | os.PathLike[str] | None = None,
    tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    purpose: str | None = None,
    ignored_tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    ignored_entity_types: str | list[str] | tuple[str, ...] | set[str] | None = None,
    policy: str | None = None,
) -> dict[str, Any]:
    """Rank tools by reliability first, then duration, then historical usage."""

    if type(tool_names) == list:
        for tool in tool_names:
            if tool.lower() == "mafft":
                tool = "mafft_sequence_alignment"
            if tool.lower() == "clustalomega" or tool.lower() == "clustalw":
                tool = "clustalw_sequence_alignment"
            if tool.lower() == "muscle":
                tool = "muscle_sequence_alignment"

    performance = get_tool_performance(
        sqlite_path=sqlite_path,
        tool_names=tool_names,
        purpose=purpose,
        ignored_tool_names=ignored_tool_names,
        ignored_entity_types=ignored_entity_types,
        policy=policy,
    )
    if not performance.get("has_data"):
        return {
            **performance,
            "recommended_tool": None,
            "recommendation": performance.get("message"),
        }

    ranked_tools = performance["tools"]
    recommended = ranked_tools[0]
    alternatives = ranked_tools[1:]


    # print("===================================== AQUI2")
    # print({
    #     **performance,
    #     "recommended_tool": recommended["tool_name"],
    #     "recommendation": _recommendation_text(recommended, alternatives),
    # })

    return {
        **performance,
        "recommended_tool": recommended["tool_name"],
        "recommendation": _recommendation_text(recommended, alternatives),
    }


def get_execution_recommendations(
    sqlite_path: str | os.PathLike[str] | None = None,
    available_tools: str | list[str] | tuple[str, ...] | set[str] | None = None,
    workflow_goal: str | None = None,
    ignored_tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    ignored_entity_types: str | list[str] | tuple[str, ...] | set[str] | None = None,
    policy: str | None = None,
) -> dict[str, Any]:
    """Recommend execution choices for the currently available tools."""

    if type(available_tools) == list:
        for tool in available_tools:
            if tool.lower() == "mafft":
                tool = "mafft_sequence_alignment"
            if tool.lower() == "clustalomega" or tool.lower() == "clustalw":
                tool = "clustalw_sequence_alignment"
            if tool.lower() == "muscle":
                tool = "muscle_sequence_alignment"

    purpose_filter = None if available_tools else workflow_goal
    comparison = compare_tools(
        sqlite_path=sqlite_path,
        tool_names=available_tools,
        purpose=purpose_filter,
        ignored_tool_names=ignored_tool_names,
        ignored_entity_types=ignored_entity_types,
        policy=policy,
    )
    if not comparison.get("has_data"):
        return {
            "sqlite_path": comparison.get("sqlite_path"),
            "has_data": False,
            "workflow_goal": workflow_goal,
            "policy": _resolve_policy(policy),
            "recommendations": [],
            "message": comparison.get("message") or "No provenance history is available for recommendations.",
        }

    recommendation = {
        "recommended_tool": comparison["recommended_tool"],
        "recommendation": comparison["recommendation"],
        "evidence": [
            _tool_evidence(tool_summary)
            for tool_summary in comparison["tools"]
        ],
    }

    # print("============= REC")
    # print({
    #     "sqlite_path": comparison["sqlite_path"],
    #     "has_data": True,
    #     "workflow_goal": workflow_goal,
    #     "policy": comparison.get("policy"),
    #     "recommendations": [recommendation],
    #     "tools": comparison["tools"],
    # })

    return {
        "sqlite_path": comparison["sqlite_path"],
        "has_data": True,
        "workflow_goal": workflow_goal,
        "policy": comparison.get("policy"),
        "recommendations": [recommendation],
        "tools": comparison["tools"],
    }


def _resolve_sqlite_path(sqlite_path: str | os.PathLike[str] | None) -> Path:
    return Path(sqlite_path) if sqlite_path else default_sqlite_path()


def _no_data_response(sqlite_path: Path, message: str) -> dict[str, Any]:
    return {
        "sqlite_path": str(sqlite_path),
        "has_data": False,
        "tool_count": 0,
        "tools": [],
        "message": message,
    }


def _load_tool_invocations(
    sqlite_path: Path,
    tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    purpose: str | None = None,
    ignored_tool_names: str | list[str] | tuple[str, ...] | set[str] | None = None,
    ignored_entity_types: str | list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict[str, Any]]:
    requested_names = _normalize_names(tool_names)
    ignored_names = get_ignored_tool_names(ignored_tool_names)
    ignored_types = get_ignored_entity_types(ignored_entity_types)
    purpose_value = purpose.lower().strip() if purpose else None

    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                i.interaction_id,
                i.timestamp,
                i.payload_json,
                e.name AS entity_name,
                e.type AS entity_type,
                e.description AS entity_description,
                t.task_exec_id,
                t.status,
                t.input_json,
                t.output_json,
                t.started_at,
                t.ended_at
            FROM interactions i
            LEFT JOIN entities e ON i.target_entity_id = e.entity_id
            LEFT JOIN task_executions t ON i.related_task_exec_id = t.task_exec_id
            WHERE i.type = ?
            ORDER BY i.timestamp DESC
            """,
            (TOOL_INVOCATION_TYPE,),
        ).fetchall()

    invocations = [_row_to_invocation(row) for row in rows]
    invocations = [
        row
        for row in invocations
        if not is_ignored_tool_name(row["tool_name"], ignored_names)
        and row["tool_name"].lower().strip() not in INVALID_RECOMMENDATION_TOOL_NAMES
        and (row.get("entity_type") or "").lower().strip() not in ignored_types
    ]

    if requested_names is not None:
        requested_names = requested_names - ignored_names
        invocations = [row for row in invocations if row["tool_name"].lower().strip() in requested_names]

    if purpose_value:
        invocations = [
            row
            for row in invocations
            if purpose_value in row["tool_name"].lower()
            or purpose_value in (row.get("entity_description") or "").lower()
            or purpose_value in _safe_json_text(row.get("payload")).lower()
        ]

    return invocations


def _row_to_invocation(row: sqlite3.Row) -> dict[str, Any]:
    payload = _parse_json(row["payload_json"])
    output = _parse_json(row["output_json"])
    input_value = _parse_json(row["input_json"])
    tool_name = row["entity_name"] or _tool_name_from_payload(payload) or "unknown_tool"

    return {
        "interaction_id": row["interaction_id"],
        "task_exec_id": row["task_exec_id"],
        "timestamp": row["timestamp"],
        "payload": payload,
        "tool_name": tool_name,
        "entity_type": row["entity_type"],
        "entity_description": row["entity_description"],
        "status": row["status"],
        "input": input_value,
        "output": output,
        "duration_seconds": _duration_seconds(row["started_at"], row["ended_at"]),
    }


def _tool_name_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    for key in ("tool_name", "name", "span_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    output = payload.get("output")
    if isinstance(output, dict):
        value = output.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _normalize_names(tool_names: str | list[str] | tuple[str, ...] | set[str] | None) -> set[str] | None:
    if tool_names is None:
        return None
    if isinstance(tool_names, str):
        names = [tool_names]
    else:
        names = list(tool_names)
    normalized = {name.lower().strip() for name in names if name and name.strip()}
    return normalized or None


def _group_by_tool(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["tool_name"]].append(row)
    return grouped


def _summarize_tool(tool_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    success_count = sum(1 for row in rows if _is_success(row))
    failure_count = sum(1 for row in rows if _is_failure(row))
    durations = [row["duration_seconds"] for row in rows if row["duration_seconds"] is not None]
    invocation_count = len(rows)
    failure_rate = failure_count / invocation_count if invocation_count else 0.0

    recent_failures = [
        {
            "status": row.get("status"),
            "timestamp": row.get("timestamp"),
            "output_snippet": _snippet(row.get("output")),
            "payload_snippet": _snippet(row.get("payload")),
        }
        for row in rows
        if _is_failure(row)
    ][:3]

    recent_outputs = [
        {
            "status": row.get("status"),
            "timestamp": row.get("timestamp"),
            "output_snippet": _snippet(row.get("output")),
        }
        for row in rows[:3]
    ]

    return {
        "tool_name": tool_name,
        "invocation_count": invocation_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "failure_rate": round(failure_rate, 4),
        "average_duration_seconds": round(sum(durations) / len(durations), 4) if durations else None,
        "recent_failures": recent_failures,
        "recent_outputs": recent_outputs,
        "recommendation_text": _single_tool_recommendation(
            tool_name,
            invocation_count,
            success_count,
            failure_count,
            failure_rate,
            durations,
        ),
    }


def _is_success(row: dict[str, Any]) -> bool:
    status = (row.get("status") or "").lower()
    return status in SUCCESS_STATUSES


def _is_failure(row: dict[str, Any]) -> bool:
    status = (row.get("status") or "").lower()
    return status in FAILED_STATUSES


def _resolve_policy(policy: str | None = None) -> str:
    resolved = (policy or os.getenv("ANCHOR_SAILOR_POLICY") or DEFAULT_POLICY).strip().lower()
    if resolved == "none":
        resolved = DEFAULT_POLICY
    if resolved not in SUPPORTED_POLICIES:
        supported = ", ".join(sorted(SUPPORTED_POLICIES))
        raise ValueError(f"Unsupported Sailor policy {resolved!r}. Supported values: {supported}")
    return resolved


def _max_failure_rate() -> float:
    return float(os.getenv("ANCHOR_SAILOR_MAX_FAILURE_RATE", "0.2"))


def _ranking_key(summary: dict[str, Any], policy: str) -> tuple[float, float, int]:
    duration = summary["average_duration_seconds"]
    duration_score = duration if duration is not None else float("inf")
    failure_rate = summary["failure_rate"]
    failure_threshold_penalty = 0 if failure_rate <= _max_failure_rate() else 1

    if policy == "speed":
        return (failure_threshold_penalty, duration_score, failure_rate, -summary["invocation_count"])
    if policy == "speed_reliability":
        return (failure_threshold_penalty, duration_score, failure_rate, -summary["invocation_count"])

    return (failure_rate, duration_score, -summary["invocation_count"])


def _recommendation_text(recommended: dict[str, Any], alternatives: list[dict[str, Any]]) -> str:
    base = (
        f"Prefer {recommended['tool_name']} based on {recommended['invocation_count']} prior invocation(s), "
        f"{recommended['success_count']} success(es), {recommended['failure_count']} failure(s), "
        f"and a {recommended['failure_rate']:.0%} failure rate"
    )
    if recommended["average_duration_seconds"] is not None:
        base += f" with {recommended['average_duration_seconds']}s average duration"
    base += "."

    if alternatives:
        alt = alternatives[0]
        base += (
            f" The nearest alternative is {alt['tool_name']} with "
            f"{alt['failure_count']} failure(s) across {alt['invocation_count']} invocation(s)."
        )

    return base


def _single_tool_recommendation(
    tool_name: str,
    invocation_count: int,
    success_count: int,
    failure_count: int,
    failure_rate: float,
    durations: list[float],
) -> str:
    duration_text = ""
    if durations:
        duration_text = f" Average duration was {round(sum(durations) / len(durations), 4)}s."
    return (
        f"{tool_name} has {invocation_count} recorded invocation(s), {success_count} success(es), "
        f"{failure_count} failure(s), and a {failure_rate:.0%} failure rate."
        f"{duration_text}"
    )


def _tool_evidence(tool_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool_summary["tool_name"],
        "invocation_count": tool_summary["invocation_count"],
        "success_count": tool_summary["success_count"],
        "failure_count": tool_summary["failure_count"],
        "failure_rate": tool_summary["failure_rate"],
        "average_duration_seconds": tool_summary["average_duration_seconds"],
        "recent_failures": tool_summary["recent_failures"],
    }


def _duration_seconds(started_at: str | None, ended_at: str | None) -> float | None:
    if not started_at or not ended_at:
        return None
    started = _parse_datetime(started_at)
    ended = _parse_datetime(ended_at)
    if started is None or ended is None:
        return None
    duration = (ended - started).total_seconds()
    return duration if duration >= 0 else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _timestamp_sort_value(value: str | None) -> datetime:
    return _parse_datetime(value) or datetime.min


def _parse_json(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _safe_json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def _snippet(value: Any, max_length: int = 240) -> str | None:
    text = _safe_json_text(value).strip()
    if not text:
        return None
    return text if len(text) <= max_length else f"{text[: max_length - 3]}..."
