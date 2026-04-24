from optimaster.config import AppConfig, ScoringConfig
from optimaster.service import EngineService


def test_runtime_scoring_profile_applies_destination_overrides():
    service = EngineService(config=AppConfig(scoring=ScoringConfig()))
    cfg = service._runtime_scoring_config("archive_safe", strict_true_peak=False)
    assert cfg.target_lufs_min == -13.0
    assert cfg.target_lufs_max == -11.0
    assert cfg.hard_true_peak_max == -0.9


def test_runtime_scoring_profile_applies_strict_true_peak_cap():
    service = EngineService(config=AppConfig(scoring=ScoringConfig()))
    cfg = service._runtime_scoring_config("club_loud", strict_true_peak=True)
    assert cfg.ideal_true_peak_max <= -1.2
    assert cfg.hard_true_peak_max <= -1.0
