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
from examples.beeai.synthetic_phylogenetic_subtrees.constants import create_llm
from examples.beeai.synthetic_phylogenetic_subtrees.agents.msa_agent import create_msa_agent
from examples.beeai.synthetic_phylogenetic_subtrees.agents.orchestrator_agent import create_orchestrator_agent
from examples.beeai.synthetic_phylogenetic_subtrees.agents.subtree_agent import create_subtree_agent
from examples.beeai.synthetic_phylogenetic_subtrees.agents.tree_agent import create_tree_agent
from examples.beeai.synthetic_phylogenetic_subtrees.agents.validation_agent import create_validation_agent
from examples.commons.synthetic_phylogenetic_subtrees.tool_profiles import STAGE_TOOLS
from anchor.telemetry.collector import InMemorySpanCollector
from anchor.observability.beeai import setup_observability


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "examples.commons.synthetic_phylogenetic_subtrees.mcp.server"]
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
    sailor_enabled = os.getenv("ANCHOR_SAILOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    provenance_agent = (
        create_provenance_agent(llm=create_llm(os.getenv("ANCHOR_SAILOR_LLM") or None))
        if sailor_enabled
        else None
    )

    def stage_tools(stage: str):
        tools = [t for t in mcp_tools if t.name in STAGE_TOOLS[stage]]
        if provenance_agent is not None:
            tools.append(
                HandoffTool(
                    provenance_agent,
                    name="provenance_agent",
                    description=(
                        "Consult Anchor Sailor provenance before choosing between available tools for the current "
                        "specialized task. Use it only as advice for tool selection."
                    ),
                )
            )
        return tools

    validation_agent = create_validation_agent(stage_tools("validation"))
    msa_agent = create_msa_agent(stage_tools("alignment"))
    tree_agent = create_tree_agent(stage_tools("tree_construction"))
    subtree_agent = create_subtree_agent(stage_tools("subtree_analysis"))

    # tools = [
    #     HandoffTool(
    #         validation_agent,
    #         name="validation_agent",
    #         description=(
    #             "Validate or prepare the input protein FASTA directory. Input: a FASTA directory path. "
    #             "Output: path to the validated FASTA directory."
    #         ),
    #     ),
    #     HandoffTool(
    #         msa_agent,
    #         name="msa_agent",
    #         description=(
    #             "Run multiple sequence alignment on a validated FASTA directory. Input: validated FASTA directory "
    #             "path. Output: path to the alignment output directory."
    #         ),
    #     ),
    #     HandoffTool(
    #         tree_agent,
    #         name="tree_agent",
    #         description=(
    #             "Construct phylogenetic tree files from the alignment output directory. Input: alignment directory "
    #             "path. Output: path to the directory containing generated tree files. Do not request a specific "
    #             "output filename or format."
    #         ),
    #     ),
    #     HandoffTool(
    #         subtree_agent,
    #         name="subtree_agent",
    #         description=(
    #             "Extract frequent phylogenetic subtrees from a directory containing generated tree files. Input: tree "
    #             "output directory path. Output: path to the final frequent-subtrees result file."
    #         ),
    #     ),
    # ]
    # 
    tools = [
        HandoffTool(validation_agent, name="validation_agent"),
        HandoffTool(msa_agent, name="msa_agent"),
        HandoffTool(tree_agent, name="tree_agent"),
        HandoffTool(subtree_agent, name="subtree_agent"),
    ]
    orchestrator_agent = create_orchestrator_agent(tools)


    example_dir = Path(__file__).resolve().parent
    input_path = os.getenv("INPUT_PATH") or str(
        example_dir.parents[1]
        / "commons"
        / "synthetic_phylogenetic_subtrees"
        / "data"
        / "input"
        / "testset"
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
            f"{input_path}. Use this path as provided; do not rewrite, shorten, or infer another path."
        )
    ).middleware(GlobalTrajectoryMiddleware(included=included_list))

    print('\n\n ----> Final Response')
    print(response.last_message.text)

if __name__ == "__main__":
    asyncio.run(main())
