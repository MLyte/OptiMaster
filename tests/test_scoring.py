from optimaster.config import ScoringConfig
from optimaster.models import LoudnessMetrics, OptimizationMode, SourceProfile
from optimaster.presets import select_presets_for_profile
from optimaster.scoring import classify_source, score_candidate


def test_score_candidate_prefers_safe_reasonable_output():
    metrics = LoudnessMetrics(
        integrated_lufs=-10.2,
        true_peak_dbtp=-1.1,
        lra_lu=7.0,
        threshold_lufs=-20.0,
    )
    source_metrics = LoudnessMetrics(
        integrated_lufs=-11.0,
        true_peak_dbtp=-1.3,
        lra_lu=7.5,
        threshold_lufs=-21.0,
    )
    score, reasons = score_candidate(metrics, ScoringConfig(), source_metrics, OptimizationMode.BALANCED)
    assert score > 80
    assert any("safe zone" in reason.lower() for reason in reasons)


def test_score_candidate_penalizes_unsafe_true_peak():
    metrics = LoudnessMetrics(
        integrated_lufs=-8.5,
        true_peak_dbtp=0.3,
        lra_lu=6.5,
        threshold_lufs=-19.0,
    )
    source_metrics = LoudnessMetrics(
        integrated_lufs=-10.0,
        true_peak_dbtp=-1.2,
        lra_lu=7.0,
        threshold_lufs=-19.0,
    )
    score, reasons = score_candidate(metrics, ScoringConfig(), source_metrics, OptimizationMode.BALANCED)
    assert score < 60
    assert any("unsafe true peak" in reason.lower() for reason in reasons)


def test_classify_source_very_hot_when_true_peak_too_high():
    profile, reasons = classify_source(
        LoudnessMetrics(
            integrated_lufs=-12.0,
            true_peak_dbtp=-0.2,
            lra_lu=6.0,
            threshold_lufs=-21.0,
        )
    )
    assert profile == "very_hot"
    assert reasons


def test_select_presets_for_safe_mode_very_hot_profile():
    presets = select_presets_for_profile(
        profile=SourceProfile.VERY_HOT,
        mode=OptimizationMode.SAFE,
        enabled_presets=[
            "do_almost_nothing",
            "transparent_trim",
            "safe_limit",
            "sweet_spot",
            "gentle_glue",
        ],
    )
    assert [preset.name for preset in presets] == ["transparent_trim", "safe_limit"]
