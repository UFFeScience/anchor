# BeeAI Complex Phylogenetic Subtree Example

This example is a bioinformatics case study for Anchor.

It follows the same multi-agent architecture as the original phylogenetic subtree example, but each specialist stage has multiple MCP tools with the same purpose. When `ANCHOR_SAILOR_ENABLED=true`, each specialist agent also receives a `provenance_agent` handoff and may consult Anchor Sailor before choosing a tool.

It uses BeeAI agents and MCP tools to run a phylogenetic workflow:

1. Validate protein FASTA files.
2. Correct invalid or duplicated sequences.
3. Run multiple sequence alignment.
4. Build phylogenetic trees.
5. Identify frequent subtrees.

Anchor instruments the BeeAI execution and persists provenance data according to the configured Anchor persistence backend.

## Run

From the repository root:

```bash
uv sync --extra beeai
brew install mafft
cp .env.example .env
export ANCHOR_LLM=ollama:granite3.3:8b
export ANCHOR_SAILOR_ENABLED=false
uv run python -m examples.beeai.complex_phylogenetic_subtree.main
```

Set `ANCHOR_SAILOR_ENABLED=true` after a provenance database exists and you want each specialist agent to consult Sailor before choosing among equivalent tools.
