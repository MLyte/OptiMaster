from __future__ import annotations

from pathlib import Path

from optimaster.config import AppConfig
from optimaster.models import CandidateResult, OptimizationMode
from optimaster.service import EngineService


def run_pipeline(
    input_file: str | Path,
    output_dir: str | Path,
    config: AppConfig,
    mode: OptimizationMode | None = None,
) -> list[CandidateResult]:
    service = EngineService(config=config)
    session = service.optimize(input_file=input_file, output_dir=output_dir, mode=mode)
    return session.candidates
