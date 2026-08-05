from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.synthetic_phylogenetic_subtrees.constants import create_llm


def create_orchestrator_agent(tools, llm=None) -> BaseAgent:
    if not llm:
        llm = create_llm()

    tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=tools,
        requirements=[],
        final_answer_as_tool=False,
        name="orchestrator_agent",
        role="bioinformatics workflow coordinator",
         instructions=(
            "You are responsible for orchestrating a phylogenetic analysis workflow. "
            "Your job is to coordinate the execution of specialized agents in the correct order: "
            "validation -> alignment -> tree construction -> subtree analysis. "
            "Before delegating workflow steps, consult provenance_agent for historical evidence about "
            "available tools or agents when prior data exists. Use its recommendation only when it is "
            "supported by Anchor provenance; if it reports no relevant history, continue with the normal "
            "workflow order. "
            "You must ensure that each step receives the correct input path from the previous step. "
            "If any required path is missing, ask the user instead of generating one. "
            "Do not perform bioinformatics tasks yourself; delegate them to the appropriate agents. "
            "Ensure the workflow completes successfully and return the final result path. "
        ),
    )
