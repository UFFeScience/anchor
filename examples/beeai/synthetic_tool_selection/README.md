# Synthetic Tool Selection Benchmark

This example is a small BeeAI + MCP workflow designed to validate Anchor Sailor.

The workflow has three ordered stages:

```text
cleaning -> feature extraction -> scoring
```

Each stage exposes multiple tools with the same purpose but different simulated reliability and runtime profiles. The simulator is probabilistic, but reproducible with `SYNTHETIC_SEED`.

Run it several times to generate provenance:

```bash
export SYNTHETIC_SEED=42
export SYNTHETIC_TIME_SCALE=1.0
uv run python -m examples.beeai.synthetic_tool_selection.main
uv run python -m anchor.telemetry.persistence.tinydb_to_sql
```

Then inspect Sailor recommendations:

```bash
uv run python -c "from anchor.sailor import compare_tools; print(compare_tools(tool_names=['fast_cleaner', 'balanced_cleaner', 'strict_cleaner']))"
```

