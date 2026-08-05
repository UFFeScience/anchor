"""Configurable persistence backend for Anchor telemetry.

Set ``ANCHOR_PERSISTENCE_BACKEND`` to ``sqlite`` or ``tinydb``.
SQLite is the default because Sailor queries provenance with SQL.
"""

from __future__ import annotations

import os
from types import ModuleType


DEFAULT_PERSISTENCE_BACKEND = "sqlite"
SUPPORTED_PERSISTENCE_BACKENDS = {"sqlite", "tinydb"}


def get_persistence_backend_name() -> str:
    backend = os.getenv("ANCHOR_PERSISTENCE_BACKEND", DEFAULT_PERSISTENCE_BACKEND).strip().lower()
    if backend not in SUPPORTED_PERSISTENCE_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_PERSISTENCE_BACKENDS))
        raise ValueError(f"Unsupported ANCHOR_PERSISTENCE_BACKEND={backend!r}. Supported values: {supported}")
    return backend


def _load_backend() -> ModuleType:
    backend = get_persistence_backend_name()
    if backend == "tinydb":
        from anchor.telemetry.persistence import tinydb

        return tinydb

    from anchor.telemetry.persistence import sqlite

    return sqlite


_backend = _load_backend()

workflow_def_table = _backend.workflow_def_table
workflow_exec_table = _backend.workflow_exec_table
capability_table = _backend.capability_table
entity_table = _backend.entity_table
intention_table = _backend.intention_table
task_exec_table = _backend.task_exec_table
interaction_table = _backend.interaction_table

serialize = _backend.serialize
save = _backend.save
update = _backend.update
get_by_id = _backend.get_by_id

__all__ = [
    "DEFAULT_PERSISTENCE_BACKEND",
    "SUPPORTED_PERSISTENCE_BACKENDS",
    "capability_table",
    "entity_table",
    "get_by_id",
    "get_persistence_backend_name",
    "intention_table",
    "interaction_table",
    "save",
    "serialize",
    "task_exec_table",
    "update",
    "workflow_def_table",
    "workflow_exec_table",
]
