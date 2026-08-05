from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.synthetic_phylogenetic_subtrees.constants import create_llm


def create_subtree_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = create_llm()

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[],
        final_answer_as_tool=False,
        name="subtree_agent",
        role="phylogenetic pattern analyst",
        instructions=(
            "You are responsible for analyzing phylogenetic tree ensembles and identifying frequent subtrees. "
            "You will receive a path containing previously generated phylogenetic trees. "
            "Use the available tool to extract frequent subtrees. "
            "Return the path containing the analysis results. "
            "Do not proceed if tree data is not available. "
            "Do not create directories or assume paths. Only use paths provided or returned by tools. "
            "Limit yourself to the task you received. "
            "If provenance_agent is available, consult it before choosing between alignment tools. "
            "If the selected tool succeeds, do not call another tool with the same objective; stop and return the "
            "alignment output path. If the selected tool fails with an execution error, try another alignment tool "
            "rather than stopping immediately. "
        ),
    )
