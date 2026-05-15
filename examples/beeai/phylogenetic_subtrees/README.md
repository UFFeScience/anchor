# BeeAI Phylogenetic Subtrees Example

This example is a bioinformatics case study for Anchor.

It uses BeeAI agents and MCP tools to run a phylogenetic workflow:

1. Validate protein FASTA files.
2. Correct invalid or duplicated sequences.
3. Run multiple sequence alignment with MAFFT.
4. Build phylogenetic trees with Biopython.
5. Identify frequent subtrees.

Anchor instruments the BeeAI execution and persists provenance data to `.anchor/workflow_db.json`.

## Run

From the repository root:

```bash
uv sync --extra beeai
brew install mafft
cp .env.example .env
uv run python -m examples.beeai.phylogenetic_subtrees.main
```

The example expects Ollama to be available with the model configured in `examples/beeai/phylogenetic_subtrees/constants.py`.
