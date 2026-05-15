# Synthetic Tool Selection Use Case

This use case is a controlled synthetic benchmark for validating Anchor Sailor, Anchor's provenance reuse layer.

It does not model a real business or scientific domain. Instead, it creates a small workflow where several tools can perform the same kind of task, but each tool has a different simulated reliability and runtime profile. This makes it useful for demonstrating how historical provenance can help an agent choose better tools in future executions.

## Goal

The goal is to generate provenance for repeated workflow executions where:

- each workflow stage has multiple candidate tools;
- tools are interchangeable within the same stage;
- some tools are fast but unreliable;
- some tools are slower but more reliable;
- failures and durations are recorded by Anchor;
- Sailor can later query SQLite provenance and recommend better choices.

The main question this use case helps answer is:

> Given several tools that can serve the same purpose, can prior provenance help the next workflow execution choose a better one?

## Workflow Shape

The synthetic workflow has three ordered stages:

```text
cleaning -> feature extraction -> scoring
```

These stages form one complete workflow.

The output path produced by each stage becomes the input path for the next stage:

```text
input cases
  -> cleaning output
  -> feature extraction output
  -> scoring output
```

## Why These Stages?

The stages are intentionally generic:

- `cleaning` simulates preparing or normalizing raw input records.
- `feature extraction` simulates turning cleaned data into an intermediate representation.
- `scoring` simulates producing a final evaluation/result.

The actual content is not important. What matters is that each stage has multiple tools with the same purpose and different operational behavior.

## Tool Sets

### Cleaning Tools

These tools all perform the cleaning stage:

```text
fast_cleaner
balanced_cleaner
strict_cleaner
```

Their intended behavior:

| Tool | Runtime | Reliability | Purpose |
| --- | --- | --- | --- |
| `fast_cleaner` | Fast | Lower | A quick cleaner that may leave problems behind or fail more often. |
| `balanced_cleaner` | Medium | Medium-high | A middle-ground cleaner. |
| `strict_cleaner` | Slowest | Highest | A stricter and more reliable cleaner. |

### Feature Extraction Tools

These tools all perform the feature extraction stage:

```text
quick_feature_extractor
robust_feature_extractor
experimental_feature_extractor
```

Their intended behavior:

| Tool | Runtime | Reliability | Purpose |
| --- | --- | --- | --- |
| `quick_feature_extractor` | Fast | Medium-low | Produces features quickly, with more risk. |
| `robust_feature_extractor` | Slower | High | Produces features more reliably. |
| `experimental_feature_extractor` | Fast-medium | Low | Represents an unstable experimental implementation. |

### Scoring Tools

These tools all perform the scoring stage:

```text
fast_scorer
accurate_scorer
unstable_scorer
```

Their intended behavior:

| Tool | Runtime | Reliability | Purpose |
| --- | --- | --- | --- |
| `fast_scorer` | Fast | Medium | Scores quickly, with moderate reliability. |
| `accurate_scorer` | Slowest | High | Produces the most reliable score. |
| `unstable_scorer` | Very fast | Low | Represents a very unstable scorer. |

## Simulated Tool Profiles

The tool behavior is configured in:

```text
examples/commons/synthetic_tool_selection/config.py
```

Each tool has a profile with:

- `stage`: the workflow stage it belongs to;
- `success_rate`: probability of completing successfully;
- `min_duration`: minimum simulated runtime;
- `max_duration`: maximum simulated runtime;
- `quality`: synthetic quality score written into successful outputs;
- `failure_modes`: possible synthetic failure labels.

Example:

```python
ToolProfile(
    name="strict_cleaner",
    stage="cleaning",
    success_rate=0.97,
    min_duration=0.25,
    max_duration=0.35,
    quality=0.95,
    failure_modes=("overly_strict_validation",),
)
```

The simulator uses these values to decide whether a call succeeds or fails and how long it should take.

## Reproducibility

The simulator is probabilistic, but deterministic for a given seed and call sequence.

Use:

```bash
export SYNTHETIC_SEED=42
```

The simulator combines the seed with:

- tool name;
- invocation count for that tool;
- input path.

That makes repeated runs reproducible while still allowing different tools and attempts to behave differently.

You can also scale simulated sleep time:

```bash
export SYNTHETIC_TIME_SCALE=1.0
```

The default is `1.0`, so the process really sleeps while a synthetic tool is executing. This is intentional: Anchor should observe different task durations even though the workload is synthetic.

For faster local testing:

```bash
export SYNTHETIC_TIME_SCALE=0
```

## Files And Directories

```text
examples/commons/synthetic_tool_selection/
  config.py                  Tool profiles and stage-to-tool mapping
  simulator.py               Deterministic probabilistic simulator
  data/
    input/
      cases.json             Small synthetic input dataset
    output/                  Tool outputs are written here by default
  mcp/
    server.py                FastMCP server exposing the synthetic tools
```

The default input file is:

```text
examples/commons/synthetic_tool_selection/data/input/cases.json
```

The default output directory is:

```text
examples/commons/synthetic_tool_selection/data/output
```

You can override the output directory with:

```bash
export OUTPUT_PATH=/path/to/output
```

## MCP Implementation

The MCP server is implemented in:

```text
examples/commons/synthetic_tool_selection/mcp/server.py
```

It exposes each synthetic tool as a separate MCP tool.

For example:

```python
@mcp.tool(
    name="fast_cleaner",
    description="Fast data cleaning tool. Same purpose as other cleaners; quicker but more failure-prone.",
)
def fast_cleaner(input_path: str = default_input_path()) -> str:
    return run_synthetic_tool("fast_cleaner", input_path)
```

All MCP tools call the same simulator entry point:

```python
run_synthetic_tool(tool_name, input_path)
```

The simulator then:

1. loads the configured tool profile;
2. updates a small local invocation-count state file;
3. computes a deterministic random outcome from the seed;
4. sleeps for the simulated runtime;
5. writes a JSON output file on success;
6. writes failure metadata and raises an error on failure.

## Output Files

Successful calls produce JSON files such as:

```text
data/output/cleaning/001_fast_cleaner.json
data/output/feature_extraction/001_robust_feature_extractor.json
data/output/scoring/001_accurate_scorer.json
```

The numeric prefix is the invocation count for that specific tool. For example, `003_fast_cleaner.json` means the `fast_cleaner` tool was actually called for the third time. It is not a workflow run number.

Each output includes metadata such as:

- tool name;
- stage;
- call count;
- seed;
- input path;
- simulated duration;
- configured success rate;
- synthetic quality;
- status.

Failed calls write failure metadata and then raise an exception. Anchor captures that failure through the BeeAI/OpenInference instrumentation.

## Agentic Workflow Consumer

The BeeAI consumer lives outside this common package:

```text
examples/beeai/synthetic_tool_selection/
```

It uses the MCP tools from this directory but keeps the agent implementation separate from the common tool implementation.

The BeeAI workflow has:

```text
cleaning_agent
extraction_agent
scoring_agent
provenance_agent
```

The example `main.py` gives a high-level goal to the BeeAI orchestrator instead of hard-coding the stage order in Python. The orchestrator must plan from:

- the user's high-level goal;
- the available specialist agents;
- each specialist's role and handoff description;
- provenance advice returned by Sailor.

The external Python runner only validates the final answer:

1. extract the final JSON path returned by the orchestrator;
2. verify that the file exists;
3. verify that the final path belongs to the `scoring` stage.

This keeps the workflow agentic while preventing silent success when the LLM invents a path.

The desired behavior is:

1. the orchestrator receives a goal such as "produce a final synthetic score from this input dataset";
2. it consults `provenance_agent` when historical evidence may help;
3. it delegates concrete tasks to specialist agents;
4. specialist agents call MCP tools and return real output paths;
5. the orchestrator returns the final scoring JSON path.

### Stage Agents

Each stage agent receives only the tools for its own stage:

```text
cleaning_agent:
  fast_cleaner
  balanced_cleaner
  strict_cleaner

extraction_agent:
  quick_feature_extractor
  robust_feature_extractor
  experimental_feature_extractor

scoring_agent:
  fast_scorer
  accurate_scorer
  unstable_scorer
```

Each stage agent is instructed to call one MCP tool for its stage and return the path created by that tool.

The implementation also includes a requirement that prevents the stage agent from returning a final answer before it has successfully called one stage MCP tool. This is important because an LLM may otherwise invent a plausible output path without actually running the tool.

### Workflow Orchestration

The orchestration coordinates the full workflow:

```text
cleaning -> feature extraction -> scoring
```

Before running each stage agent, it consults the Sailor provenance agent:

```text
provenance_agent
```

The provenance agent queries Anchor's SQLite provenance database and returns historical evidence about candidate tools, such as:

- invocation count;
- success count;
- failure count;
- failure rate;
- average duration;
- recent failures;
- recommendation text.

Sailor ignores internal framework tools such as BeeAI's `think`, `final_answer`, `HandoffTool` agent calls, and Sailor's own query tools by default. This keeps provenance reuse focused on domain tools like `fast_cleaner`, `robust_feature_extractor`, and `accurate_scorer`.

The recommendation is passed as context to the stage agent through the orchestrator's handoff task. The stage agent still has to call one of its MCP tools and produce a real output file.

## Provenance Reuse Flow

The intended validation loop is:

1. Run the synthetic BeeAI workflow several times.
2. Anchor captures provenance into TinyDB.
3. Export TinyDB to SQLite.
4. Sailor queries SQLite.
5. The provenance agent recommends tools based on prior executions.
6. Later workflow executions can use those recommendations.

In commands:

```bash
export SYNTHETIC_SEED=42
export SYNTHETIC_TIME_SCALE=1.0
export ANCHOR_OUTPUT_PATH=.anchor

uv run python -m examples.beeai.synthetic_tool_selection.main
uv run python -m examples.beeai.synthetic_tool_selection.main
uv run python -m examples.beeai.synthetic_tool_selection.main

uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

Then query Sailor directly:

```bash
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['fast_cleaner', 'balanced_cleaner', 'strict_cleaner']))"
```

## Important Notes

The SQLite export currently recreates the SQLite file from the TinyDB JSON file. Therefore, repeated workflow executions should accumulate in:

```text
.anchor/workflow_db.json
```

Then, after enough executions, export once:

```bash
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

The resulting SQLite database is:

```text
.anchor/workflow_db.sqlite
```

Sailor reads from SQLite, not TinyDB.

## What This Use Case Demonstrates

This use case demonstrates operational provenance reuse:

- Which equivalent tool has failed less often?
- Which one tends to run faster?
- Which one has enough historical evidence to be trusted?
- What should a workflow agent choose next based on prior executions?

It intentionally does not evaluate semantic quality beyond the synthetic `quality` field. The first goal is tool choice optimization from execution history.
