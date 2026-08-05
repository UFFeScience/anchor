from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM
from examples.beeai.complex_phylogenetic_subtree.agents.requirements import require_stage_tool_before_final_answer


def create_subtree_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    # mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            # require_stage_tool_before_final_answer(
            #     [
            #         "identify_frequent_subtrees, dendropy_identify_frequent_subtrees, ete_identify_frequent_subtrees, treepattern_identify_frequent_subtrees",
            #     ]
            # ),
            # ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False),
        ],
        name="subtree_agent",
        role="phylogenetic pattern analyst",
        instructions=(
            "You are responsible for analyzing phylogenetic tree ensembles and identifying frequent subtrees. "
            "You have one tools with to achieve your purpose: dendropy_identify_frequent_subtrees."
            "You will receive a path containing previously generated phylogenetic trees. "
            "Return the path containing the analysis results. "
            "Do not proceed if tree data is not available. "
            "Do not create directories or assume paths. Only use paths provided or returned by tools. "
        ),
    )
