from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from anchor.sailor import compare_tools, get_execution_recommendations, get_tool_failures, get_tool_performance
from anchor.telemetry.persistence.tinydb_to_sql import create_schema


class SailorQueryTests(unittest.TestCase):
    def test_empty_database_returns_no_data(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            result = get_tool_performance(sqlite_path)

        self.assertFalse(result["has_data"])
        self.assertEqual(result["tools"], [])

    def test_repeated_failures_produce_higher_failure_rate(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "fast_tool", "completed")
            insert_tool_invocation(sqlite_path, "fragile_tool", "failed")
            insert_tool_invocation(sqlite_path, "fragile_tool", "failed")

            result = get_tool_performance(sqlite_path)

        tools = {tool["tool_name"]: tool for tool in result["tools"]}
        self.assertEqual(tools["fast_tool"]["failure_rate"], 0.0)
        self.assertEqual(tools["fragile_tool"]["failure_rate"], 1.0)
        self.assertEqual(tools["fragile_tool"]["failure_count"], 2)

    def test_successful_tools_rank_above_failed_tools(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "reliable_tool", "completed", duration_seconds=8)
            insert_tool_invocation(sqlite_path, "broken_tool", "failed", duration_seconds=1)

            result = compare_tools(sqlite_path, tool_names=["reliable_tool", "broken_tool"])

        self.assertEqual(result["recommended_tool"], "reliable_tool")
        self.assertIn("reliable_tool", result["recommendation"])
        self.assertIn("0 failure(s)", result["recommendation"])

    def test_duration_summaries_ignore_missing_timestamps(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "mixed_tool", "completed", duration_seconds=4)
            insert_tool_invocation(sqlite_path, "mixed_tool", "completed")

            result = get_tool_performance(sqlite_path, tool_names=["mixed_tool"])

        self.assertEqual(result["tools"][0]["average_duration_seconds"], 4.0)

    def test_recommendations_include_evidence(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "alignment_a", "completed", duration_seconds=3)
            insert_tool_invocation(sqlite_path, "alignment_b", "failed", output={"error": "bad input"})

            result = get_execution_recommendations(
                sqlite_path,
                available_tools=["alignment_a", "alignment_b"],
                workflow_goal="alignment",
            )

        self.assertTrue(result["has_data"])
        evidence = result["recommendations"][0]["evidence"]
        self.assertEqual(evidence[0]["tool_name"], "alignment_a")
        self.assertIn("failure_rate", evidence[0])

    def test_recent_failures_include_snippets(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "fragile_tool", "failed", output={"error": "timeout"})

            result = get_tool_failures(sqlite_path, tool_names=["fragile_tool"])

        self.assertTrue(result["has_data"])
        self.assertIn("timeout", result["failures"][0]["output_snippet"])

    def test_internal_beeai_tools_are_ignored_by_default(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "think", "completed", duration_seconds=1)
            insert_tool_invocation(sqlite_path, "final_answer", "completed", duration_seconds=1)
            insert_tool_invocation(sqlite_path, "domain_tool", "completed", duration_seconds=2)

            result = get_tool_performance(sqlite_path)

        tool_names = [tool["tool_name"] for tool in result["tools"]]
        self.assertEqual(tool_names, ["domain_tool"])

    def test_internal_tools_are_ignored_even_when_passed_as_available_tools(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "final_answer", "completed", duration_seconds=1)
            insert_tool_invocation(sqlite_path, "useful_tool", "completed", duration_seconds=3)

            result = get_execution_recommendations(
                sqlite_path,
                available_tools=["final_answer", "useful_tool"],
                workflow_goal="synthetic goal",
            )

        self.assertTrue(result["has_data"])
        self.assertEqual(result["recommendations"][0]["recommended_tool"], "useful_tool")
        self.assertEqual([tool["tool_name"] for tool in result["tools"]], ["useful_tool"])

    def test_agent_handoff_targets_are_ignored_by_default(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "cleaning_agent", "completed", entity_type="agent")
            insert_tool_invocation(sqlite_path, "domain_cleaner", "completed", entity_type="tool")

            result = get_tool_performance(sqlite_path)

        self.assertTrue(result["has_data"])
        self.assertEqual([tool["tool_name"] for tool in result["tools"]], ["domain_cleaner"])

    def test_sailor_query_tools_are_ignored_by_default(self) -> None:
        with temporary_anchor_db() as sqlite_path:
            insert_tool_invocation(sqlite_path, "get_execution_recommendations", "completed")
            insert_tool_invocation(sqlite_path, "compare_tools", "completed")
            insert_tool_invocation(sqlite_path, "useful_tool", "completed")

            result = get_tool_performance(sqlite_path)

        self.assertTrue(result["has_data"])
        self.assertEqual([tool["tool_name"] for tool in result["tools"]], ["useful_tool"])


def temporary_anchor_db():
    return TemporaryAnchorDb()


class TemporaryAnchorDb:
    def __enter__(self) -> Path:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "workflow_db.sqlite"
        with sqlite3.connect(self.path) as connection:
            create_schema(connection, drop_existing=True)
            connection.execute(
                "INSERT INTO workflow_definitions (workflow_def_id, name) VALUES (?, ?)",
                ("workflow_def", "Workflow"),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions (
                    workflow_exec_id, workflow_def_id, goal, status, started_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ("workflow_exec", "workflow_def", "test goal", "completed", "2026-01-01T00:00:00"),
            )
            connection.execute(
                "INSERT INTO entities (entity_id, type, name) VALUES (?, ?, ?)",
                ("agent", "agent", "orchestrator"),
            )
            connection.commit()
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tempdir.cleanup()


def insert_tool_invocation(
    sqlite_path: Path,
    tool_name: str,
    status: str,
    *,
    duration_seconds: int | None = None,
    output: dict | None = None,
    entity_type: str = "tool",
) -> None:
    sequence = next_sequence(sqlite_path)
    tool_id = f"tool_{tool_name}"
    task_id = f"task_{sequence}"
    interaction_id = f"interaction_{sequence}"
    started_at = None
    ended_at = None
    if duration_seconds is not None:
        started_at = "2026-01-01T00:00:00"
        ended_at = f"2026-01-01T00:00:{duration_seconds:02d}"

    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO entities (entity_id, type, name) VALUES (?, ?, ?)",
            (tool_id, entity_type, tool_name),
        )
        connection.execute(
            """
            INSERT INTO task_executions (
                task_exec_id, workflow_exec_id, created_by_entity_id, assigned_to_entity_id,
                status, output_json, started_at, ended_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                "workflow_exec",
                "agent",
                tool_id,
                status,
                json.dumps(output or {"result": status}),
                started_at,
                ended_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO interactions (
                interaction_id, workflow_exec_id, source_entity_id, target_entity_id,
                type, related_task_exec_id, payload_json, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction_id,
                "workflow_exec",
                "agent",
                tool_id,
                "tool_invocation",
                task_id,
                json.dumps({"span_name": tool_name}),
                f"2026-01-01T00:00:{sequence:02d}",
            ),
        )
        connection.commit()


def next_sequence(sqlite_path: Path) -> int:
    with sqlite3.connect(sqlite_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    return count + 1


if __name__ == "__main__":
    unittest.main()
