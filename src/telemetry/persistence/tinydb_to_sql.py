"""Export a TinyDB workflow database to relational SQLite."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

from anchor.model.interaction_oriented import (
    Capability,
    Entity,
    Intention,
    Interaction,
    TaskExecution,
    WorkflowDefinition,
    WorkflowExecution,
)
DEFAULT_ANCHOR_OUTPUT_PATH = Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor"))
DEFAULT_TINYDB_PATH = DEFAULT_ANCHOR_OUTPUT_PATH / "workflow_db.json"
DEFAULT_SQLITE_PATH = DEFAULT_ANCHOR_OUTPUT_PATH / "workflow_db.sqlite"

TABLE_MODELS = {
    "workflow_definitions": WorkflowDefinition,
    "workflow_executions": WorkflowExecution,
    "entity_table": Entity,
    "capabilities": Capability,
    "intention_table": Intention,
    "task_executions": TaskExecution,
    "interaction_table": Interaction,
}


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Unsupported value for JSON serialization: {type(value)!r}")


def dumps_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=json_default, ensure_ascii=True, sort_keys=True)


def load_tinydb_dump(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    expected_tables = set(TABLE_MODELS)
    missing_tables = expected_tables.difference(data)
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise ValueError(f"TinyDB JSON is missing required tables: {missing}")

    return data


def validate_rows(table_name: str, rows: Iterable[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    model = TABLE_MODELS[table_name]
    validated_rows: list[tuple[str, dict[str, Any]]] = []

    for doc_id, row in rows:
        validated = model.model_validate(row)
        validated_rows.append((doc_id, validated.model_dump(mode="json", by_alias=True)))

    return validated_rows


def create_schema(connection: sqlite3.Connection, drop_existing: bool = True) -> None:
    drop_statements = """
        DROP TABLE IF EXISTS interactions;
        DROP TABLE IF EXISTS task_executions;
        DROP TABLE IF EXISTS intentions;
        DROP TABLE IF EXISTS capabilities;
        DROP TABLE IF EXISTS entities;
        DROP TABLE IF EXISTS workflow_executions;
        DROP TABLE IF EXISTS workflow_definitions;
    """ if drop_existing else ""

    connection.executescript(
        f"""
        PRAGMA foreign_keys = ON;

        {drop_statements}

        CREATE TABLE IF NOT EXISTS workflow_definitions (
            workflow_def_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            tinydb_doc_id TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS workflow_executions (
            workflow_exec_id TEXT PRIMARY KEY,
            workflow_def_id TEXT NOT NULL,
            root_interaction_id TEXT,
            goal TEXT,
            final_output_json TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            error_message TEXT,
            aggregated_model_metrics_json TEXT,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (workflow_def_id) REFERENCES workflow_definitions(workflow_def_id)
        );

        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            supervisor_id TEXT,
            model_config_json TEXT,
            tool_schema_json TEXT,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (supervisor_id) REFERENCES entities(entity_id)
        );

        CREATE TABLE IF NOT EXISTS capabilities (
            capability_id TEXT PRIMARY KEY,
            owner_entity_id TEXT NOT NULL,
            target_entity_id TEXT NOT NULL,
            type TEXT NOT NULL,
            granted_by TEXT,
            granted_at TEXT,
            valid_from TEXT,
            valid_until TEXT,
            constraints_json TEXT,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (granted_by) REFERENCES entities(entity_id)
        );

        CREATE TABLE IF NOT EXISTS intentions (
            intention_id TEXT PRIMARY KEY,
            created_by_entity_id TEXT NOT NULL,
            goal TEXT,
            reasoning TEXT,
            confidence TEXT NOT NULL,
            evidence_json TEXT,
            timestamp TEXT NOT NULL,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (created_by_entity_id) REFERENCES entities(entity_id)
        );

        CREATE TABLE IF NOT EXISTS task_executions (
            task_exec_id TEXT PRIMARY KEY,
            workflow_exec_id TEXT NOT NULL,
            parent_task_exec_id TEXT,
            created_by_entity_id TEXT NOT NULL,
            created_by_interaction_id TEXT,
            assigned_to_entity_id TEXT,
            status TEXT NOT NULL,
            input_json TEXT,
            output_json TEXT,
            started_at TEXT,
            ended_at TEXT,
            metrics_json TEXT,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (workflow_exec_id) REFERENCES workflow_executions(workflow_exec_id),
            FOREIGN KEY (parent_task_exec_id) REFERENCES task_executions(task_exec_id),
            FOREIGN KEY (created_by_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (assigned_to_entity_id) REFERENCES entities(entity_id)
        );

        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id TEXT PRIMARY KEY,
            workflow_exec_id TEXT NOT NULL,
            source_entity_id TEXT NOT NULL,
            target_entity_id TEXT,
            type TEXT NOT NULL,
            related_task_exec_id TEXT,
            based_on_intention_id TEXT,
            caused_by_interaction_id TEXT,
            payload_json TEXT,
            timestamp TEXT NOT NULL,
            tinydb_doc_id TEXT UNIQUE,
            FOREIGN KEY (workflow_exec_id) REFERENCES workflow_executions(workflow_exec_id),
            FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (related_task_exec_id) REFERENCES task_executions(task_exec_id),
            FOREIGN KEY (based_on_intention_id) REFERENCES intentions(intention_id),
            FOREIGN KEY (caused_by_interaction_id) REFERENCES interactions(interaction_id)
        );

        CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_def_id
            ON workflow_executions(workflow_def_id);
        CREATE INDEX IF NOT EXISTS idx_entities_supervisor_id
            ON entities(supervisor_id);
        CREATE INDEX IF NOT EXISTS idx_capabilities_owner_entity_id
            ON capabilities(owner_entity_id);
        CREATE INDEX IF NOT EXISTS idx_capabilities_target_entity_id
            ON capabilities(target_entity_id);
        CREATE INDEX IF NOT EXISTS idx_intentions_created_by_entity_id
            ON intentions(created_by_entity_id);
        CREATE INDEX IF NOT EXISTS idx_task_executions_workflow_exec_id
            ON task_executions(workflow_exec_id);
        CREATE INDEX IF NOT EXISTS idx_task_executions_parent_task_exec_id
            ON task_executions(parent_task_exec_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_workflow_exec_id
            ON interactions(workflow_exec_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_source_entity_id
            ON interactions(source_entity_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_target_entity_id
            ON interactions(target_entity_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_related_task_exec_id
            ON interactions(related_task_exec_id);
        """
    )


def insert_workflow_definitions(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO workflow_definitions (
            workflow_def_id, name, description, tinydb_doc_id
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (
                row["workflow_def_id"],
                row["name"],
                row.get("description"),
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_workflow_executions(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO workflow_executions (
            workflow_exec_id, workflow_def_id, root_interaction_id, goal,
            final_output_json, status, started_at, ended_at, error_message,
            aggregated_model_metrics_json, tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["workflow_exec_id"],
                row["workflow_def_id"],
                row.get("root_interaction_id"),
                row.get("goal"),
                dumps_json(row.get("final_output")),
                row["status"],
                row["started_at"],
                row.get("ended_at"),
                row.get("error_message"),
                dumps_json(row.get("aggregated_model_metrics")),
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_entities(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO entities (
            entity_id, type, name, description, supervisor_id,
            model_config_json, tool_schema_json, tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["entity_id"],
                row["type"],
                row["name"],
                row.get("description"),
                row.get("supervisor_id"),
                dumps_json(row.get("model_config")),
                dumps_json(row.get("tool_schema")),
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_capabilities(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO capabilities (
            capability_id, owner_entity_id, target_entity_id, type, granted_by,
            granted_at, valid_from, valid_until, constraints_json, tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["capability_id"],
                row["owner_entity_id"],
                row["target_entity_id"],
                row["type"],
                row.get("granted_by"),
                row.get("granted_at"),
                row.get("valid_from"),
                row.get("valid_until"),
                dumps_json(row.get("constraints")),
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_intentions(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO intentions (
            intention_id, created_by_entity_id, goal, reasoning, confidence,
            evidence_json, timestamp, tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["intention_id"],
                row["created_by_entity_id"],
                row.get("goal"),
                row.get("reasoning"),
                row["confidence"],
                dumps_json(row.get("evidence")),
                row["timestamp"],
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_task_executions(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO task_executions (
            task_exec_id, workflow_exec_id, parent_task_exec_id,
            created_by_entity_id, created_by_interaction_id, assigned_to_entity_id,
            status, input_json, output_json, started_at, ended_at, metrics_json,
            tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["task_exec_id"],
                row["workflow_exec_id"],
                row.get("parent_task_exec_id"),
                row["created_by_entity_id"],
                row.get("created_by_interaction_id"),
                row.get("assigned_to_entity_id"),
                row["status"],
                dumps_json(row.get("input")),
                dumps_json(row.get("output")),
                row.get("started_at"),
                row.get("ended_at"),
                dumps_json(row.get("metrics")),
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def insert_interactions(connection: sqlite3.Connection, rows: list[tuple[str, dict[str, Any]]]) -> None:
    connection.executemany(
        """
        INSERT INTO interactions (
            interaction_id, workflow_exec_id, source_entity_id, target_entity_id,
            type, related_task_exec_id, based_on_intention_id, caused_by_interaction_id,
            payload_json, timestamp, tinydb_doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["interaction_id"],
                row["workflow_exec_id"],
                row["source_entity_id"],
                row.get("target_entity_id"),
                row["type"],
                row.get("related_task_exec_id"),
                row.get("based_on_intention_id"),
                row.get("caused_by_interaction_id"),
                dumps_json(row.get("payload")),
                row["timestamp"],
                doc_id,
            )
            for doc_id, row in rows
        ],
    )


def export_tinydb_to_sqlite(
    tinydb_path: Path = DEFAULT_TINYDB_PATH,
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
) -> dict[str, int]:
    data = load_tinydb_dump(tinydb_path)

    validated_tables = {
        table_name: validate_rows(table_name, table_data.items())
        for table_name, table_data in data.items()
        if table_name in TABLE_MODELS
    }

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()

    with sqlite3.connect(sqlite_path) as connection:
        create_schema(connection)
        insert_workflow_definitions(connection, validated_tables["workflow_definitions"])
        insert_workflow_executions(connection, validated_tables["workflow_executions"])
        insert_entities(connection, validated_tables["entity_table"])
        insert_capabilities(connection, validated_tables["capabilities"])
        insert_intentions(connection, validated_tables["intention_table"])
        insert_task_executions(connection, validated_tables["task_executions"])
        insert_interactions(connection, validated_tables["interaction_table"])
        connection.commit()

    return {table_name: len(rows) for table_name, rows in validated_tables.items()}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tinydb-path",
        type=Path,
        default=DEFAULT_TINYDB_PATH,
        help=f"Path to the TinyDB JSON dump. Default: {DEFAULT_TINYDB_PATH}",
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help=f"Output path for the SQLite database. Default: {DEFAULT_SQLITE_PATH}",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    counts = export_tinydb_to_sqlite(
        tinydb_path=args.tinydb_path.resolve(),
        sqlite_path=args.sqlite_path.resolve(),
    )

    print(f"SQLite export created at: {args.sqlite_path.resolve()}")
    for table_name, count in counts.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
