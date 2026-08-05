#!/bin/bash

ANCHOR_OUTPUT_PATH="${ANCHOR_OUTPUT_PATH:-.anchor}"

export ANCHOR_PERSISTENCE_BACKEND="${ANCHOR_PERSISTENCE_BACKEND:-sqlite}"
export ANCHOR_SAILOR_ENABLED="${ANCHOR_SAILOR_ENABLED:-true}"
export SYNTHETIC_PHYLO_TIME_SCALE="${SYNTHETIC_PHYLO_TIME_SCALE:-1.0}"

time python -m examples.beeai.synthetic_phylogenetic_subtrees.main
