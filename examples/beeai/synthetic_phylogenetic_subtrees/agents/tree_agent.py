from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.synthetic_phylogenetic_subtrees.constants import create_llm


def create_tree_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = create_llm()

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[],
        final_answer_as_tool=False,
        name="tree_agent",
        role="phylogenetic inference specialist",
        instructions=(
            "You are responsible for constructing phylogenetic trees from multiple sequence alignment results. "
            "You will receive a path containing alignment files. "
            "Use the available tool to generate phylogenetic trees. "
            "Return the path where the tree results are stored. "
            "Do not attempt to generate trees without valid alignment input. "
            "Do not create new directories. Only use paths provided as input or returned by tools. "
            "Limit yourself to the task you received. "
            "If provenance_agent is available, consult it before choosing between alignment tools. "
            "If the selected tool succeeds, do not call another tool with the same objective; stop and return the "
            "alignment output path. If the selected tool fails with an execution error, try another alignment tool "
            "rather than stopping immediately. "
        ),
    )
