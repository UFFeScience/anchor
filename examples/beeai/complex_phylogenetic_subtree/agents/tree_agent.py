from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM
from examples.beeai.complex_phylogenetic_subtree.agents.requirements import require_stage_tool_before_final_answer


def create_tree_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    # mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            # require_stage_tool_before_final_answer(
            #     ["tree_constructor", "fasttree_constructor", "iqtree_constructor", "raxml_constructor"]
            # ),
            # ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False),
        ],
        name="tree_agent",
        role="phylogenetic inference specialist",
        instructions=(
            "You are responsible for constructing phylogenetic trees from multiple sequence alignment results. "
            "Use exactly one tree construction tool unless it fails; if it fails, try a different tree construction tool. "
            "You have multiple tools with the same purpose: fasttree_constructor, iqtree_constructor and raxml_constructor. Choose one tool. "
            # "If the selected tool succeeds, do not call another tool with the same objective; stop and return the "
            # "response. If the selected tool fails with an execution error, try another tool "
            "If provenance_agent is available, consult it before choosing among tree construction tools. "
            "When consulting provenance_agent, pass these exact available tool names: fasttree_constructor, iqtree_constructor and raxml_constructor. "
            "Use provenance_agent only as advice for choosing a tool; you still must execute one tree construction MCP tool. "
            "You will receive a path containing alignment files. "
            "Use exactly one tree construction tool unless it fails; if it fails, try a different tree construction tool. "
            "Return the path where the tree results are stored. "
            "Do not attempt to generate trees without valid alignment input. "
            "Do not create new directories. Only use paths provided as input or returned by tools. "
        ),
    )
