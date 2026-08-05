from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM


def create_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm=OLLAMA_LLM
    
    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False)],
        name="biologist",
        role="biologist",
        instructions=(
            "You are a biologist. Your task is to receive references to FASTA file sets (as a path) and perform all the necessary "
            "steps to construct phylogenetic trees and identify frequent subtrees in phylogenetic tree ensembles. Use the tools "
            "available to you. If you have any questions about any step, ask the user."
            "Analyze the list of available tools, as well as their inputs and outputs, when making your decisions."
            "Do not create unsolicited directories or subdirectories!!!"
            "Only use file paths explicitly provided by the user or returned by tools."
            "If you need a path and none is provided, do not generate one. Instead, ask the user for the exact path."
        ),
    )
    
