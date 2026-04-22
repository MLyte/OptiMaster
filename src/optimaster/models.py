from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LoudnessMetrics:
    integrated_lufs: float
    true_peak_dbtp: float
    lra_lu: float
    threshold_lufs: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class CandidatePreset:
    name: str
    description: str
    ffmpeg_filter: str

    def output_name(self, source: Path, suffix: str = ".wav") -> str:
        return f"{source.stem}_{self.name}{suffix}"


@dataclass(slots=True)
class CandidateResult:
    preset: CandidatePreset
    output_path: Path
    source_metrics: LoudnessMetrics
    output_metrics: LoudnessMetrics
    score: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset": {
                "name": self.preset.name,
                "description": self.preset.description,
                "ffmpeg_filter": self.preset.ffmpeg_filter,
            },
            "output_path": str(self.output_path),
            "source_metrics": self.source_metrics.to_dict(),
            "output_metrics": self.output_metrics.to_dict(),
            "score": self.score,
            "reasons": self.reasons,
        }
