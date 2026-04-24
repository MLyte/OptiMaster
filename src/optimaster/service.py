from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from optimaster.config import AppConfig
from optimaster.ffmpeg import analyze_loudness, assert_ffmpeg_available, render_candidate, validate_input_file
from optimaster.models import (
    CandidateResult,
    OptimizationMode,
    OptimizationSession,
    SourceAnalysis,
    SourceProfile,
)
from optimaster.preferences import PreferenceStore
from optimaster.presets import select_presets_for_profile
from optimaster.scoring import classify_source, score_candidate


PROFILE_MAP = {
    "very_hot": SourceProfile.VERY_HOT,
    "almost_ready": SourceProfile.ALMOST_READY,
    "needs_finish": SourceProfile.NEEDS_FINISH,
    "low_dynamics": SourceProfile.LOW_DYNAMICS,
    "dynamic_ok": SourceProfile.DYNAMIC_OK,
}

ProgressCallback = Callable[[str, int], None]


DESTINATION_SCORING_OVERRIDES = {
    "streaming_prudent": {
        "target_lufs_min": -12.0,
        "target_lufs_max": -10.0,
        "ideal_true_peak_max": -1.1,
        "hard_true_peak_max": -0.8,
    },
    "club_loud": {
        "target_lufs_min": -10.0,
        "target_lufs_max": -8.0,
        "ideal_true_peak_max": -1.0,
        "hard_true_peak_max": -0.5,
        "max_lufs_delta_from_source": 2.5,
    },
    "archive_safe": {
        "target_lufs_min": -13.0,
        "target_lufs_max": -11.0,
        "ideal_true_peak_max": -1.2,
        "hard_true_peak_max": -0.9,
        "min_lra": 5.5,
        "preferred_lra_min": 6.5,
    },
}


@dataclass(slots=True)
class EngineService:
    config: AppConfig
    preference_path: Path | None = None
    _ffmpeg_checked: bool = False

    def analyze_source(
        self,
        input_file: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> SourceAnalysis:
        self._notify(progress_callback, "Validating input file", 5)
        input_path = validate_input_file(input_file)
        self._notify(progress_callback, "Checking FFmpeg availability", 15)
        self._ensure_ffmpeg_available()
        self._notify(progress_callback, "Analyzing source loudness", 35)
        source_metrics = analyze_loudness(input_path, ffmpeg_binary=self.config.ffmpeg_binary)
        profile_str, diagnostics = classify_source(source_metrics)
        profile = PROFILE_MAP.get(profile_str, SourceProfile.TOUCH_MINIMALLY)
        self._notify(progress_callback, "Source analysis ready", 100)
        return SourceAnalysis(
            source_path=input_path,
            metrics=source_metrics,
            profile=profile,
            diagnostics=diagnostics,
        )

    def add_listening_note(self, preset_name: str, rating: int) -> Path:
        preference_path = self.preference_path or (Path.cwd() / "renders" / "preferences.json")
        store = PreferenceStore(preference_path)
        store.save_note(preset_name=preset_name, rating=rating)
        return preference_path

    def optimize(
        self,
        input_file: str | Path,
        output_dir: str | Path,
        mode: OptimizationMode | None = None,
        source_analysis: SourceAnalysis | None = None,
        destination_profile: str = "streaming_prudent",
        strict_true_peak: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> OptimizationSession:
        selected_mode = mode or self.config.default_mode
        scoring_cfg = self._runtime_scoring_config(destination_profile, strict_true_peak)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        self._notify(progress_callback, "Starting optimization session", 0)
        input_path = validate_input_file(input_file)
        analysis = source_analysis
        if analysis is not None and analysis.source_path != input_path:
            analysis = None

        if analysis is None:
            analysis = self.analyze_source(input_path, progress_callback=progress_callback)
        else:
            self._notify(progress_callback, "Reusing existing source analysis", 40)

        presets = select_presets_for_profile(
            profile=analysis.profile,
            mode=selected_mode,
            enabled_presets=self.config.enabled_presets,
        )
        self._notify(progress_callback, f"Selected {len(presets)} candidate presets", 45)

        preference_path = self.preference_path or (out_dir / "preferences.json")
        preset_bias = PreferenceStore(preference_path).load()

        results: list[CandidateResult] = []
        total_presets = max(len(presets), 1)
        for idx, preset in enumerate(presets, start=1):
            render_progress = 45 + int(((idx - 1) / total_presets) * 40)
            analyze_progress = 55 + int(((idx - 1) / total_presets) * 40)
            score_progress = 65 + int(((idx - 1) / total_presets) * 35)
            self._notify(progress_callback, f"Rendering {preset.name}", render_progress)
            output_path = out_dir / preset.output_name(analysis.source_path, suffix=f".{self.config.output_format}")
            render_candidate(
                input_path=analysis.source_path,
                output_path=output_path,
                ffmpeg_filter=preset.ffmpeg_filter,
                ffmpeg_binary=self.config.ffmpeg_binary,
            )
            self._notify(progress_callback, f"Measuring {preset.name}", analyze_progress)
            output_metrics = analyze_loudness(output_path, ffmpeg_binary=self.config.ffmpeg_binary)
            self._notify(progress_callback, f"Scoring {preset.name}", score_progress)
            score, reasons = score_candidate(
                metrics=output_metrics,
                cfg=scoring_cfg,
                source_metrics=analysis.metrics,
                mode=selected_mode,
            )
            bias = preset_bias.get(preset.name, 0.0)
            if abs(bias) > 0:
                score += bias
                reasons.append(f"Preference bias {bias:+.2f} from listening notes")
            results.append(
                CandidateResult(
                    preset=preset,
                    output_path=output_path,
                    source_metrics=analysis.metrics,
                    output_metrics=output_metrics,
                    score=score,
                    reasons=reasons,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        self._notify(progress_callback, "Writing session exports", 92)
        session = OptimizationSession(
            session_id=datetime.now(UTC).strftime("session-%Y%m%d-%H%M%S"),
            mode=selected_mode,
            analysis=analysis,
            candidates=results,
        )
        self._write_exports(session, out_dir)
        self._notify(progress_callback, "Optimization complete", 100)
        return session

    def _ensure_ffmpeg_available(self) -> None:
        if self._ffmpeg_checked:
            return
        assert_ffmpeg_available(self.config.ffmpeg_binary)
        self._ffmpeg_checked = True

    def _runtime_scoring_config(self, destination_profile: str, strict_true_peak: bool):
        scoring_cfg = self.config.scoring
        overrides = DESTINATION_SCORING_OVERRIDES.get(destination_profile, {})
        if overrides:
            scoring_cfg = replace(scoring_cfg, **overrides)
        if strict_true_peak:
            strict_ideal = min(scoring_cfg.ideal_true_peak_max, -1.2)
            strict_hard = min(scoring_cfg.hard_true_peak_max, -1.0)
            scoring_cfg = replace(
                scoring_cfg,
                ideal_true_peak_max=strict_ideal,
                hard_true_peak_max=strict_hard,
            )
        return scoring_cfg

    def _write_exports(self, session: OptimizationSession, output_dir: Path) -> None:
        (output_dir / "analysis.json").write_text(
            json.dumps(
                {
                    "session_id": session.session_id,
                    "mode": session.mode.value,
                    "source": session.analysis.to_dict(),
                    "candidates": [c.to_dict() for c in session.candidates],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "ranking.json").write_text(
            json.dumps(
                [
                    {
                        "rank": idx + 1,
                        "preset": result.preset.name,
                        "score": result.score,
                        "output_path": str(result.output_path),
                    }
                    for idx, result in enumerate(session.candidates)
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _notify(progress_callback: ProgressCallback | None, message: str, percent: int) -> None:
        if progress_callback is not None:
            progress_callback(message, max(0, min(percent, 100)))
