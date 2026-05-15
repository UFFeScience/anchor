import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import StdioServerParameters, stdio_client

from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware
from beeai_framework.tools import Tool
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.tools.mcp import MCPTool

from anchor.observability.beeai import setup_observability
from anchor.sailor.beeai import create_provenance_agent
from anchor.telemetry.collector import InMemorySpanCollector
from examples.beeai.synthetic_tool_selection.agents.cleaning_agent import create_cleaning_agent
from examples.beeai.synthetic_tool_selection.agents.extraction_agent import create_extraction_agent
from examples.beeai.synthetic_tool_selection.agents.orchestrator_agent import create_orchestrator_agent
from examples.beeai.synthetic_tool_selection.agents.scoring_agent import create_scoring_agent
from examples.commons.synthetic_tool_selection.config import STAGE_TOOLS
from examples.commons.synthetic_tool_selection.simulator import default_input_path


load_dotenv()


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "examples.commons.synthetic_tool_selection.mcp.server"],
)

SPAN_COLLECTOR = InMemorySpanCollector()
setup_observability(span_collector=SPAN_COLLECTOR)


def select_tools(mcp_tools, names):
    return [tool for tool in mcp_tools if tool.name in names]


def extract_existing_path(text: str) -> Path | None:
    candidates = re.findall(r"/[^\s\"']+\.json", text)
    for candidate in reversed(candidates):
        path = Path(candidate.rstrip(".,)"))
        if path.exists():
            return path
    return None


async def main():
    client = stdio_client(SERVER_PARAMS)
    mcp_tools = await MCPTool.from_client(client)

    cleaning_agent = create_cleaning_agent(select_tools(mcp_tools, STAGE_TOOLS["cleaning"]))
    extraction_agent = create_extraction_agent(select_tools(mcp_tools, STAGE_TOOLS["feature_extraction"]))
    scoring_agent = create_scoring_agent(select_tools(mcp_tools, STAGE_TOOLS["scoring"]))
    provenance_agent = create_provenance_agent()
    tools = [
        HandoffTool(
            provenance_agent,
            name="provenance_agent",
            description=(
                "Consult Anchor provenance for similar workflows, useful next tasks, historical tool performance, "
                "failures, durations, and evidence-based tool recommendations."
            ),
        ),
        HandoffTool(
            cleaning_agent,
            name="cleaning_agent",
            description=(
                "Specialist that prepares raw synthetic records and returns a JSON path produced by a cleaning tool."
            ),
        ),
        HandoffTool(
            extraction_agent,
            name="extraction_agent",
            description=(
                "Specialist that transforms a cleaned JSON path into feature data and returns a feature JSON path."
            ),
        ),
        HandoffTool(
            scoring_agent,
            name="scoring_agent",
            description=(
                "Specialist that scores a feature JSON path and returns the final scoring JSON path."
            ),
        ),
    ]
    orchestrator_agent = create_orchestrator_agent(tools)

    example_dir = Path(__file__).resolve().parent
    input_path = os.getenv("SYNTHETIC_INPUT_PATH") or default_input_path()
    output_path = os.getenv(
        "OUTPUT_PATH",
        str(example_dir.parents[1] / "commons" / "synthetic_tool_selection" / "data" / "output"),
    )
    included = [Tool]

    response = await orchestrator_agent.run(
        (
            "Produce a final synthetic score from the input dataset. "
            f"Input dataset path: {input_path}. "
            f"Output root for generated artifacts: {output_path}. "
            "Plan the workflow from this high-level goal. Use provenance when it can help choose reliable tools "
            "or identify useful next tasks from similar prior executions. Return only the final JSON output path."
        )
    ).middleware(GlobalTrajectoryMiddleware(included=included))

    final_path = extract_existing_path(response.last_message.text)
    if final_path is None:
        raise RuntimeError(
            "The orchestrator returned a JSON path that does not exist. "
            "A stage was probably skipped or a path was invented."
        )
    if "/scoring/" not in str(final_path):
        raise RuntimeError(f"The workflow did not return a scoring output path: {final_path}")

    print("\n\n ----> Final Response")
    print(f"Synthetic workflow completed successfully: {final_path}")


if __name__ == "__main__":
    asyncio.run(main())
