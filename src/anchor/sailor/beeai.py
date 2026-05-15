"""BeeAI adapter for Anchor Sailor provenance reuse."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from anchor.sailor.config import get_ignored_entity_types, get_ignored_tool_names
from anchor.sailor.queries import (
    compare_tools,
    get_execution_recommendations,
    get_tool_failures,
    get_tool_performance,
)


DEFAULT_BEEAI_LLM = "ollama:granite3.3:8b"


def create_provenance_agent(llm: str | Any | None = None, sqlite_path: str | Path | None = None):
    """Create a BeeAI RequirementAgent backed by deterministic Sailor query tools."""

    try:
        from beeai_framework.agents.requirement import RequirementAgent
        from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
        from beeai_framework.tools import JSONToolOutput, tool
        from beeai_framework.tools.think import ThinkTool
    except ImportError as exc:
        raise ImportError(
            "BeeAI is required for anchor.sailor.beeai. Install Anchor with the BeeAI extra: "
            'uv sync --extra beeai or uv pip install -e ".[beeai]".'
        ) from exc

    resolved_sqlite_path = str(sqlite_path) if sqlite_path else None
    ignored_tool_names = sorted(get_ignored_tool_names())
    ignored_entity_types = sorted(get_ignored_entity_types())

    @tool(
        name="get_tool_performance",
        description=(
            "Summarize historical Anchor provenance for tool invocations from SQLite. "
            "Use this to inspect invocation counts, success counts, failure counts, failure rates, "
            "average duration, and recent outputs."
        ),
    )
    def tool_performance(tool_names: list[str] | None = None, purpose: str | None = None) -> JSONToolOutput:
        return JSONToolOutput(
            get_tool_performance(
                sqlite_path=resolved_sqlite_path,
                tool_names=tool_names,
                purpose=purpose,
                ignored_tool_names=ignored_tool_names,
                ignored_entity_types=ignored_entity_types,
            )
        )

    @tool(
        name="get_tool_failures",
        description=(
            "Return recent failed tool invocations from Anchor SQLite provenance, including compact "
            "input/output snippets when available."
        ),
    )
    def tool_failures(tool_names: list[str] | None = None, limit: int = 20) -> JSONToolOutput:
        return JSONToolOutput(
            get_tool_failures(
                sqlite_path=resolved_sqlite_path,
                tool_names=tool_names,
                limit=limit,
                ignored_tool_names=ignored_tool_names,
                ignored_entity_types=ignored_entity_types,
            )
        )

    @tool(
        name="compare_tools",
        description=(
            "Compare candidate tools using prior Anchor SQLite provenance. Rank by lower failure rate, "
            "then lower average duration, then stronger historical support."
        ),
    )
    def compare_candidate_tools(tool_names: list[str] | None = None, purpose: str | None = None) -> JSONToolOutput:
        return JSONToolOutput(
            compare_tools(
                sqlite_path=resolved_sqlite_path,
                tool_names=tool_names,
                purpose=purpose,
                ignored_tool_names=ignored_tool_names,
                ignored_entity_types=ignored_entity_types,
            )
        )

    @tool(
        name="get_execution_recommendations",
        description=(
            "Recommend tool choices for an upcoming workflow using only historical Anchor SQLite provenance."
        ),
    )
    def execution_recommendations(
        available_tools: list[str] | None = None,
        workflow_goal: str | None = None,
    ) -> JSONToolOutput:
        return JSONToolOutput(
            get_execution_recommendations(
                sqlite_path=resolved_sqlite_path,
                available_tools=available_tools,
                workflow_goal=workflow_goal,
                ignored_tool_names=ignored_tool_names,
                ignored_entity_types=ignored_entity_types,
            )
        )

    think_tool = ThinkTool()
    return RequirementAgent(
        llm=llm or os.getenv("ANCHOR_SAILOR_LLM") or os.getenv("ANCHOR_LLM") or DEFAULT_BEEAI_LLM,
        tools=[
            tool_performance,
            tool_failures,
            compare_candidate_tools,
            execution_recommendations,
            think_tool,
        ],
        requirements=[ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False)],
        name="provenance_agent",
        role="provenance reuse advisor",
        instructions=(
            "You advise humans and workflow agents using Anchor provenance stored in SQLite. "
            "Answer with evidence from the deterministic provenance tools. Explain tradeoffs in terms of "
            "failure rate, prior successes, prior failures, recent failures, and duration when timestamps exist. "
            "Recommend tool choices only when historical data supports the recommendation. "
            f"Ignore internal framework tools/stages such as: {', '.join(ignored_tool_names)}. "
            f"Ignore provenance rows whose target entity type is: {', '.join(ignored_entity_types)}. "
            "If the SQLite database does not exist or no relevant history exists, say that clearly and do not "
            "invent recommendations. BeeAI is only the adapter; the source of truth is Anchor provenance."
        ),
    )


__all__ = ["create_provenance_agent"]
