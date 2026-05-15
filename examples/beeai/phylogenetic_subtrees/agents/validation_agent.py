from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.phylogenetic_subtrees.constants import OLLAMA_LLM

    
def create_validation_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False)],
        name="validation_agent",
        role="bioinformatics data validator",
        instructions=(
            "You are responsible for validating protein sequences in FASTA format. "
            "Your task is to ensure that all sequences in the provided path are valid. "
            "Use the available tools to validate the sequences. "
            "If invalid sequences are detected, you must correct them using the appropriate tool. "
            "Always return a valid path containing only corrected and validated FASTA files. "
            "Do not proceed unless the sequences are valid. "
            "Do not create unsolicited directories or subdirectories. "
            "Only use file paths explicitly provided by the user or returned by tools. "
            "If you need a path and none is provided, ask the user."
        ),
    )
