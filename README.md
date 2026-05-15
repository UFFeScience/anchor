

<div style="text-align: center;">
  <img src="assets/img/anchor.png" alt="Anchor logo" width="300">
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

examples/
  beeai/phylogenetic_subtrees/      BeeAI-specific bioinformatics case study
  commons/phylogenetic_subtrees/    Shared MCP tools and data for the case study

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
```

`ANCHOR_OUTPUT_PATH` controls where Anchor writes its own provenance outputs. The default is `.anchor`.

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
.anchor/workflow_db.json
examples/commons/phylogenetic_subtrees/data/output/validated-files/
examples/commons/phylogenetic_subtrees/data/output/align/
examples/commons/phylogenetic_subtrees/data/output/frequent-subtrees.json
```

Anchor stores captured workflow data under `.anchor/workflow_db.json`.

If you change `ANCHOR_OUTPUT_PATH`, replace `.anchor` in the paths above with your configured directory.

## Export TinyDB To SQLite

The current workflow persists to TinyDB first. To export that TinyDB database to SQLite:

```bash
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

Expected output:

```text
.anchor/workflow_db.sqlite
```

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
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
uv run python -m anchor.prov.mapper
```

If you already had a `.venv` before changing the package layout, the fastest temporary workaround is:

```bash
PYTHONPATH=src uv run python -c "import anchor; print(anchor.__version__)"
PYTHONPATH=src uv run python -m anchor.telemetry.persistence.tinydb_to_sql
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
