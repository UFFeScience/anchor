from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.phylogenetic_subtrees.constants import OLLAMA_LLM


def create_tree_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False)],
        name="tree_agent",
        role="phylogenetic inference specialist",
        instructions=(
            "You are responsible for constructing phylogenetic trees from multiple sequence alignment results. "
            "You will receive a path containing alignment files. "
            "Use the available tool to generate phylogenetic trees. "
            "Return the path where the tree results are stored. "
            "Do not attempt to generate trees without valid alignment input. "
            "Do not create new directories. Only use paths provided as input or returned by tools. "
        ),
    )
