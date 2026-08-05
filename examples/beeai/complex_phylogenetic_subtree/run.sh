#!/bin/bash

ANCHOR_OUTPUT_PATH="${ANCHOR_OUTPUT_PATH:-.anchor}"

# Remove previous example output.
rm -rf examples/commons/complex_phylogenetic_subtree/data/output/align
rm -rf examples/commons/complex_phylogenetic_subtree/data/output/validated-files
rm -f examples/commons/complex_phylogenetic_subtree/data/output/frequent-subtrees.json
rm -f "$ANCHOR_OUTPUT_PATH/workflow_db.json"

# Run the case study.
time python -m examples.beeai.complex_phylogenetic_subtree.main
