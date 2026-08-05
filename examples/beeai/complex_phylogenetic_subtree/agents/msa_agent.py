from typing import List
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.agents.base import BaseAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement

from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM
from examples.beeai.complex_phylogenetic_subtree.agents.requirements import require_stage_tool_before_final_answer


def create_msa_agent(mcp_tools: List[MCPTool], llm=None) -> BaseAgent:
    if not llm:
        llm = OLLAMA_LLM
    
    # mcp_tools.append(ThinkTool())

    return RequirementAgent(
        llm=llm,
        tools=mcp_tools,
        requirements=[
            # require_stage_tool_before_final_answer(
            #     [
            #         "multiple_sequence_alignment",
            #         "mafft_sequence_alignment",
            #         "muscle_sequence_alignment",
            #         "clustalw_sequence_alignment",
            #     ]
            # ),
            # ConditionalRequirement(ThinkTool, force_at_step=1, consecutive_allowed=False),
        ],
        name="msa_agent",
        role="multiple sequence alignment specialist",
        instructions=(
            "You are responsible for performing multiple sequence alignment (MSA) on validated FASTA files. "
            "Use exactly one alignment tool unless it fails; if it fails, try a different alignment tool. "
            "You have multiple tools with the same purpose: mafft_sequence_alignment, muscle_sequence_alignment and clustalw_sequence_alignment. Choose one tool. "
            # "If the selected tool succeeds, do not call another tool with the same objective; stop and return the "
            # "response. If the selected tool fails with an execution error, try another tool "
            "When consulting provenance_agent, pass these exact available tool names: mafft_sequence_alignment, muscle_sequence_alignment, clustalw_sequence_alignment. "
            "If provenance_agent is available, consult it before choosing among alignment tools. "
            "Use provenance_agent only as advice for choosing a tool; you still must execute one alignment MCP tool. "
            "You will receive a path containing validated sequences. "
            "Use exactly one alignment tool unless it fails; if it fails, try a different alignment tool. "
            "You must ensure that the output path is explicitly provided; if not, ask the user for it. "
            "Do not assume or create output directories. "
            "Return the path where alignment results were saved. "
            "Do not proceed if the input sequences are not confirmed as valid. "
        ),
    )
