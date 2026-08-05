# Synthetic Phylogenetic Subtrees Experiment Instructions

This guide explains how to run the synthetic phylogenetic subtree experiments used to evaluate Anchor Sailor.

Assume every command is executed from the repository root:

```bash
cd /anchor
```

## 1. Experiment Goal

The experiment evaluates whether Sailor helps a workflow agent choose better tools from previous provenance.

The workflow goal is intentionally high level: given a protein FASTA dataset, produce a phylogenetic subtree analysis. The BeeAI orchestrator delegates to specialist agents. Each specialist has multiple realistic tool alternatives for the same purpose.

Sailor reads prior Anchor provenance from SQLite and recommends tools based on execution history.

## 2. Experimental Conditions

Use three separate SQLite databases:

```text
baseline                  no Sailor
sailor_speed              Sailor prefers faster tools
sailor_speed_reliability  Sailor prefers fast tools that stay below the failure-rate threshold
```

Recommended design:

```text
50 runs  baseline
50 runs  sailor_speed
50 runs  sailor_speed_reliability
```

Each condition writes to its own output directory:

```text
.anchor/experiments/baseline
.anchor/experiments/sailor_speed
.anchor/experiments/sailor_speed_reliability
```

## 3. Install And Configure

Install `uv` if needed:

```bash
brew install uv
```

Create and activate the virtual environment:

```bash
uv venv --python 3.12
source .venv/bin/activate
```

Install Anchor with the BeeAI example dependencies:

```bash
uv pip install -e ".[beeai]"
```

Create your environment file:

```bash
cp .env.example .env
```

Configure your model provider in `.env`.

For Hugging Face Inference Providers, use your Hugging Face token and the model you want to test. A good first candidate is:

```text
openai/gpt-oss-20b
```

Keep the same model fixed across the three 50-run conditions. That makes the Sailor effect easier to interpret.

## 4. Useful Environment Variables

Anchor persistence:

```bash
export ANCHOR_PERSISTENCE_BACKEND=sqlite
```

Experiment output path:

```bash
export ANCHOR_OUTPUT_PATH=.anchor/experiments/dev
```

Enable or disable Sailor:

```bash
export ANCHOR_SAILOR_ENABLED=true
export ANCHOR_SAILOR_ENABLED=false
```

Sailor policy:

```bash
export ANCHOR_SAILOR_POLICY=speed
export ANCHOR_SAILOR_POLICY=speed_reliability
```

Failure-rate threshold used by `speed_reliability`:

```bash
export ANCHOR_SAILOR_MAX_FAILURE_RATE=0.2
```

Synthetic tool timing scale:

```bash
export SYNTHETIC_PHYLO_TIME_SCALE=1.0
```

`SYNTHETIC_PHYLO_TIME_SCALE` only changes the deterministic sleep inside the synthetic tools. It does not change the LLM, Sailor, MCP, or Anchor persistence behavior.

## 5. Smoke Test One Run

Before running the full experiment, run a single development workflow:

```bash
export ANCHOR_PERSISTENCE_BACKEND=sqlite
export ANCHOR_OUTPUT_PATH=.anchor/experiments/dev
export ANCHOR_SAILOR_ENABLED=true
export ANCHOR_SAILOR_POLICY=speed_reliability
export SYNTHETIC_PHYLO_TIME_SCALE=1.0

uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.main
```

Expected output:

```text
.anchor/experiments/dev/workflow_db.sqlite
```

The workflow should also produce files under:

```text
examples/commons/synthetic_phylogenetic_subtrees/data/output
```

## 6. Run The 150-Round Experiment

Baseline, without Sailor:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition baseline \
  --runs 50 \
  --anchor-output-path .anchor/experiments/baseline \
  --sailor-policy none
```

Sailor optimizing for speed:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed \
  --sailor-policy speed
```

Sailor optimizing for speed and reliability:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed_reliability \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed_reliability \
  --sailor-policy speed_reliability
```

## 7. Seeding Sailor From Baseline History

If you want Sailor to start from the provenance collected during the baseline condition, seed the Sailor database from the baseline SQLite file:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed \
  --sailor-policy speed \
  --seed-sqlite-from .anchor/experiments/baseline/workflow_db.sqlite
```

And:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.run_experiment \
  --condition sailor_speed_reliability \
  --runs 50 \
  --anchor-output-path .anchor/experiments/sailor_speed_reliability \
  --sailor-policy speed_reliability \
  --seed-sqlite-from .anchor/experiments/baseline/workflow_db.sqlite
```

This is often the most useful setup for the paper narrative: first collect baseline provenance, then evaluate whether Sailor reuses that provenance to improve later runs.

## 8. Outputs

Each experiment directory contains:

```text
workflow_db.sqlite
experiment_config.json
experiment_runs.jsonl
experiment_summary.json
```

`workflow_db.sqlite` is the Anchor provenance database.

`experiment_config.json` records how the condition was executed.

`experiment_runs.jsonl` contains one JSON object per workflow run.

`experiment_summary.json` contains aggregated metrics for the condition.

## 9. Metrics To Compare

Start with these fields in `experiment_summary.json`:

```text
workflow_success_rate
avg_workflow_duration_seconds
avg_total_tool_calls
avg_failed_tool_calls
avg_fallback_count
tool_usage_by_stage
avg_duration_by_stage
avg_failed_attempts_by_stage
```

Useful comparisons:

```text
baseline vs sailor_speed
baseline vs sailor_speed_reliability
sailor_speed vs sailor_speed_reliability
```

The strongest evidence that Sailor helped is usually:

```text
lower average workflow duration
lower failed tool calls
lower fallback count
more frequent selection of historically good tools
similar or better workflow success rate
```

## 10. Regenerate Metrics Only

The experiment runner generates metrics at the end automatically. If you need to regenerate them later from an existing SQLite database:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.experiment_metrics \
  --sqlite-path .anchor/experiments/baseline/workflow_db.sqlite \
  --output-dir .anchor/experiments/baseline \
  --condition baseline \
  --sailor-policy none
```

For a Sailor condition:

```bash
uv run python -m examples.beeai.synthetic_phylogenetic_subtrees.experiment_metrics \
  --sqlite-path .anchor/experiments/sailor_speed_reliability/workflow_db.sqlite \
  --output-dir .anchor/experiments/sailor_speed_reliability \
  --condition sailor_speed_reliability \
  --sailor-policy speed_reliability \
  --sailor-enabled
```

## 11. Optional Model Comparison

For the main experiment, use one fixed model across all three conditions.

Recommended main model:

```text
openai/gpt-oss-20b
```

After the main experiment, you can run a smaller local comparison with Ollama. This answers a different but useful question: whether Sailor still helps when the workflow agent is a smaller model.

Suggested optional design:

```text
10-20 runs baseline with Ollama
10-20 runs Sailor speed_reliability with Ollama
```

Keep this separate from the main results unless you want to frame it as a secondary robustness check.

## 12. Notes For Interpretation

The synthetic tools are deterministic. Some tool profiles always succeed and some always fail in this environment, but the MCP descriptions do not reveal that to the workflow agent.

The point is not to benchmark real bioinformatics tools. The point is to test whether provenance helps an agent learn which operational choices are better after prior executions.

Sailor does not retrain the model. It queries SQLite, aggregates historical tool evidence, and provides compact recommendations to the workflow agent through the provenance handoff agent.
