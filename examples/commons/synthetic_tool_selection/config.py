from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolProfile:
    name: str
    stage: str
    success_rate: float
    min_duration: float
    max_duration: float
    quality: float
    failure_modes: tuple[str, ...]


TOOL_PROFILES: dict[str, ToolProfile] = {
    "fast_cleaner": ToolProfile(
        name="fast_cleaner",
        stage="cleaning",
        success_rate=0.65,
        min_duration=0.05,
        max_duration=0.10,
        quality=0.70,
        failure_modes=("missing_values_left", "schema_drift"),
    ),
    "balanced_cleaner": ToolProfile(
        name="balanced_cleaner",
        stage="cleaning",
        success_rate=0.85,
        min_duration=0.12,
        max_duration=0.20,
        quality=0.84,
        failure_modes=("partial_normalization", "unexpected_nulls"),
    ),
    "strict_cleaner": ToolProfile(
        name="strict_cleaner",
        stage="cleaning",
        success_rate=0.97,
        min_duration=0.25,
        max_duration=0.35,
        quality=0.95,
        failure_modes=("overly_strict_validation",),
    ),
    "quick_feature_extractor": ToolProfile(
        name="quick_feature_extractor",
        stage="feature_extraction",
        success_rate=0.70,
        min_duration=0.05,
        max_duration=0.12,
        quality=0.68,
        failure_modes=("feature_underflow", "invalid_vector_shape"),
    ),
    "robust_feature_extractor": ToolProfile(
        name="robust_feature_extractor",
        stage="feature_extraction",
        success_rate=0.93,
        min_duration=0.20,
        max_duration=0.30,
        quality=0.91,
        failure_modes=("feature_validation_error",),
    ),
    "experimental_feature_extractor": ToolProfile(
        name="experimental_feature_extractor",
        stage="feature_extraction",
        success_rate=0.55,
        min_duration=0.08,
        max_duration=0.18,
        quality=0.88,
        failure_modes=("unstable_embedding", "timeout"),
    ),
    "fast_scorer": ToolProfile(
        name="fast_scorer",
        stage="scoring",
        success_rate=0.75,
        min_duration=0.05,
        max_duration=0.10,
        quality=0.72,
        failure_modes=("low_confidence_score",),
    ),
    "accurate_scorer": ToolProfile(
        name="accurate_scorer",
        stage="scoring",
        success_rate=0.95,
        min_duration=0.25,
        max_duration=0.38,
        quality=0.96,
        failure_modes=("calibration_error",),
    ),
    "unstable_scorer": ToolProfile(
        name="unstable_scorer",
        stage="scoring",
        success_rate=0.45,
        min_duration=0.04,
        max_duration=0.08,
        quality=0.80,
        failure_modes=("timeout", "invalid_score", "runtime_error"),
    ),
}


STAGE_TOOLS = {
    "cleaning": ["fast_cleaner", "balanced_cleaner", "strict_cleaner"],
    "feature_extraction": [
        "quick_feature_extractor",
        "robust_feature_extractor",
        "experimental_feature_extractor",
    ],
    "scoring": ["fast_scorer", "accurate_scorer", "unstable_scorer"],
}

