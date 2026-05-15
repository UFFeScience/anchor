from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
from beeai_framework.tools.think import ThinkTool

from examples.beeai.synthetic_tool_selection.constants import OLLAMA_LLM


def create_orchestrator_agent(tools, llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=tools,
        requirements=[ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False)],
        name="synthetic_orchestrator_agent",
        role="synthetic benchmark workflow planner",
        instructions=(
            "You receive a high-level workflow goal and must plan how to complete it using the available specialist "
            "agents. Infer the necessary task sequence from the goal, the available specialists, and the data "
            "dependencies described by their roles. "
            "Use provenance_agent to look for historical evidence, similar prior workflows, useful next tasks, "
            "or tool-choice recommendations before choosing among equivalent tools. Use those recommendations only "
            "when they include evidence from Anchor provenance; if no relevant history exists, continue planning from "
            "the current goal and specialist capabilities. "
            "Delegate concrete work to the specialist agents and pass the exact output path from one completed task "
            "as the input path for any later task that needs it. "
            "Do not perform synthetic processing yourself. Do not invent paths. Return only the final JSON output path "
            "created by a specialist tool in this run."
        ),
    )
