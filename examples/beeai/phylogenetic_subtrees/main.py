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

from examples.beeai.phylogenetic_subtrees.agents.msa_agent import create_msa_agent
from examples.beeai.phylogenetic_subtrees.agents.orchestrator_agent import create_orchestrator_agent
from examples.beeai.phylogenetic_subtrees.agents.subtree_agent import create_subtree_agent
from examples.beeai.phylogenetic_subtrees.agents.tree_agent import create_tree_agent
from examples.beeai.phylogenetic_subtrees.agents.validation_agent import create_validation_agent
from anchor.telemetry.collector import InMemorySpanCollector
from anchor.observability.beeai import setup_observability


load_dotenv()


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "examples.commons.phylogenetic_subtrees.mcp.server"]
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
    validation_agent = create_validation_agent([t for t in mcp_tools if t.name == "sequence_validator" or t.name == "invalid_sequence_corrector"])
    msa_agent = create_msa_agent([t for t in mcp_tools if t.name == "multiple_sequence_alignment"])
    tree_agent = create_tree_agent([t for t in mcp_tools if t.name == "tree_constructor"])
    subtree_agent = create_subtree_agent([t for t in mcp_tools if t.name == "identify_frequent_subtrees"])

    tools = [
        HandoffTool(validation_agent, name="validation_agent"),
        HandoffTool(msa_agent, name="msa_agent"),
        HandoffTool(tree_agent, name="tree_agent"),
        HandoffTool(subtree_agent, name="subtree_agent"),
    ]
    orchestrator_agent = create_orchestrator_agent(tools)


    example_dir = Path(__file__).resolve().parent
    input_path = os.getenv("INPUT_PATH") or str(example_dir.parents[2] / "commons" / "phylogenetic_subtrees" / "data" / "input" / "testset")
    included_list = [
        Tool, 
        # BaseAgent, 
        # Requirement, 
        # ChatModel
    ]

    response = await orchestrator_agent.run(
        (
            f"Find the phylogenetic subtrees in the FASTA files available in the '{input_path}'."
        )  
    ).middleware(GlobalTrajectoryMiddleware(included=included_list))

    print('\n\n ----> Final Response')
    print(response.last_message.text)

if __name__ == "__main__":
    asyncio.run(main())
