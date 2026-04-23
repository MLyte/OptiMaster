from pathlib import Path

from optimaster.config import AppConfig
from optimaster.models import (
    CandidatePreset,
    LoudnessMetrics,
    OptimizationMode,
    SourceProfile,
)
from optimaster.service import EngineService


def test_analyze_source_emits_progress_updates(monkeypatch, tmp_path: Path):
    input_file = tmp_path / "input.wav"
    input_file.write_bytes(b"stub")

    source_metrics = LoudnessMetrics(
        integrated_lufs=-11.2,
        true_peak_dbtp=-1.4,
        lra_lu=7.1,
        threshold_lufs=-20.0,
    )

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda _: input_file)
    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", lambda _: None)
    monkeypatch.setattr("optimaster.service.analyze_loudness", lambda *_, **__: source_metrics)
    monkeypatch.setattr(
        "optimaster.service.classify_source",
        lambda *_: ("almost_ready", ["Source is close to target range"]),
    )

    progress: list[tuple[str, int]] = []
    analysis = EngineService(AppConfig()).analyze_source(
        input_file=input_file,
        progress_callback=lambda message, percent: progress.append((message, percent)),
    )

    assert analysis.profile is SourceProfile.ALMOST_READY
    assert progress[0] == ("Validating input file", 5)
    assert progress[-1] == ("Source analysis ready", 100)


def test_optimize_writes_exports_and_progress(monkeypatch, tmp_path: Path):
    input_file = tmp_path / "input.wav"
    input_file.write_bytes(b"stub")
    output_dir = tmp_path / "renders"

    source_metrics = LoudnessMetrics(
        integrated_lufs=-11.0,
        true_peak_dbtp=-1.3,
        lra_lu=7.2,
        threshold_lufs=-20.2,
    )
    rendered_metrics = LoudnessMetrics(
        integrated_lufs=-10.1,
        true_peak_dbtp=-1.1,
        lra_lu=6.9,
        threshold_lufs=-19.8,
    )

    preset = CandidatePreset(
        name="safe_limit",
        description="Safe limiter pass",
        ffmpeg_filter="alimiter=limit=-1.0",
    )

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda _: input_file)
    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", lambda _: None)
    monkeypatch.setattr(
        "optimaster.service.analyze_loudness",
        lambda path, **_: source_metrics if Path(path) == input_file else rendered_metrics,
    )
    monkeypatch.setattr("optimaster.service.classify_source", lambda *_: ("almost_ready", ["Stable profile"]))
    monkeypatch.setattr("optimaster.service.select_presets_for_profile", lambda **_: [preset])
    monkeypatch.setattr("optimaster.service.render_candidate", lambda **_: None)
    monkeypatch.setattr(
        "optimaster.service.score_candidate",
        lambda **_: (92.0, ["Stayed inside the safe true-peak target"]),
    )

    progress: list[tuple[str, int]] = []
    session = EngineService(AppConfig()).optimize(
        input_file=input_file,
        output_dir=output_dir,
        mode=OptimizationMode.BALANCED,
        progress_callback=lambda message, percent: progress.append((message, percent)),
    )

    assert session.candidates[0].preset.name == "safe_limit"
    assert (output_dir / "analysis.json").exists()
    assert (output_dir / "ranking.json").exists()
    assert progress[0] == ("Starting optimization session", 0)
    assert progress[-1] == ("Optimization complete", 100)
