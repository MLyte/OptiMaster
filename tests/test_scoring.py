from optimaster.config import ScoringConfig
from optimaster.models import LoudnessMetrics
from optimaster.scoring import score_candidate


def test_score_candidate_prefers_safe_reasonable_output():
    metrics = LoudnessMetrics(
        integrated_lufs=-10.2,
        true_peak_dbtp=-1.1,
        lra_lu=7.0,
        threshold_lufs=-20.0,
    )
    score, reasons = score_candidate(metrics, ScoringConfig())
    assert score > 80
    assert any("safe zone" in reason.lower() for reason in reasons)


def test_score_candidate_penalizes_unsafe_true_peak():
    metrics = LoudnessMetrics(
        integrated_lufs=-8.5,
        true_peak_dbtp=0.3,
        lra_lu=6.5,
        threshold_lufs=-19.0,
    )
    score, reasons = score_candidate(metrics, ScoringConfig())
    assert score < 60
    assert any("unsafe true peak" in reason.lower() for reason in reasons)
