

<div align="center">
  <p>
    <img src="assets/img/anchor.png" alt="Anchor logo" width="300">
  </p>
  <br>
  <h3>ANalysis of agentiC workflows via HistOry and pRovenance</h3>
</div>



## Overview

Anchor is a framework for capturing and analyzing provenance in agentic workflows using an interaction-centric model.

The project focuses on representing how agents, tools, users, model calls, delegations, and intentions interact over time. This makes agentic workflows easier to trace, reproduce, audit, and study.

## Repository Layout

```text
src/anchor/
  model/                Interaction-centric provenance model
  observability/        BeeAI/OpenInference instrumentation helpers
  telemetry/            Span collection, translation, schema, and persistence
  prov/                 PROV document and graph generation
  sailor/               SQLite provenance reuse queries and agent adapters

examples/
  beeai/phylogenetic_subtrees/      BeeAI-specific bioinformatics case study
  beeai/synthetic_tool_selection/   BeeAI consumer for Sailor validation
  commons/phylogenetic_subtrees/    Shared MCP tools and data for the case study
  commons/synthetic_tool_selection/ Shared synthetic MCP tools and simulator

docs/                   Architecture and provenance model notes
assets/                 Images and diagrams
tests/                  Test suite placeholder
```

## Install

Anchor uses `pyproject.toml` and can be installed with `uv`.

Start from the repository root:

```bash
cd anchor
```

Install `uv` and the external system dependencies used by the BeeAI phylogenetic subtrees example:

```bash
brew install uv
brew install mafft
brew install ollama
```

Then create a local Python environment and install Anchor with the BeeAI example dependencies:

```bash
export UV_PROJECT_ENVIRONMENT=venv
uv venv --python 3.12 venv
source venv/bin/activate
uv sync --extra beeai
```

Anchor uses a `src/` package layout. Use a non-hidden virtual environment directory such as `venv`, not `.venv`, because some Python/uv combinations skip `.pth` files inside hidden environment paths. If that happens, imports such as `import anchor` will fail even though the project is installed.

If `uv sync --extra beeai` does not install the editable project in your local setup, use:

```bash
uv pip install -e ".[beeai]"
```

## BeeAI Case Study

The BeeAI phylogenetic subtrees workflow is intentionally kept as an example, not as part of Anchor's core package. It demonstrates how Anchor can instrument a multi-agent workflow that validates FASTA files, runs multiple sequence alignment, builds phylogenetic trees, and identifies frequent subtrees.

### 1. Configure Environment Variables

```bash
cp .env.example .env
```

The default `.env` points to the bundled sample data:

```env
INPUT_PATH=examples/commons/phylogenetic_subtrees/data/input/testset
OUTPUT_PATH=examples/commons/phylogenetic_subtrees/data/output
ANCHOR_OUTPUT_PATH=.anchor
ANCHOR_PERSISTENCE_BACKEND=sqlite
```

`ANCHOR_OUTPUT_PATH` controls where Anchor writes its own provenance outputs. The default is `.anchor`.

`ANCHOR_PERSISTENCE_BACKEND` controls telemetry persistence. The default is `sqlite`, which writes directly to `.anchor/workflow_db.sqlite`. Use `tinydb` only when you want the legacy TinyDB capture path. Both backends use the same Anchor persistence interface.

### 2. Configure Ollama

The BeeAI example currently uses the model configured in:

```text
examples/beeai/phylogenetic_subtrees/constants.py
```

By default:

```python
OLLAMA_LLM = "ollama:granite3.3:8b"
```

Start Ollama in one terminal:

```bash
ollama serve
```

In another terminal, pull the model:

```bash
ollama pull granite3.3:8b
```

### 3. Run The Example

From the repository root:

```bash
uv run python -m examples.beeai.phylogenetic_subtrees.main
```

You can also use the example runner:

```bash
uv run ./examples/beeai/phylogenetic_subtrees/run.sh
```

The runner removes previous example outputs and then starts the workflow.

### 4. Expected Outputs

After a successful run, Anchor and the example should create:

```text
.anchor/workflow_db.sqlite
examples/commons/phylogenetic_subtrees/data/output/validated-files/
examples/commons/phylogenetic_subtrees/data/output/align/
examples/commons/phylogenetic_subtrees/data/output/frequent-subtrees.json
```

Anchor stores captured workflow data under `.anchor/workflow_db.sqlite` by default.

If you change `ANCHOR_OUTPUT_PATH`, replace `.anchor` in the paths above with your configured directory.

## Persistence Backend

Anchor has two implemented persistence adapters:

```text
sqlite   Default backend. Writes directly to workflow_db.sqlite.
tinydb   Legacy backend. Writes to workflow_db.json and can be exported to SQLite.
```

The active backend is selected with:

```bash
export ANCHOR_PERSISTENCE_BACKEND=sqlite
```

or:

```bash
export ANCHOR_PERSISTENCE_BACKEND=tinydb
```

Both adapters expose the same interface to the telemetry collector:

```python
workflow_def_table
workflow_exec_table
capability_table
entity_table
intention_table
task_exec_table
interaction_table

serialize(model)
save(table, model)
update(table, model, id_field)
get_by_id(table, field_name, value)
```

### SQLite Backend

SQLite is the default:

```bash
export ANCHOR_PERSISTENCE_BACKEND=sqlite
```

Expected database:

```text
.anchor/workflow_db.sqlite
```

The SQLite backend creates the schema if needed and preserves existing tables:

```text
create_schema(drop_existing=False)
```

Across multiple workflow executions, Anchor appends new provenance records to the same SQLite database. If a record with the same provenance id appears again, it is updated with `INSERT ... ON CONFLICT DO UPDATE`.

Use SQLite when you want Sailor to query provenance directly with no export step.

### TinyDB Backend

TinyDB is still available as a configurable legacy backend:

```bash
export ANCHOR_PERSISTENCE_BACKEND=tinydb
```

Expected database:

```text
.anchor/workflow_db.json
```

Across multiple workflow executions, TinyDB also accumulates provenance unless the JSON file is deleted by a script or manually removed.

Use TinyDB when you want to keep the older capture format. To export TinyDB to SQLite for Sailor:

```bash
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

The export recreates the SQLite database from the current TinyDB JSON contents:

```text
.anchor/workflow_db.json -> .anchor/workflow_db.sqlite
```

So with TinyDB, run workflows multiple times first, then export when you want a SQLite snapshot.

To inspect the SQLite database visually, you can install DB Browser for SQLite:

```bash
brew install db-browser-for-sqlite
```

## Reuse Provenance With Sailor

Sailor is Anchor's provenance reuse layer. It reads only Anchor's SQLite database and summarizes historical tool behavior so humans or workflow agents can make better execution choices. With the default SQLite backend, no export step is required before using Sailor. With the TinyDB backend, export TinyDB to SQLite before asking Sailor for recommendations.

By default, Sailor reads:

```text
${ANCHOR_OUTPUT_PATH:-.anchor}/workflow_db.sqlite
```

Sailor ignores internal framework tools by default, including BeeAI's `think`, `final_answer`, `HandoffTool` targets, agent calls, and Sailor's own query tools, so recommendations focus on domain tools. To add more ignored tool names:

```bash
export ANCHOR_SAILOR_IGNORED_TOOLS=debug_tool,internal_router
```

To ignore additional provenance target entity types:

```bash
export ANCHOR_SAILOR_IGNORED_ENTITY_TYPES=agent,router
```

Run direct provenance queries from Python:

```bash
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools())"
uv run python -c "from anchor.sailor import get_execution_recommendations; print(get_execution_recommendations())"
```

Sailor recommendation policy can be configured with:

```bash
export ANCHOR_SAILOR_POLICY=reliability
export ANCHOR_SAILOR_POLICY=speed
export ANCHOR_SAILOR_POLICY=speed_reliability
export ANCHOR_SAILOR_MAX_FAILURE_RATE=0.2
```

Useful query functions:

```python
from anchor.sailor import (
    compare_tools,
    get_execution_recommendations,
    get_tool_failures,
    get_tool_performance,
)
```

The BeeAI phylogenetic subtrees example also creates a Sailor provenance agent and gives it to the orchestrator as a `provenance_agent` handoff tool. The orchestrator can consult it before delegating workflow steps. If no SQLite history exists, Sailor reports that clearly and avoids inventing recommendations.

## Synthetic Tool Selection Example

The synthetic tool-selection workflow is a smaller BeeAI + MCP example designed to validate Sailor. It has one workflow with three ordered stages:

```text
cleaning -> feature extraction -> scoring
```

Each stage has multiple tools with the same purpose but different simulated success rates and runtimes. The simulator is probabilistic and reproducible with `SYNTHETIC_SEED`.

Run it several times to create provenance history:

```bash
export SYNTHETIC_SEED=42
export SYNTHETIC_TIME_SCALE=1.0
uv run python -m examples.beeai.synthetic_tool_selection.main
```

Then ask Sailor to compare equivalent tools:

```bash
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['fast_cleaner', 'balanced_cleaner', 'strict_cleaner']))"
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['quick_feature_extractor', 'robust_feature_extractor', 'experimental_feature_extractor']))"
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['fast_scorer', 'accurate_scorer', 'unstable_scorer']))"
```

Use `OUTPUT_PATH` to redirect synthetic workflow outputs and `ANCHOR_OUTPUT_PATH` to redirect Anchor provenance outputs.

## Generate PROV Artifacts

To convert the captured Anchor workflow database into PROV artifacts:

```bash
uv run python -m anchor.prov.mapper
```

Expected outputs:

```text
.anchor/prov.json
.anchor/workflow_prov.png
```

If PNG generation fails, install Graphviz:

```bash
brew install graphviz
```

## Full Local Run

This is the complete sequence for the BeeAI phylogenetic subtrees case study:

```bash
cd anchor

brew install uv
brew install mafft
brew install ollama

export UV_PROJECT_ENVIRONMENT=venv
uv venv --python 3.12 venv
source venv/bin/activate
uv sync --extra beeai
cp .env.example .env

ollama serve
```

Then, in another terminal:

```bash
cd anchor

export UV_PROJECT_ENVIRONMENT=venv
ollama pull granite3.3:8b

uv run python -m examples.beeai.phylogenetic_subtrees.main
uv run python -m anchor.prov.mapper
```

If you already had a `.venv` before changing the package layout, the fastest temporary workaround is:

```bash
PYTHONPATH=src uv run python -c "import anchor; print(anchor.__version__)"
PYTHONPATH=src uv run python -m anchor.prov.mapper
```

The cleaner fix is to recreate the environment with a non-hidden directory:

```bash
rm -rf .venv
export UV_PROJECT_ENVIRONMENT=venv
uv venv --python 3.12 venv
source venv/bin/activate
uv sync --extra beeai --reinstall-package anchor-agentic-provenance
```

## Status

Anchor is under active development. APIs and schemas may change while the project is being prepared for public release.
