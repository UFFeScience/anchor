from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.phylogenetic_subtrees.constants import OLLAMA_LLM


def create_msa_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM
    
    mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[ConditionalRequirement(ThinkTool, force_after="Tool", consecutive_allowed=False)],
        name="msa_agent",
        role="multiple sequence alignment specialist",
        instructions=(
            "You are responsible for performing multiple sequence alignment (MSA) on validated FASTA files. "
            "You will receive a path containing validated sequences. "
            "Use the available tool to generate alignments. "
            "You must ensure that the output path is explicitly provided; if not, ask the user for it. "
            "Do not assume or create output directories. "
            "Return the path where alignment results were saved. "
            "Do not proceed if the input sequences are not confirmed as valid. "
        ),
    )
