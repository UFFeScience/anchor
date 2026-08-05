from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM


def create_orchestrator_agent(tools, llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=tools,
        requirements=[ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False)],
        name="orchestrator_agent",
        role="bioinformatics workflow coordinator",
        instructions=(
            "You are responsible for orchestrating a phylogenetic analysis workflow. "
            "Your job is to coordinate the execution of specialized agents in the correct order: "
            "validation -> alignment -> tree construction -> subtree analysis. "
            "Do not choose concrete MCP tools yourself; each specialist chooses among its own tools. "
            "You must ensure that each step receives the correct input path from the previous step. "
            "If any required path is missing, ask the user instead of generating one. "
            "Do not perform bioinformatics tasks yourself; delegate them to the appropriate agents. "
            "Ensure the workflow completes successfully and return the final result path. "
        ),
    )
