from __future__ import annotations

import json
from dataclasses import dataclass
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
HISTORY_LIMIT = 200


@dataclass(slots=True)
class EngineService:
    config: AppConfig

    def analyze_source(
        self,
        input_file: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> SourceAnalysis:
        self._notify(progress_callback, "Validating input file", 5)
        input_path = validate_input_file(input_file)
        self._notify(progress_callback, "Checking FFmpeg availability", 15)
        assert_ffmpeg_available(self.config.ffmpeg_binary)
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

    def optimize(
        self,
        input_file: str | Path,
        output_dir: str | Path,
        mode: OptimizationMode | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> OptimizationSession:
        selected_mode = mode or self.config.default_mode
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        self._notify(progress_callback, "Starting optimization session", 0)
        analysis = self.analyze_source(input_file, progress_callback=progress_callback)
        presets = select_presets_for_profile(
            profile=analysis.profile,
            mode=selected_mode,
            enabled_presets=self.config.enabled_presets,
        )
        self._notify(progress_callback, f"Selected {len(presets)} candidate presets", 45)

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
                cfg=self.config.scoring,
                source_metrics=analysis.metrics,
                mode=selected_mode,
            )
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
        self._append_session_history(session=session, output_dir=output_dir)

    @staticmethod
    def history_path() -> Path:
        return Path.home() / ".optimaster" / "session_history.jsonl"

    def _append_session_history(
        self,
        session: OptimizationSession,
        output_dir: Path,
        history_file: Path | None = None,
    ) -> None:
        history_file = history_file or self.history_path()
        history_file.parent.mkdir(parents=True, exist_ok=True)
        existing = self.load_recent_history(limit=HISTORY_LIMIT, history_file=history_file)
        best = session.best_candidate
        existing.append(
            {
                "session_id": session.session_id,
                "created_at": datetime.now(UTC).isoformat(),
                "mode": session.mode.value,
                "source_path": str(session.analysis.source_path),
                "profile": session.analysis.profile.value,
                "output_dir": str(output_dir),
                "best_candidate": best.preset.name if best else None,
                "best_score": best.score if best else None,
            }
        )
        retained = existing[-HISTORY_LIMIT:]
        with history_file.open("w", encoding="utf-8") as handle:
            for item in retained:
                handle.write(json.dumps(item) + "\n")

    @staticmethod
    def load_recent_history(limit: int = 8, history_file: Path | None = None) -> list[dict[str, object]]:
        target = history_file or EngineService.history_path()
        if not target.exists():
            return []
        rows: list[dict[str, object]] = []
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows[-max(limit, 0) :]

    @staticmethod
    def _notify(progress_callback: ProgressCallback | None, message: str, percent: int) -> None:
        if progress_callback is not None:
            progress_callback(message, max(0, min(percent, 100)))
