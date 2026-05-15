from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from anchor.telemetry.persistence.tinydb_to_sql import (
    create_schema,
    dumps_json,
)


DB_DIR = Path(os.getenv("ANCHOR_OUTPUT_PATH", ".anchor"))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "workflow_db.sqlite"


class SQLiteTable:
    def __init__(self, name: str, id_field: str, columns: tuple[str, ...]) -> None:
        self.name = name
        self.id_field = id_field
        self.columns = columns


workflow_def_table = SQLiteTable(
    "workflow_definitions",
    "workflow_def_id",
    ("workflow_def_id", "name", "description"),
)
workflow_exec_table = SQLiteTable(
    "workflow_executions",
    "workflow_exec_id",
    (
        "workflow_exec_id",
        "workflow_def_id",
        "root_interaction_id",
        "goal",
        "final_output_json",
        "status",
        "started_at",
        "ended_at",
        "error_message",
        "aggregated_model_metrics_json",
    ),
)
entity_table = SQLiteTable(
    "entities",
    "entity_id",
    (
        "entity_id",
        "type",
        "name",
        "description",
        "supervisor_id",
        "model_config_json",
        "tool_schema_json",
    ),
)
capability_table = SQLiteTable(
    "capabilities",
    "capability_id",
    (
        "capability_id",
        "owner_entity_id",
        "target_entity_id",
        "type",
        "granted_by",
        "granted_at",
        "valid_from",
        "valid_until",
        "constraints_json",
    ),
)
intention_table = SQLiteTable(
    "intentions",
    "intention_id",
    (
        "intention_id",
        "created_by_entity_id",
        "goal",
        "reasoning",
        "confidence",
        "evidence_json",
        "timestamp",
    ),
)
task_exec_table = SQLiteTable(
    "task_executions",
    "task_exec_id",
    (
        "task_exec_id",
        "workflow_exec_id",
        "parent_task_exec_id",
        "created_by_entity_id",
        "created_by_interaction_id",
        "assigned_to_entity_id",
        "status",
        "input_json",
        "output_json",
        "started_at",
        "ended_at",
        "metrics_json",
    ),
)
interaction_table = SQLiteTable(
    "interactions",
    "interaction_id",
    (
        "interaction_id",
        "workflow_exec_id",
        "source_entity_id",
        "target_entity_id",
        "type",
        "related_task_exec_id",
        "based_on_intention_id",
        "caused_by_interaction_id",
        "payload_json",
        "timestamp",
    ),
)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    create_schema(connection, drop_existing=False)
    return connection


def _model_dump(model: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(model, BaseModel):
        return model.model_dump(mode="json", by_alias=True)
    return dict(model)


def _table_row(table: SQLiteTable, data: dict[str, Any]) -> dict[str, Any]:
    if table is workflow_exec_table:
        data = {
            **data,
            "final_output_json": dumps_json(data.get("final_output")),
            "aggregated_model_metrics_json": dumps_json(data.get("aggregated_model_metrics")),
        }
    elif table is entity_table:
        data = {
            **data,
            "model_config_json": dumps_json(data.get("model_config")),
            "tool_schema_json": dumps_json(data.get("tool_schema")),
        }
    elif table is capability_table:
        data = {**data, "constraints_json": dumps_json(data.get("constraints"))}
    elif table is intention_table:
        data = {**data, "evidence_json": dumps_json(data.get("evidence"))}
    elif table is task_exec_table:
        data = {
            **data,
            "input_json": dumps_json(data.get("input")),
            "output_json": dumps_json(data.get("output")),
            "metrics_json": dumps_json(data.get("metrics")),
        }
    elif table is interaction_table:
        data = {**data, "payload_json": dumps_json(data.get("payload"))}

    return {column: data.get(column) for column in table.columns}


def serialize(model: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return _model_dump(model)


def save(table: SQLiteTable, model: BaseModel | dict[str, Any]) -> None:
    update(table, model, table.id_field)


def update(table: SQLiteTable, model: BaseModel | dict[str, Any], id_field: str | None = None) -> None:
    data = _table_row(table, _model_dump(model))
    columns = tuple(data)
    placeholders = ", ".join("?" for _ in columns)
    assignments = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column != (id_field or table.id_field)
    )

    sql = (
        f"INSERT INTO {table.name} ({', '.join(columns)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT({id_field or table.id_field}) DO UPDATE SET {assignments}"
    )

    with _connect() as connection:
        connection.execute(sql, tuple(data[column] for column in columns))
        connection.commit()


def get_by_id(table: SQLiteTable, field_name: str, value: Any) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT * FROM {table.name} WHERE {field_name} = ?",
            (str(value),),
        ).fetchone()
    return dict(row) if row is not None else None
