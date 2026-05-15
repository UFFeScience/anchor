from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any

from examples.commons.synthetic_tool_selection.config import TOOL_PROFILES


EXAMPLE_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = EXAMPLE_ROOT / "data" / "input" / "cases.json"
DEFAULT_OUTPUT_PATH = EXAMPLE_ROOT / "data" / "output"


def default_input_path() -> str:
    return str(DEFAULT_INPUT_PATH)


def default_output_path() -> Path:
    return Path(os.getenv("OUTPUT_PATH", str(DEFAULT_OUTPUT_PATH)))


def run_synthetic_tool(tool_name: str, input_path: str | None = None) -> str:
    if tool_name not in TOOL_PROFILES:
        raise ValueError(f"Unknown synthetic tool: {tool_name}")

    profile = TOOL_PROFILES[tool_name]
    source_path = Path(input_path or DEFAULT_INPUT_PATH)
    output_root = default_output_path()
    output_root.mkdir(parents=True, exist_ok=True)

    state = _load_state(output_root)
    invocation_count = state.get(tool_name, 0) + 1
    state[tool_name] = invocation_count
    _save_state(output_root, state)

    seed = os.getenv("SYNTHETIC_SEED", "42")
    rng = random.Random(f"{seed}:{tool_name}:{invocation_count}:{source_path}")
    duration = rng.uniform(profile.min_duration, profile.max_duration)
    time.sleep(duration * float(os.getenv("SYNTHETIC_TIME_SCALE", "1.0")))

    attempt = {
        "tool": tool_name,
        "stage": profile.stage,
        "invocation_count_for_tool": invocation_count,
        "seed": seed,
        "input_path": str(source_path),
        "simulated_duration_seconds": round(duration, 4),
        "success_rate": profile.success_rate,
    }

    if rng.random() > profile.success_rate:
        failure_mode = rng.choice(profile.failure_modes)
        failure_path = _write_result(output_root, profile.stage, tool_name, invocation_count, {
            **attempt,
            "status": "failed",
            "failure_mode": failure_mode,
        })
        raise RuntimeError(
            f"{tool_name} failed with {failure_mode}. Failure metadata: {failure_path}"
        )

    records = _load_records(source_path)
    result = {
        **attempt,
        "status": "completed",
        "record_count": len(records),
        "quality": profile.quality,
        "summary": _stage_summary(profile.stage, tool_name, records, profile.quality),
    }
    return str(_write_result(output_root, profile.stage, tool_name, invocation_count, result))


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return data["records"]
    if isinstance(data, list):
        return data
    return []


def _stage_summary(stage: str, tool_name: str, records: list[dict[str, Any]], quality: float) -> str:
    return (
        f"{tool_name} completed {stage} for {len(records)} synthetic records "
        f"with simulated quality {quality:.2f}."
    )


def _state_path(output_root: Path) -> Path:
    return output_root / ".synthetic_tool_state.json"


def _load_state(output_root: Path) -> dict[str, int]:
    path = _state_path(output_root)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {str(key): int(value) for key, value in data.items()}


def _save_state(output_root: Path, state: dict[str, int]) -> None:
    path = _state_path(output_root)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)


def _write_result(output_root: Path, stage: str, tool_name: str, invocation_count: int, payload: dict[str, Any]) -> Path:
    stage_dir = output_root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{invocation_count:03d}_{tool_name}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
    return path
