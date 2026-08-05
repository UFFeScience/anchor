import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from mcp import StdioServerParameters, stdio_client

from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware
from beeai_framework.tools import Tool
from beeai_framework.tools.mcp import MCPTool
from beeai_framework.tools.handoff import HandoffTool

from anchor.sailor.beeai import create_provenance_agent
from examples.beeai.complex_phylogenetic_subtree.constants import OLLAMA_LLM
from examples.beeai.complex_phylogenetic_subtree.agents.msa_agent import create_msa_agent
from examples.beeai.complex_phylogenetic_subtree.agents.orchestrator_agent import create_orchestrator_agent
from examples.beeai.complex_phylogenetic_subtree.agents.subtree_agent import create_subtree_agent
from examples.beeai.complex_phylogenetic_subtree.agents.tree_agent import create_tree_agent
from examples.beeai.complex_phylogenetic_subtree.agents.validation_agent import create_validation_agent
from anchor.telemetry.collector import InMemorySpanCollector
from anchor.observability.beeai import setup_observability


load_dotenv()


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "examples.commons.complex_phylogenetic_subtree.mcp.server"]
)


SPAN_COLLECTOR = InMemorySpanCollector()
setup_observability(span_collector=SPAN_COLLECTOR)


def tool_specs(tools):
    return {
        t.name: {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema
        }
        for t in tools
    }

async def main():
    client = stdio_client(SERVER_PARAMS)
    mcp_tools = await MCPTool.from_client(client)
    validation_tool_names = {
        "sequence_validator",
        # "seqkit_sequence_validator",
        # "emboss_sequence_validator",
        "invalid_sequence_corrector",
        # "fast_invalid_sequence_corrector",
        # "emboss_invalid_sequence_corrector",
    }
    msa_tool_names = {
        # "multiple_sequence_alignment",
        "mafft_sequence_alignment",
        "muscle_sequence_alignment",
        "clustalw_sequence_alignment",
    }
    tree_tool_names = {
        # "tree_constructor",
        "fasttree_constructor",
        "iqtree_constructor",
        "raxml_constructor",
    }
    subtree_tool_names = {
        # "identify_frequent_subtrees",
        "dendropy_identify_frequent_subtrees",
        # "ete_identify_frequent_subtrees",
        # "treepattern_identify_frequent_subtrees",
    }

    sailor_enabled = os.getenv("ANCHOR_SAILOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    provenance_handoff = None
    if sailor_enabled:
        provenance_handoff = HandoffTool(
            create_provenance_agent(llm=OLLAMA_LLM),
            name="provenance_agent",
            description=(
                "Ask Anchor Sailor for provenance evidence before choosing among tools for the current specialist task."
                "YOU MUST inform the correct name of available tools for the provenance agent!!!"
            ),
        )

    def stage_tools(tool_names):
        tools = [t for t in mcp_tools if t.name in tool_names]
        if provenance_handoff is not None:
            tools.append(provenance_handoff)
        return tools

    validation_agent = create_validation_agent(stage_tools(validation_tool_names)[:-1])
    msa_agent = create_msa_agent(stage_tools(msa_tool_names))
    tree_agent = create_tree_agent(stage_tools(tree_tool_names))
    subtree_agent = create_subtree_agent(stage_tools(subtree_tool_names)[:-1])

    tools = [
        HandoffTool(validation_agent, name="validation_agent"),
        HandoffTool(msa_agent, name="msa_agent"),
        HandoffTool(tree_agent, name="tree_agent"),
        HandoffTool(subtree_agent, name="subtree_agent"),
    ]
    orchestrator_agent = create_orchestrator_agent(tools)


    example_dir = Path(__file__).resolve().parent
    input_path = os.getenv("INPUT_PATH") or str(
        example_dir.parents[1] / "commons" / "complex_phylogenetic_subtree" / "data" / "input" / "testset"
    )
    included_list = [
        Tool, 
        # BaseAgent, 
        # Requirement, 
        # ChatModel
    ]

    response = await orchestrator_agent.run(
        (
            "Find the phylogenetic subtrees in the FASTA files available at this exact input path: "
            f"{input_path}. Use this path exactly as provided; do not rewrite, shorten, or infer another path."
        )  
    ).middleware(GlobalTrajectoryMiddleware(included=included_list))

    print('\n\n ----> Final Response')
    print(response.last_message.text)

if __name__ == "__main__":
    asyncio.run(main())
