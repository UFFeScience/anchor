# Synthetic Phylogenetic Subtrees Tools

This package contains the common MCP tools for the synthetic phylogenetic subtrees experiment.

It is based on the original `examples/commons/phylogenetic_subtrees` use case, but exposes multiple realistic tool alternatives for each workflow purpose.

The descriptions are intentionally realistic and do not reveal which implementations are wrappers or deterministic failures. The agent should discover tool behavior through execution, and Anchor should capture that behavior as provenance.

## Tool Profiles

Tool behavior is configured in:

```text
examples/commons/synthetic_phylogenetic_subtrees/tool_profiles.py
```

Each profile has:

```text
name
stage
behavior
sleep_seconds
description
failure_message
```

The execution is deterministic. There is no probabilistic success rate.

## Stages And Tools

### Validation

```text
biopython_sequence_validator
seqkit_sequence_validator
emboss_sequence_validator
biopython_sequence_corrector
seqkit_sequence_deduplicator
emboss_seqret_normalizer
```

### Alignment

```text
mafft_aligner
clustalw_aligner
muscle_aligner
kalign_aligner
```

### Tree Construction

```text
biopython_neighbor_joining_tree_builder
fasttree_tree_builder
iqtree_tree_builder
raxml_tree_builder
```

### Subtree Analysis

```text
anchor_subtree_miner
dendropy_subtree_miner
ete_subtree_miner
treepattern_subtree_miner
```

## Timing

Each tool sleeps for a configured synthetic duration before returning or failing.

Scale sleeps with:

```bash
export SYNTHETIC_PHYLO_TIME_SCALE=1.0
```

For quick smoke tests:

```bash
export SYNTHETIC_PHYLO_TIME_SCALE=0
```

## Implementation Strategy

Successful tools either call the original local implementation or wrap the original implementation while exposing a different realistic tool name.

Failure tools sleep briefly and then raise deterministic execution errors. Their MCP descriptions do not disclose that behavior.

This makes the benchmark useful for provenance reuse:

- the baseline agent must discover tool behavior by trying tools;
- Anchor captures successes, failures, and durations;
- Sailor can later recommend tools based on the captured history.

