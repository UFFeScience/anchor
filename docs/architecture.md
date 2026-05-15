# Architecture

Anchor is organized as a core provenance framework plus standalone examples.

The core package lives under `src/anchor` and contains:

- `model`: interaction-centric provenance schema.
- `observability`: framework-specific instrumentation entry points.
- `telemetry`: OpenTelemetry/OpenInference span collection, semantic translation, schema definitions, and persistence.
- `prov`: conversion from Anchor's interaction-centric model to W3C PROV artifacts.

The `examples/beeai/phylogenetic_subtrees` directory is a case study. It uses BeeAI agents and MCP tools to run a phylogenetic workflow, while Anchor observes the execution and persists provenance records.
