from typing import List

from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool

from examples.beeai.synthetic_tool_selection.constants import OLLAMA_LLM
from examples.beeai.synthetic_tool_selection.agents.requirements import require_stage_tool_before_final_answer


def create_scoring_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            require_stage_tool_before_final_answer(["fast_scorer", "accurate_scorer", "unstable_scorer"]),
            ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False),
        ],
        name="scoring_agent",
        role="synthetic result scoring specialist",
        instructions=(
            "You perform the scoring stage of a synthetic benchmark workflow. "
            "You have multiple tools with the same purpose: fast_scorer, accurate_scorer, and unstable_scorer. "
            "Use exactly one scoring tool unless it fails; if it fails, try a different scoring tool. "
            "Use the input path received from the feature extraction stage. "
            "You must call a scoring MCP tool in this task before returning any answer. "
            "Return only the path produced by the successful scoring tool in this task. "
            "Do not invent paths and do not reuse paths from previous runs."
        ),
    )
