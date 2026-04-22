from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class ScoringConfig:
    target_lufs_min: float = -11.0
    target_lufs_max: float = -9.0
    ideal_true_peak_max: float = -1.0
    hard_true_peak_max: float = -0.5
    min_lra: float = 5.0
    preferred_lra_min: float = 6.0


@dataclass(slots=True)
class AppConfig:
    ffmpeg_binary: str = "ffmpeg"
    output_format: str = "wav"
    enabled_presets: list[str] = field(default_factory=lambda: [
        "transparent_trim",
        "safe_limit",
        "sweet_spot",
        "gentle_glue",
    ])
    scoring: ScoringConfig = field(default_factory=ScoringConfig)


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return AppConfig()

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    scoring_raw = raw.get("scoring", {})
    presets_raw = raw.get("presets", {})
    return AppConfig(
        ffmpeg_binary=raw.get("ffmpeg_binary", "ffmpeg"),
        output_format=raw.get("output_format", "wav"),
        enabled_presets=presets_raw.get("enabled", [
            "transparent_trim",
            "safe_limit",
            "sweet_spot",
            "gentle_glue",
        ]),
        scoring=ScoringConfig(
            target_lufs_min=float(scoring_raw.get("target_lufs_min", -11.0)),
            target_lufs_max=float(scoring_raw.get("target_lufs_max", -9.0)),
            ideal_true_peak_max=float(scoring_raw.get("ideal_true_peak_max", -1.0)),
            hard_true_peak_max=float(scoring_raw.get("hard_true_peak_max", -0.5)),
            min_lra=float(scoring_raw.get("min_lra", 5.0)),
            preferred_lra_min=float(scoring_raw.get("preferred_lra_min", 6.0)),
        ),
    )
