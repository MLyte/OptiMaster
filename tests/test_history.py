from pathlib import Path

from optimaster.history import SessionHistoryStore
from optimaster.models import (
    CandidatePreset,
    CandidateResult,
    LoudnessMetrics,
    OptimizationMode,
    OptimizationSession,
    SourceAnalysis,
    SourceProfile,
)


def _session(session_id: str = "sess-1") -> OptimizationSession:
    source_metrics = LoudnessMetrics(-12.0, -1.2, 6.5, -22.0)
    output_metrics = LoudnessMetrics(-10.0, -1.0, 5.9, -20.0)
    preset = CandidatePreset("safe_plus", "Safe finishing", "alimiter")
    candidate = CandidateResult(
        preset=preset,
        output_path=Path("/tmp/render.wav"),
        source_metrics=source_metrics,
        output_metrics=output_metrics,
        score=84.2,
        reasons=["Good true peak margin"],
    )
    analysis = SourceAnalysis(
        source_path=Path("/tmp/source.wav"),
        metrics=source_metrics,
        profile=SourceProfile.ALMOST_READY,
        diagnostics=["Source is already controlled."],
    )
    return OptimizationSession(
        session_id=session_id,
        mode=OptimizationMode.BALANCED,
        analysis=analysis,
        candidates=[candidate],
    )


def test_session_history_append_and_read(tmp_path: Path) -> None:
    history_path = tmp_path / "history.json"
    store = SessionHistoryStore(path=history_path, max_entries=3)
    store.append(_session("sess-1"), tmp_path)

    entries = store.read_all()
    assert len(entries) == 1
    assert entries[0].session_id == "sess-1"
    assert entries[0].best_preset == "safe_plus"
    assert entries[0].mode == "balanced"


def test_session_history_max_entries(tmp_path: Path) -> None:
    history_path = tmp_path / "history.json"
    store = SessionHistoryStore(path=history_path, max_entries=2)
    store.append(_session("sess-1"), tmp_path)
    store.append(_session("sess-2"), tmp_path)
    store.append(_session("sess-3"), tmp_path)

    entries = store.read_all()
    assert [entry.session_id for entry in entries] == ["sess-3", "sess-2"]
