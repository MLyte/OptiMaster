from __future__ import annotations

from optimaster.config import ScoringConfig
from optimaster.models import LoudnessMetrics, OptimizationMode


def classify_source(metrics: LoudnessMetrics) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if metrics.true_peak_dbtp >= -0.7:
        reasons.append("Source true peak is already close to 0 dBTP.")
        return "very_hot", reasons
    if metrics.integrated_lufs >= -10.0:
        reasons.append("Source loudness is already high for a prudent finishing workflow.")
        return "almost_ready", reasons
    if metrics.lra_lu < 4.5:
        reasons.append("Source dynamic range is low, avoid heavy processing.")
        return "low_dynamics", reasons
    if metrics.lra_lu >= 6.0:
        reasons.append("Source has healthy dynamics to preserve.")
        return "dynamic_ok", reasons
    reasons.append("Source needs a light finishing pass without drastic changes.")
    return "needs_finish", reasons


def _mode_target_bounds(mode: OptimizationMode, cfg: ScoringConfig) -> tuple[float, float]:
    if mode == OptimizationMode.SAFE:
        return cfg.target_lufs_min - 1.0, cfg.target_lufs_max - 0.5
    if mode == OptimizationMode.LOUDER:
        return cfg.target_lufs_min + 0.5, cfg.target_lufs_max + 0.5
    return cfg.target_lufs_min, cfg.target_lufs_max


def score_candidate(
    metrics: LoudnessMetrics,
    cfg: ScoringConfig,
    source_metrics: LoudnessMetrics,
    mode: OptimizationMode = OptimizationMode.BALANCED,
) -> tuple[float, list[str]]:
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

    target_min, target_max = _mode_target_bounds(mode, cfg)
    if metrics.integrated_lufs < target_min:
        score -= 8
        reasons.append("Output is quieter than the preferred loudness range for this mode.")
    elif metrics.integrated_lufs > target_max:
        score -= 12
        reasons.append("Output is louder than the preferred loudness range for this mode.")
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

    loudness_delta = abs(metrics.integrated_lufs - source_metrics.integrated_lufs)
    if loudness_delta > cfg.max_lufs_delta_from_source:
        score -= 10
        reasons.append("Transformation is too aggressive compared to the source loudness.")
    else:
        reasons.append("Loudness shift stays in a prudent range.")

    lra_drop = source_metrics.lra_lu - metrics.lra_lu
    if lra_drop > 2.0:
        score -= 10
        reasons.append("Candidate loses too much dynamic range versus source.")

    return round(max(score, 0.0), 2), reasons
