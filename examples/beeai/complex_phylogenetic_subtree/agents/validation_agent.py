from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM
from examples.beeai.complex_phylogenetic_subtree.agents.requirements import require_stage_tool_before_final_answer

    
def create_validation_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM

    # mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            # require_stage_tool_before_final_answer(
            #     [
            #         "sequence_validator",
            #         "seqkit_sequence_validator",
            #         "emboss_sequence_validator",
            #         "invalid_sequence_corrector",
            #         "fast_invalid_sequence_corrector",
            #         "emboss_invalid_sequence_corrector",
            #     ]
            # ),
            # ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False),
        ],
        name="validation_agent",
        role="bioinformatics data validator",
        instructions=(
            "You are responsible for validating protein sequences in FASTA format. "
            "If provenance_agent is available, consult it before choosing among validation/correction tools. "
            "Use provenance_agent only as advice for choosing a tool; you still must execute one validation or correction MCP tool. "
            "Your task is to ensure that all sequences in the provided path are valid. "
            "Use the available tools to validate the sequences. "
            "Use exactly one validation tool first. If it fails, try a different validation tool. "
            "If invalid sequences are detected, correct them using one correction tool; if it fails, try a different correction tool. "
            "Always return a valid path containing only corrected and validated FASTA files. "
            "Do not proceed unless the sequences are valid. "
            "Do not create unsolicited directories or subdirectories. "
            "Only use file paths explicitly provided by the user or returned by tools. "
            "If you need a path and none is provided, ask the user."
        ),
    )
