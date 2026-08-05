# Synthetic Phylogenetic Subtrees BeeAI Experiment

This example is a controlled experimental version of the phylogenetic subtrees workflow.

It keeps the same broad workflow:

```text
validation -> alignment -> tree construction -> subtree analysis
```

but each specialist agent receives multiple realistic tool alternatives. The MCP tool descriptions are written as if the tools are real bioinformatics tools. The implementation is controlled: some tools call the existing local implementation, some are wrappers over the existing implementation, and some fail deterministically. The agent only discovers failures by trying the tools.

## Why This Example Exists

This use case is meant to evaluate whether Anchor Sailor can improve tool choice from provenance.

Suggested experimental conditions:

```text
baseline                  50 runs without Sailor
sailor_speed              50 runs with Sailor optimizing speed
sailor_speed_reliability  50 runs with Sailor optimizing speed and reliability
```

Each condition should use its own SQLite database:

```text
.anchor/experiments/baseline/workflow_db.sqlite
.anchor/experiments/sailor_speed/workflow_db.sqlite
.anchor/experiments/sailor_speed_reliability/workflow_db.sqlite
```

## Run One Workflow

```bash
export ANCHOR_PERSISTENCE_BACKEND=sqlite
export ANCHOR_OUTPUT_PATH=.anchor/experiments/dev
export ANCHOR_SAILOR_ENABLED=true
export ANCHOR_SAILOR_POLICY=speed_reliability

uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.main
```

Disable Sailor:

```bash
export ANCHOR_SAILOR_ENABLED=false
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.main
```

## Run Experiments

Baseline:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition baseline \
  --runs 50 \
  --anchor-output-path .anchor/experiments/baseline \
  --sailor-policy none
```

Sailor speed:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed \
  --sailor-policy speed
```

Sailor speed + reliability:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed_reliability \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed_reliability \
  --sailor-policy speed_reliability
```

To seed a Sailor condition with a baseline database snapshot:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed \
  --sailor-policy speed \
  --seed-sqlite-from .anchor/experiments/baseline/workflow_db.sqlite
```

## Outputs

Each experiment directory contains:

```text
workflow_db.sqlite
experiment_config.json
experiment_runs.jsonl
experiment_summary.json
```

`workflow_db.sqlite` is Anchor provenance.

`experiment_runs.jsonl` and `experiment_summary.json` are generated after all runs by reading the SQLite database.

## Sailor Policies

```text
reliability         lower failure rate first, then lower duration
speed               lower duration first, then lower failure rate
speed_reliability   prefer tools below ANCHOR_SAILOR_MAX_FAILURE_RATE, then lower duration
```

The default threshold for `speed_reliability` is:

```bash
export ANCHOR_SAILOR_MAX_FAILURE_RATE=0.2
```

