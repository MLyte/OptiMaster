import json
from pathlib import Path

from optimaster.config import load_config
from optimaster.models import (
    CandidatePreset,
    CandidateResult,
    LoudnessMetrics,
    OptimizationMode,
    OptimizationSession,
    SourceAnalysis,
    SourceProfile,
)
from optimaster.service import EngineService, HISTORY_LIMIT


def _build_session(session_id: str) -> OptimizationSession:
    metrics = LoudnessMetrics(
        integrated_lufs=-11.0,
        true_peak_dbtp=-1.0,
        lra_lu=7.0,
        threshold_lufs=-21.0,
    )
    analysis = SourceAnalysis(
        source_path=Path("/tmp/source.wav"),
        metrics=metrics,
        profile=SourceProfile.DYNAMIC_OK,
        diagnostics=["ok"],
    )
    preset = CandidatePreset(name="safe_limit", description="safe", ffmpeg_filter="alimiter")
    candidate = CandidateResult(
        preset=preset,
        output_path=Path("/tmp/render.wav"),
        source_metrics=metrics,
        output_metrics=metrics,
        score=88.5,
        reasons=["safe zone"],
    )
    return OptimizationSession(
        session_id=session_id,
        mode=OptimizationMode.BALANCED,
        analysis=analysis,
        candidates=[candidate],
    )


def test_append_and_load_history(tmp_path):
    service = EngineService(config=load_config(None))
    history_file = tmp_path / "session_history.jsonl"

    service._append_session_history(_build_session("session-1"), output_dir=tmp_path, history_file=history_file)

    rows = service.load_recent_history(limit=8, history_file=history_file)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "session-1"
    assert rows[0]["best_candidate"] == "safe_limit"


def test_history_limit_is_respected(tmp_path):
    history_file = tmp_path / "session_history.jsonl"
    for idx in range(HISTORY_LIMIT + 5):
        with history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"session_id": f"session-{idx}"}) + "\n")

    rows = EngineService.load_recent_history(limit=HISTORY_LIMIT, history_file=history_file)
    assert len(rows) == HISTORY_LIMIT
    assert rows[0]["session_id"] == "session-5"
