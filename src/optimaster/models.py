from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class OptimizationMode(str, Enum):
    SAFE = "safe"
    BALANCED = "balanced"
    LOUDER = "louder"


class SourceProfile(str, Enum):
    VERY_HOT = "very_hot"
    ALMOST_READY = "almost_ready"
    NEEDS_FINISH = "needs_finish"
    LOW_DYNAMICS = "low_dynamics"
    DYNAMIC_OK = "dynamic_ok"
    TOUCH_MINIMALLY = "touch_minimally"


@dataclass(slots=True)
class LoudnessMetrics:
    integrated_lufs: float
    true_peak_dbtp: float
    lra_lu: float
    threshold_lufs: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class SourceAnalysis:
    source_path: Path
    metrics: LoudnessMetrics
    profile: SourceProfile
    diagnostics: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "metrics": self.metrics.to_dict(),
            "profile": self.profile.value,
            "diagnostics": self.diagnostics,
        }


@dataclass(slots=True)
class CandidatePreset:
    name: str
    description: str
    ffmpeg_filter: str
    families: tuple[SourceProfile, ...] = field(default_factory=tuple)

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
    success: bool = True
    error: str | None = None

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
            "success": self.success,
            "error": self.error,
        }


@dataclass(slots=True)
class OptimizationSession:
    session_id: str
    mode: OptimizationMode
    analysis: SourceAnalysis
    candidates: list[CandidateResult]

    @property
    def best_candidate(self) -> CandidateResult | None:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda candidate: candidate.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "analysis": self.analysis.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "best_candidate": self.best_candidate.preset.name if self.best_candidate else None,
        }
