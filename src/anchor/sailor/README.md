# Anchor Sailor

Sailor is Anchor's provenance reuse layer.

It reads prior workflow provenance from Anchor's SQLite database and turns that history into actionable guidance for humans or workflow agents. Its first use case is operational tool choice: when a workflow has multiple tools that can serve the same purpose, Sailor compares prior invocations, failures, durations, and recent outputs so the next execution can make a better choice.

Sailor is part of Anchor core. BeeAI is only one adapter.

## What Sailor Reads

Sailor reads SQLite only.

By default, it looks for:

```text
${ANCHOR_OUTPUT_PATH:-.anchor}/workflow_db.sqlite
```

That SQLite database is produced either by:

- exporting Anchor's TinyDB capture with `anchor.telemetry.persistence.tinydb_to_sql`; or
- writing directly through Anchor's SQLite persistence layer.

Sailor does not query TinyDB.

## Main Idea

Anchor captures provenance from agentic workflows:

- which agents ran;
- which tools were invoked;
- task status;
- inputs and outputs;
- timestamps;
- failures;
- workflow execution context.

Sailor queries that provenance and answers questions like:

- Which equivalent tool has been more reliable?
- Which tool has failed more often?
- Which tool tends to run faster?
- Is there enough historical evidence to recommend one option?
- What recent failures should the next workflow know about?

## How The Provenance Agent Uses SQL Results

The BeeAI provenance agent does not receive raw SQL rows directly.

The flow is:

```text
workflow agent or orchestrator
  -> asks provenance_agent for help
    -> provenance_agent calls a deterministic Sailor tool
      -> Sailor queries SQLite
      -> Sailor aggregates and summarizes matching provenance
    -> provenance_agent receives compact evidence
  -> workflow agent uses that answer as context
```

For example, a workflow agent may ask:

```text
For the cleaning task, compare fast_cleaner, balanced_cleaner, and strict_cleaner.
```

The provenance agent calls a Sailor tool such as:

```text
get_execution_recommendations
```

That tool queries SQLite for historical `tool_invocation` records matching those tool names. Sailor then computes deterministic summaries before returning anything to the LLM:

```python
{
    "tool_name": "strict_cleaner",
    "invocation_count": 8,
    "success_count": 8,
    "failure_count": 0,
    "failure_rate": 0.0,
    "average_duration_seconds": 0.31,
    "recent_failures": [],
    "recommendation_text": "strict_cleaner has 8 recorded invocation(s)..."
}
```

So the LLM sees compact evidence, not a raw dump of every database occurrence.

This separation matters:

- SQL retrieves the historical records.
- Python computes deterministic metrics and rankings.
- The LLM explains the evidence and communicates tradeoffs.
- The workflow agent uses that explanation to guide its next action.

In short:

```text
raw SQLite provenance
  -> deterministic Sailor query/aggregation
  -> compact evidence
  -> provenance_agent explanation
  -> workflow-agent decision support
```

## SQLite Tables Used

Sailor currently queries these Anchor tables:

```text
task_executions
interactions
entities
workflow_executions
```

The main signal is:

```text
interactions.type = "tool_invocation"
```

Sailor joins tool invocation interactions with related task execution records when available. That allows it to combine:

- tool identity from `entities`;
- task status from `task_executions`;
- timestamps from `task_executions`;
- input/output payloads from tasks and interactions.

## Public Query Functions

The framework-neutral API is available from:

```python
from anchor.sailor import (
    compare_tools,
    get_execution_recommendations,
    get_tool_failures,
    get_tool_performance,
)
```

### `get_tool_performance`

```python
get_tool_performance(
    sqlite_path=None,
    tool_names=None,
    purpose=None,
    ignored_tool_names=None,
    ignored_entity_types=None,
)
```

Returns historical performance summaries for matching tools.

The result includes:

- tool name;
- invocation count;
- success count;
- failure count;
- failure rate;
- average duration when timestamps exist;
- recent failure snippets;
- recent output snippets;
- recommendation text per tool.

Example:

```python
from anchor.sailor import get_tool_performance

result = get_tool_performance(
    tool_names=["fast_cleaner", "balanced_cleaner", "strict_cleaner"]
)
print(result)
```

### `get_tool_failures`

```python
get_tool_failures(
    sqlite_path=None,
    tool_names=None,
    limit=20,
    ignored_tool_names=None,
    ignored_entity_types=None,
)
```

Returns recent failed tool invocations.

The result includes:

- tool name;
- status;
- timestamp;
- interaction id;
- related task execution id;
- compact input snippet;
- compact output snippet;
- compact payload snippet.

Example:

```python
from anchor.sailor import get_tool_failures

failures = get_tool_failures(
    tool_names=["experimental_feature_extractor"],
    limit=5,
)
print(failures)
```

### `compare_tools`

```python
compare_tools(
    sqlite_path=None,
    tool_names=None,
    purpose=None,
    ignored_tool_names=None,
    ignored_entity_types=None,
)
```

Ranks matching tools using operational evidence.

Current ranking order:

1. lower failure rate;
2. lower average duration;
3. higher invocation count.

Returns:

- ranked tool summaries;
- recommended tool;
- recommendation text explaining the evidence.

Example:

```python
from anchor.sailor import compare_tools

comparison = compare_tools(
    tool_names=["fast_scorer", "accurate_scorer", "unstable_scorer"]
)
print(comparison["recommended_tool"])
print(comparison["recommendation"])
```

### `get_execution_recommendations`

```python
get_execution_recommendations(
    sqlite_path=None,
    available_tools=None,
    workflow_goal=None,
    ignored_tool_names=None,
    ignored_entity_types=None,
)
```

Returns recommendations for an upcoming workflow execution.

Use this when a workflow agent has a set of available tools and wants guidance before choosing one.

Example:

```python
from anchor.sailor import get_execution_recommendations

recommendations = get_execution_recommendations(
    available_tools=["quick_feature_extractor", "robust_feature_extractor"],
    workflow_goal="extract features from cleaned synthetic records",
)
print(recommendations)
```

If there is no SQLite database or no relevant history, Sailor returns a no-data response and does not invent recommendations.

## Output Shape

A successful comparison returns a compact dictionary like:

```python
{
    "sqlite_path": ".anchor/workflow_db.sqlite",
    "has_data": True,
    "tool_count": 2,
    "tools": [
        {
            "tool_name": "robust_feature_extractor",
            "invocation_count": 5,
            "success_count": 5,
            "failure_count": 0,
            "failure_rate": 0.0,
            "average_duration_seconds": 0.28,
            "recent_failures": [],
            "recent_outputs": [...],
            "recommendation_text": "..."
        }
    ],
    "recommended_tool": "robust_feature_extractor",
    "recommendation": "Prefer robust_feature_extractor based on ..."
}
```

A no-data response looks like:

```python
{
    "sqlite_path": ".anchor/workflow_db.sqlite",
    "has_data": False,
    "tool_count": 0,
    "tools": [],
    "message": "No matching tool invocation history was found."
}
```

## Internal Tool Filtering

Sailor is meant to recommend domain tools, not framework mechanics.

By default, it ignores:

- BeeAI internal tools:
  - `think`
  - `ThinkTool`
  - `final_answer`
  - `FinalAnswerTool`
- handoff/coordinator artifacts:
  - `handoff`
  - `HandoffTool`
  - names ending in `_agent`
  - `provenance_agent`
- Sailor's own query tools:
  - `get_tool_performance`
  - `get_tool_failures`
  - `compare_tools`
  - `get_execution_recommendations`
- provenance rows whose target entity type is `agent`.

This prevents recommendations such as "use final_answer" or "use provenance_agent" and keeps the ranking focused on workflow/domain tools.

### Extending The Ignore List

Add ignored tool names with:

```bash
export ANCHOR_SAILOR_IGNORED_TOOLS=debug_tool,internal_router
```

Add ignored entity types with:

```bash
export ANCHOR_SAILOR_IGNORED_ENTITY_TYPES=agent,router
```

You can also pass ignore lists directly:

```python
compare_tools(
    ignored_tool_names=["debug_tool"],
    ignored_entity_types=["router"],
)
```

## BeeAI Adapter

The BeeAI adapter lives in:

```text
anchor.sailor.beeai
```

Create a provenance agent:

```python
from anchor.sailor.beeai import create_provenance_agent

provenance_agent = create_provenance_agent()
```

Or pass a specific LLM/path:

```python
provenance_agent = create_provenance_agent(
    llm="ollama:granite3.3:8b",
    sqlite_path=".anchor/workflow_db.sqlite",
)
```

The adapter returns a BeeAI `RequirementAgent`.

It exposes deterministic Sailor query tools:

```text
get_tool_performance
get_tool_failures
compare_tools
get_execution_recommendations
```

The agent instructions require it to:

- answer with evidence from provenance;
- explain tradeoffs;
- recommend tool choices only from historical data;
- say clearly when no relevant history exists;
- avoid inventing recommendations.

## BeeAI Handoff Example

A BeeAI workflow can use Sailor as a handoff tool:

```python
from beeai_framework.tools.handoff import HandoffTool
from anchor.sailor.beeai import create_provenance_agent

provenance_agent = create_provenance_agent()

tools = [
    HandoffTool(provenance_agent, name="provenance_agent"),
    # other workflow tools or specialist agents
]
```

Then an orchestrator can ask:

```text
For the scoring task, compare fast_scorer, accurate_scorer, and unstable_scorer using prior Anchor provenance.
```

Sailor may answer:

```text
Prefer accurate_scorer based on 8 prior invocations, 8 successes, 0 failures,
and a 0% failure rate. It is slower than fast_scorer, but has stronger reliability evidence.
```

Or, if no history exists:

```text
No matching tool invocation history was found. I cannot recommend a tool from provenance yet.
```

## Running Against Local Provenance

Run a workflow several times so Anchor accumulates TinyDB provenance:

```bash
uv run python -m examples.beeai.synthetic_tool_selection.main
uv run python -m examples.beeai.synthetic_tool_selection.main
uv run python -m examples.beeai.synthetic_tool_selection.main
```

Export TinyDB to SQLite:

```bash
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

Query Sailor:

```bash
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['fast_cleaner', 'balanced_cleaner', 'strict_cleaner']))"
```

## Current Scope

Sailor currently optimizes operational execution:

- lower failure rate;
- faster runtime;
- stronger evidence from prior invocations;
- recent failure awareness.

Semantic quality scoring is intentionally out of scope until Anchor captures domain-specific evaluation signals in the provenance model.
