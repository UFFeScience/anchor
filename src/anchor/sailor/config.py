"""Configuration helpers for Sailor provenance queries."""

from __future__ import annotations

import os


DEFAULT_IGNORED_TOOL_NAMES = frozenset(
    {
        "compare_tools",
        "final_answer",
        "final_answer_tool",
        "FinalAnswerTool",
        "get_execution_recommendations",
        "get_tool_failures",
        "get_tool_performance",
        "handoff",
        "handoff_tool",
        "HandoffTool",
        "provenance_agent",
        "think",
        "think_tool",
        "ThinkTool",
    }
)

DEFAULT_IGNORED_ENTITY_TYPES = frozenset({"agent"})
DEFAULT_IGNORED_TOOL_SUFFIXES = frozenset({"_agent"})


def get_ignored_tool_names(extra_names: str | list[str] | tuple[str, ...] | set[str] | None = None) -> set[str]:
    """Return tool names that Sailor should ignore when mining provenance."""

    ignored = {_normalize_name(name) for name in DEFAULT_IGNORED_TOOL_NAMES}
    ignored.update(_parse_env_names(os.getenv("ANCHOR_SAILOR_IGNORED_TOOLS")))

    if extra_names:
        if isinstance(extra_names, str):
            ignored.add(_normalize_name(extra_names))
        else:
            ignored.update(_normalize_name(name) for name in extra_names if name)

    return {name for name in ignored if name}


def get_ignored_entity_types(extra_types: str | list[str] | tuple[str, ...] | set[str] | None = None) -> set[str]:
    """Return entity types that Sailor should ignore when mining tool provenance."""

    ignored = {_normalize_name(name) for name in DEFAULT_IGNORED_ENTITY_TYPES}
    ignored.update(_parse_env_names(os.getenv("ANCHOR_SAILOR_IGNORED_ENTITY_TYPES")))

    if extra_types:
        if isinstance(extra_types, str):
            ignored.add(_normalize_name(extra_types))
        else:
            ignored.update(_normalize_name(name) for name in extra_types if name)

    return {name for name in ignored if name}


def is_ignored_tool_name(tool_name: str, ignored_names: set[str] | None = None) -> bool:
    """Return true for framework/internal tool names that should not drive recommendations."""

    normalized = _normalize_name(tool_name)
    ignored = ignored_names if ignored_names is not None else get_ignored_tool_names()
    return normalized in ignored or any(normalized.endswith(suffix) for suffix in DEFAULT_IGNORED_TOOL_SUFFIXES)


def _parse_env_names(value: str | None) -> set[str]:
    if not value:
        return set()
    return {_normalize_name(name) for name in value.split(",") if name.strip()}


def _normalize_name(value: str) -> str:
    return value.strip().lower()
