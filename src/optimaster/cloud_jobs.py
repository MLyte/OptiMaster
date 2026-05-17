from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AiMasteringJob:
    mastering_id: int
    source_path: str
    output_path: str
    output_dir: str
    mode: str
    target_lufs: float
    output_format: str
    status: str
    progress: int
    message: str
    created_at: str
    output_audio_id: int | None = None


class AiMasteringJobStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".optimaster" / "aimastering_jobs.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, job: AiMasteringJob) -> None:
        jobs = [item for item in self.read_all() if item.mastering_id != job.mastering_id]
        jobs.insert(0, job)
        self._write(jobs)

    def read_all(self) -> list[AiMasteringJob]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        jobs: list[AiMasteringJob] = []
        for item in raw:
            if isinstance(item, dict):
                jobs.append(self._from_dict(item))
        return jobs

    def update(self, updated: AiMasteringJob) -> None:
        jobs = [updated if item.mastering_id == updated.mastering_id else item for item in self.read_all()]
        self._write(jobs)

    def _write(self, jobs: list[AiMasteringJob]) -> None:
        self.path.write_text(json.dumps([asdict(job) for job in jobs], indent=2), encoding="utf-8")

    def _from_dict(self, item: dict[str, Any]) -> AiMasteringJob:
        return AiMasteringJob(
            mastering_id=int(item.get("mastering_id", 0)),
            source_path=str(item.get("source_path", "")),
            output_path=str(item.get("output_path", "")),
            output_dir=str(item.get("output_dir", "")),
            mode=str(item.get("mode", "")),
            target_lufs=float(item.get("target_lufs", -12.0)),
            output_format=str(item.get("output_format", "wav")),
            status=str(item.get("status", "waiting")),
            progress=int(item.get("progress", 0)),
            message=str(item.get("message", "")),
            created_at=str(item.get("created_at", datetime.now(tz=timezone.utc).isoformat())),
            output_audio_id=item.get("output_audio_id"),
        )
