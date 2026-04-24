from pathlib import Path

from optimaster.config import AppConfig
from optimaster.models import (
    CandidatePreset,
    LoudnessMetrics,
    OptimizationMode,
    SourceAnalysis,
    SourceProfile,
)
from optimaster.service import EngineService


def test_analyze_source_checks_ffmpeg_once(monkeypatch, tmp_path):
    config = AppConfig()
    service = EngineService(config=config)

    source = tmp_path / "mix.wav"
    source.write_text("data", encoding="utf-8")

    ffmpeg_checks: list[str] = []

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda path: Path(path))

    def fake_check(binary: str) -> None:
        ffmpeg_checks.append(binary)

    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", fake_check)
    monkeypatch.setattr(
        "optimaster.service.analyze_loudness",
        lambda *_args, **_kwargs: LoudnessMetrics(-11.0, -1.2, 7.1, -21.0),
    )
    monkeypatch.setattr(
        "optimaster.service.classify_source",
        lambda *_: ("almost_ready", ["Source is close to target range"]),
    )

    service.analyze_source(source)
    service.analyze_source(source)

    assert ffmpeg_checks == ["ffmpeg"]


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


def test_optimize_reuses_precomputed_analysis(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_text("data", encoding="utf-8")

    precomputed_analysis = SourceAnalysis(
        source_path=source,
        metrics=LoudnessMetrics(-12.0, -1.5, 7.5, -22.0),
        profile=SourceProfile.NEEDS_FINISH,
        diagnostics=["Ready"],
    )

    service = EngineService(config=AppConfig(enabled_presets=["do_almost_nothing"]))

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda path: Path(path))
    monkeypatch.setattr(
        "optimaster.service.select_presets_for_profile",
        lambda **_kwargs: [
            CandidatePreset(
                name="do_almost_nothing",
                description="Minimal",
                ffmpeg_filter="volume=-0.8dB",
                families=(SourceProfile.NEEDS_FINISH,),
            )
        ],
    )
    monkeypatch.setattr("optimaster.service.render_candidate", lambda **_kwargs: None)
    monkeypatch.setattr(
        "optimaster.service.analyze_loudness",
        lambda *_args, **_kwargs: LoudnessMetrics(-10.2, -1.1, 6.8, -20.2),
    )
    monkeypatch.setattr("optimaster.service.score_candidate", lambda **_kwargs: (97.0, ["Good"]))
    monkeypatch.setattr("optimaster.service.EngineService._write_exports", lambda *_args, **_kwargs: None)

    analyze_calls: list[str] = []

    original_analyze = EngineService.analyze_source

    def fail_if_called(self, *_args, **_kwargs):
        analyze_calls.append("called")
        return original_analyze(self, *_args, **_kwargs)

    monkeypatch.setattr(EngineService, "analyze_source", fail_if_called)

    session = service.optimize(
        input_file=source,
        output_dir=tmp_path / "renders",
        mode=OptimizationMode.BALANCED,
        source_analysis=precomputed_analysis,
    )

    assert not analyze_calls
    assert session.analysis is precomputed_analysis
    assert session.candidates


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


def test_optimize_applies_target_lufs_to_render_filter(monkeypatch, tmp_path: Path):
    input_file = tmp_path / "input.wav"
    input_file.write_bytes(b"stub")
    output_dir = tmp_path / "renders"
    metrics = LoudnessMetrics(-11.0, -1.3, 7.2, -20.2)
    preset = CandidatePreset(
        name="transparent_trim",
        description="Transparent trim",
        ffmpeg_filter="volume=-1.5dB",
    )
    render_filters: list[str] = []

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda _: input_file)
    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", lambda _: None)
    monkeypatch.setattr("optimaster.service.analyze_loudness", lambda *_args, **_kwargs: metrics)
    monkeypatch.setattr("optimaster.service.classify_source", lambda *_: ("almost_ready", ["Stable profile"]))
    monkeypatch.setattr("optimaster.service.select_presets_for_profile", lambda **_: [preset])
    monkeypatch.setattr(
        "optimaster.service.render_candidate",
        lambda **kwargs: render_filters.append(kwargs["ffmpeg_filter"]),
    )
    monkeypatch.setattr("optimaster.service.score_candidate", lambda **_: (92.0, ["Good"]))
    monkeypatch.setattr("optimaster.service.EngineService._write_exports", lambda *_args, **_kwargs: None)

    EngineService(AppConfig()).optimize(
        input_file=input_file,
        output_dir=output_dir,
        mode=OptimizationMode.LOUDER,
        target_lufs=-8.0,
    )

    assert render_filters == [
        "volume=-1.5dB,loudnorm=I=-8.0:TP=-0.8:LRA=7.0",
        "volume=-1.5dB",
    ]


def test_target_lufs_uses_performance_scoring(monkeypatch, tmp_path: Path):
    input_file = tmp_path / "input.wav"
    input_file.write_bytes(b"stub")
    metrics = LoudnessMetrics(-9.9, -1.0, 4.5, -20.2)
    preset = CandidatePreset(
        name="sweet_spot",
        description="Balanced finish",
        ffmpeg_filter="volume=-1.7dB,alimiter=limit=-1dB",
    )
    scoring_configs = []

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda _: input_file)
    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", lambda _: None)
    monkeypatch.setattr("optimaster.service.analyze_loudness", lambda *_args, **_kwargs: metrics)
    monkeypatch.setattr("optimaster.service.classify_source", lambda *_: ("dynamic_ok", ["Stable profile"]))
    monkeypatch.setattr("optimaster.service.select_presets_for_profile", lambda **_: [preset])
    monkeypatch.setattr("optimaster.service.render_candidate", lambda **_kwargs: None)

    def fake_score_candidate(**kwargs):
        scoring_configs.append(kwargs["cfg"])
        return 92.0, ["Good"]

    monkeypatch.setattr("optimaster.service.score_candidate", fake_score_candidate)
    monkeypatch.setattr("optimaster.service.EngineService._write_exports", lambda *_args, **_kwargs: None)

    EngineService(AppConfig()).optimize(
        input_file=input_file,
        output_dir=tmp_path / "renders",
        mode=OptimizationMode.LOUDER,
        target_lufs=-8.0,
    )

    assert scoring_configs[0].min_lra == 3.5
    assert scoring_configs[0].preferred_lra_min == 4.5
    assert scoring_configs[0].max_lufs_delta_from_source == 5.0
    assert scoring_configs[1].min_lra > scoring_configs[0].min_lra


def test_maximize_loudness_renders_loudness_search(monkeypatch, tmp_path: Path):
    input_file = tmp_path / "input.wav"
    input_file.write_bytes(b"stub")
    metrics = LoudnessMetrics(-10.0, -1.0, 6.0, -20.2)
    preset = CandidatePreset(
        name="sweet_spot",
        description="Balanced finish",
        ffmpeg_filter="volume=-1.7dB,alimiter=limit=-1dB",
    )
    render_filters: list[str] = []

    monkeypatch.setattr("optimaster.service.validate_input_file", lambda _: input_file)
    monkeypatch.setattr("optimaster.service.assert_ffmpeg_available", lambda _: None)
    monkeypatch.setattr("optimaster.service.analyze_loudness", lambda *_args, **_kwargs: metrics)
    monkeypatch.setattr("optimaster.service.classify_source", lambda *_: ("dynamic_ok", ["Stable profile"]))
    monkeypatch.setattr("optimaster.service.select_presets_for_profile", lambda **_: [preset])
    monkeypatch.setattr(
        "optimaster.service.render_candidate",
        lambda **kwargs: render_filters.append(kwargs["ffmpeg_filter"]),
    )
    monkeypatch.setattr("optimaster.service.score_candidate", lambda **_: (80.0, ["Good"]))
    monkeypatch.setattr("optimaster.service.EngineService._write_exports", lambda *_args, **_kwargs: None)

    session = EngineService(AppConfig()).optimize(
        input_file=input_file,
        output_dir=tmp_path / "renders",
        mode=OptimizationMode.LOUDER,
        target_lufs=-8.0,
        maximize_loudness=True,
    )

    assert len(render_filters) == 6
    assert render_filters[0].endswith("loudnorm=I=-10.0:TP=-0.5:LRA=7.0")
    assert render_filters[4].endswith("loudnorm=I=-6.0:TP=-0.5:LRA=7.0")
    assert render_filters[5] == "volume=-1.7dB,alimiter=limit=-1dB"
    assert any("_loudest_" in candidate.preset.name for candidate in session.candidates)
