from __future__ import annotations

from optimaster.config import ScoringConfig
from optimaster.models import LoudnessMetrics


def score_candidate(metrics: LoudnessMetrics, cfg: ScoringConfig) -> tuple[float, list[str]]:
    score = 100.0
    reasons: list[str] = []

    if metrics.true_peak_dbtp > cfg.hard_true_peak_max:
        score -= 60
        reasons.append("Unsafe true peak above hard ceiling.")
    elif metrics.true_peak_dbtp > cfg.ideal_true_peak_max:
        score -= 20
        reasons.append("True peak is safe-ish but above the ideal ceiling.")
    else:
        reasons.append("True peak is within the preferred safe zone.")

    if metrics.integrated_lufs < cfg.target_lufs_min:
        score -= 8
        reasons.append("Output is quieter than the preferred loudness range.")
    elif metrics.integrated_lufs > cfg.target_lufs_max:
        score -= 12
        reasons.append("Output is louder than the preferred loudness range.")
    else:
        reasons.append("Output loudness sits in the preferred range.")

    if metrics.lra_lu < cfg.min_lra:
        score -= 20
        reasons.append("Dynamic range dropped below the minimum target.")
    elif metrics.lra_lu < cfg.preferred_lra_min:
        score -= 8
        reasons.append("Dynamic range is acceptable but slightly restrained.")
    else:
        reasons.append("Dynamic range is preserved well.")

    return round(max(score, 0.0), 2), reasons
