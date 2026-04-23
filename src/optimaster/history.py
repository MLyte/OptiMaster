from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from optimaster.models import OptimizationSession


@dataclass(slots=True)
class SessionHistoryEntry:
    session_id: str
    created_at: str
    source_path: str
    mode: str
    best_preset: str | None
    best_score: float | None
    output_dir: str


class SessionHistoryStore:
    def __init__(self, path: Path | None = None, max_entries: int = 25) -> None:
        default_path = Path.home() / ".optimaster" / "session_history.json"
        self.path = path or default_path
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, session: OptimizationSession, output_dir: Path) -> None:
        entries = self.read_all()
        best = session.best_candidate
        entries.insert(
            0,
            SessionHistoryEntry(
                session_id=session.session_id,
                created_at=datetime.now(tz=timezone.utc).isoformat(),
                source_path=str(session.analysis.source_path),
                mode=session.mode.value,
                best_preset=best.preset.name if best else None,
                best_score=best.score if best else None,
                output_dir=str(output_dir),
            ),
        )
        serialized = [asdict(entry) for entry in entries[: self.max_entries]]
        self.path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def read_all(self) -> list[SessionHistoryEntry]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        entries: list[SessionHistoryEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            entries.append(
                SessionHistoryEntry(
                    session_id=str(item.get("session_id", "")),
                    created_at=str(item.get("created_at", "")),
                    source_path=str(item.get("source_path", "")),
                    mode=str(item.get("mode", "")),
                    best_preset=item.get("best_preset"),
                    best_score=item.get("best_score"),
                    output_dir=str(item.get("output_dir", "")),
                )
            )
        return entries
