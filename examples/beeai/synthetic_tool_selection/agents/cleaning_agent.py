from typing import List

from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool

from examples.beeai.synthetic_tool_selection.constants import OLLAMA_LLM
from examples.beeai.synthetic_tool_selection.agents.requirements import require_stage_tool_before_final_answer


def create_cleaning_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            require_stage_tool_before_final_answer(["fast_cleaner", "balanced_cleaner", "strict_cleaner"]),
            ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False),
        ],
        name="cleaning_agent",
        role="synthetic data cleaning specialist",
        instructions=(
            "You perform the cleaning stage of a synthetic benchmark workflow. "
            "You have multiple tools with the same purpose: fast_cleaner, balanced_cleaner, and strict_cleaner. "
            "Use exactly one cleaning tool unless it fails; if it fails, try a different cleaning tool. "
            "You must call a cleaning MCP tool in this task before returning any answer. "
            "Return only the path produced by the successful cleaning tool in this task. "
            "Do not invent paths and do not reuse paths from previous runs."
        ),
    )
