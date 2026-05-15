#!/usr/bin/env bash
set -euo pipefail

export SYNTHETIC_SEED="${SYNTHETIC_SEED:-42}"
export SYNTHETIC_TIME_SCALE="${SYNTHETIC_TIME_SCALE:-1.0}"
export ANCHOR_OUTPUT_PATH="${ANCHOR_OUTPUT_PATH:-.anchor}"

uv run python -m examples.beeai.synthetic_tool_selection.main

