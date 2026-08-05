"""BeeAI adapter for Anchor Sailor provenance reuse."""

from __future__ import annotations

import os
import json
import logging
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
logger = logging.getLogger(__name__)


def create_provenance_agent(llm: str | Any | None = None, sqlite_path: str | Path | None = None):
    """Create a BeeAI RequirementAgent backed by deterministic Sailor query tools."""

    try:
        from beeai_framework.agents.requirement import RequirementAgent
        from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
        from beeai_framework.tools import JSONToolOutput, StringToolOutput, tool
        from beeai_framework.tools.think import ThinkTool
    except ImportError as exc:
        raise ImportError(
            "BeeAI is required for anchor.sailor.beeai. Install Anchor with the BeeAI extra: "
            'uv sync --extra beeai or uv pip install -e ".[beeai]".'
        ) from exc

    resolved_sqlite_path = str(sqlite_path or os.getenv("ANCHOR_SAILOR_SQLITE_PATH") or "") or None
    ignored_tool_names = sorted(get_ignored_tool_names())
    ignored_entity_types = sorted(get_ignored_entity_types())
    sailor_policy = os.getenv("ANCHOR_SAILOR_POLICY", "reliability")

    def normalize_tool_names(tool_names: list[str] | None) -> list[str] | None:
        if not isinstance(tool_names, list):
            return tool_names

        aliases = {
            "mafft": "mafft_sequence_alignment",
            "clustalomega": "clustalw_sequence_alignment",
            "clustalw": "clustalw_sequence_alignment",
            "muscle": "muscle_sequence_alignment",
            "fasttree": "fasttree_constructor", 
            "iqtree": "iqtree_constructor",
            "raxml": "raxml_constructor",
        }
        return [aliases.get(tool.lower(), tool) for tool in tool_names]

    def log_sailor_tool_call(tool_name: str, inputs: dict[str, Any], result: dict[str, Any]) -> None:
        logger.warning(
            "Anchor Sailor BeeAI tool call: %s",
            json.dumps(
                {
                    "tool": tool_name,
                    "inputs": inputs,
                    "resolved_sqlite_path": resolved_sqlite_path,
                    "env_anchor_output_path": os.getenv("ANCHOR_OUTPUT_PATH"),
                    "env_anchor_sailor_sqlite_path": os.getenv("ANCHOR_SAILOR_SQLITE_PATH"),
                    "policy": sailor_policy,
                    "result": result,
                },
                ensure_ascii=False,
                default=str,
            ),
        )

    @tool(
        name="get_tool_performance",
        description=(
            "Summarize historical Anchor provenance for tool invocations from SQLite. "
            "Pass candidate tool names in the tool_names argument; do not pass a generic task field. "
            "Use exact MCP tool names when available. "
            "Use this to inspect invocation counts, success counts, failure counts, failure rates, "
            "average duration, and recent outputs."
        ),
    )
    def tool_performance(tool_names: list[str] | None = None, purpose: str | None = None) -> StringToolOutput:
        original_tool_names = list(tool_names) if isinstance(tool_names, list) else tool_names
        tool_names = normalize_tool_names(tool_names)

        result = get_tool_performance(
            sqlite_path=resolved_sqlite_path,
            tool_names=tool_names,
            purpose=purpose,
            ignored_tool_names=ignored_tool_names,
            ignored_entity_types=ignored_entity_types,
            policy=sailor_policy,
        )
        log_sailor_tool_call(
            "get_tool_performance",
            {
                "original_tool_names": original_tool_names,
                "tool_names_after_normalization": tool_names,
                "purpose": purpose,
            },
            result,
        )
        return StringToolOutput(json.dumps(result))

    @tool(
        name="get_tool_failures",
        description=(
            "Return recent failed tool invocations from Anchor SQLite provenance, including compact "
            "input/output snippets when available. Pass candidate tool names in the tool_names argument; "
            "do not pass a generic task field."
        ),
    )
    def tool_failures(tool_names: list[str] | None = None, limit: int = 20) -> StringToolOutput:
        original_tool_names = list(tool_names) if isinstance(tool_names, list) else tool_names
        tool_names = normalize_tool_names(tool_names)

        result = get_tool_failures(
            sqlite_path=resolved_sqlite_path,
            tool_names=tool_names,
            limit=limit,
            ignored_tool_names=ignored_tool_names,
            ignored_entity_types=ignored_entity_types,
        )
        log_sailor_tool_call(
            "get_tool_failures",
            {
                "original_tool_names": original_tool_names,
                "tool_names_after_normalization": tool_names,
                "limit": limit,
            },
            result,
        )
        return StringToolOutput(json.dumps(result))

    @tool(
        name="compare_tools",
        description=(
            "Compare candidate tools using prior Anchor SQLite provenance. Pass the candidate MCP tool "
            "names in the tool_names argument, for example ['fasttree_constructor', 'iqtree_constructor']; "
            "do not pass a generic task field. Rank by the active Sailor policy using historical failure "
            "rate, duration, and support."
        ),
    )
    def compare_candidate_tools(tool_names: list[str] | None = None, purpose: str | None = None) -> StringToolOutput:
        original_tool_names = list(tool_names) if isinstance(tool_names, list) else tool_names
        tool_names = normalize_tool_names(tool_names)

        result = compare_tools(
            sqlite_path=resolved_sqlite_path,
            tool_names=tool_names,
            purpose=purpose,
            ignored_tool_names=ignored_tool_names,
            ignored_entity_types=ignored_entity_types,
            policy=sailor_policy,
        )
        log_sailor_tool_call(
            "compare_tools",
            {
                "original_tool_names": original_tool_names,
                "tool_names_after_normalization": tool_names,
                "purpose": purpose,
            },
            result,
        )
        return StringToolOutput(json.dumps(result))

    @tool(
        name="get_execution_recommendations",
        description=(
            "Recommend tool choices for an upcoming workflow using only historical Anchor SQLite provenance. "
            "Pass candidate MCP tool names in available_tools and the task objective in workflow_goal; "
            "do not pass a generic task field. Use exact MCP tool names when available."
        ),
    )
    def execution_recommendations(
        available_tools: list[str] | None = None,
        workflow_goal: str | None = None,
    ) -> StringToolOutput:
        original_available_tools = list(available_tools) if isinstance(available_tools, list) else available_tools
        available_tools = normalize_tool_names(available_tools)

        result = get_execution_recommendations(
            sqlite_path=resolved_sqlite_path,
            available_tools=available_tools,
            workflow_goal=workflow_goal,
            ignored_tool_names=ignored_tool_names,
            ignored_entity_types=ignored_entity_types,
            policy=sailor_policy,
        )
        log_sailor_tool_call(
            "get_execution_recommendations",
            {
                "original_available_tools": original_available_tools,
                "available_tools_after_normalization": available_tools,
                "workflow_goal": workflow_goal,
            },
            result,
        )
        return StringToolOutput(json.dumps(result))

    # think_tool = ThinkTool()
    return RequirementAgent(
        llm=llm or os.getenv("ANCHOR_SAILOR_LLM") or os.getenv("ANCHOR_LLM") or DEFAULT_BEEAI_LLM,
        tools=[
            tool_performance,
            tool_failures,
            compare_candidate_tools,
            execution_recommendations,
            # think_tool,
        ],
        requirements=[],
        final_answer_as_tool=False,
        name="provenance_agent",
        role="provenance reuse advisor",
        instructions=(
            "You advise humans and workflow agents using Anchor provenance stored in SQLite. "
            "Answer with evidence from the deterministic provenance tools. Explain tradeoffs in terms of "
            "failure rate, prior successes, prior failures, recent failures, and duration when timestamps exist. "
            f"The active recommendation policy is {sailor_policy}. "
            "Recommend tool choices only when historical data supports the recommendation. "
            f"Ignore internal framework tools/stages such as: {', '.join(ignored_tool_names)}. "
            f"Ignore provenance rows whose target entity type is: {', '.join(ignored_entity_types)}. "
            "If the SQLite database does not exist or no relevant history exists, say that clearly and do not "
            "invent recommendations. BeeAI is only the adapter; the source of truth is Anchor provenance."
        ),
    )


__all__ = ["create_provenance_agent"]
