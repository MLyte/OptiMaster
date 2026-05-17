from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from optimaster.models import OptimizationMode


@dataclass(slots=True)
class ScoringConfig:
    target_lufs_min: float = -11.0
    target_lufs_max: float = -9.0
    ideal_true_peak_max: float = -1.0
    hard_true_peak_max: float = -0.5
    min_lra: float = 5.0
    preferred_lra_min: float = 6.0
    max_lufs_delta_from_source: float = 2.0


@dataclass(slots=True)
class AiMasteringConfig:
    base_url: str = "https://api.bakuage.com"
    token_env: str = "AIMASTERING_ACCESS_TOKEN"
    access_token: str | None = None
    auth_prefix: str = ""
    poll_interval_seconds: float = 3.0
    timeout_seconds: float = 60.0
    job_timeout_seconds: float = 900.0
    preset: str = "general"
    bit_depth: int = 24


@dataclass(slots=True)
class AppConfig:
    ffmpeg_binary: str = "ffmpeg"
    output_format: str = "wav"
    default_mode: OptimizationMode = OptimizationMode.BALANCED
    enabled_presets: list[str] = field(
        default_factory=lambda: [
            "do_almost_nothing",
            "transparent_trim",
            "safe_limit",
            "sweet_spot",
            "gentle_glue",
        ]
    )
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    aimastering: AiMasteringConfig = field(default_factory=AiMasteringConfig)


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return AppConfig()

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    scoring_raw = raw.get("scoring", {})
    presets_raw = raw.get("presets", {})
    aimastering_raw = raw.get("aimastering", {})
    mode = str(raw.get("default_mode", OptimizationMode.BALANCED.value)).lower()
    return AppConfig(
        ffmpeg_binary=raw.get("ffmpeg_binary", "ffmpeg"),
        output_format=raw.get("output_format", "wav"),
        default_mode=OptimizationMode(mode),
        enabled_presets=presets_raw.get(
            "enabled",
            [
                "do_almost_nothing",
                "transparent_trim",
                "safe_limit",
                "sweet_spot",
                "gentle_glue",
            ],
        ),
        scoring=ScoringConfig(
            target_lufs_min=float(scoring_raw.get("target_lufs_min", -11.0)),
            target_lufs_max=float(scoring_raw.get("target_lufs_max", -9.0)),
            ideal_true_peak_max=float(scoring_raw.get("ideal_true_peak_max", -1.0)),
            hard_true_peak_max=float(scoring_raw.get("hard_true_peak_max", -0.5)),
            min_lra=float(scoring_raw.get("min_lra", 5.0)),
            preferred_lra_min=float(scoring_raw.get("preferred_lra_min", 6.0)),
            max_lufs_delta_from_source=float(scoring_raw.get("max_lufs_delta_from_source", 2.0)),
        ),
        aimastering=AiMasteringConfig(
            base_url=str(aimastering_raw.get("base_url", "https://api.bakuage.com")).rstrip("/"),
            token_env=str(aimastering_raw.get("token_env", "AIMASTERING_ACCESS_TOKEN")),
            auth_prefix=str(aimastering_raw.get("auth_prefix", "")),
            poll_interval_seconds=float(aimastering_raw.get("poll_interval_seconds", 3.0)),
            timeout_seconds=float(aimastering_raw.get("timeout_seconds", 60.0)),
            job_timeout_seconds=float(aimastering_raw.get("job_timeout_seconds", 900.0)),
            preset=str(aimastering_raw.get("preset", "general")),
            bit_depth=int(aimastering_raw.get("bit_depth", 24)),
        ),
    )
