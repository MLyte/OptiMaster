from __future__ import annotations

import json
from pathlib import Path

from optimaster.config import AppConfig
from optimaster.ffmpeg import analyze_loudness, render_candidate
from optimaster.models import CandidateResult
from optimaster.presets import get_enabled_presets
from optimaster.scoring import score_candidate


def run_pipeline(input_file: str | Path, output_dir: str | Path, config: AppConfig) -> list[CandidateResult]:
    source_path = Path(input_file)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_metrics = analyze_loudness(source_path, ffmpeg_binary=config.ffmpeg_binary)
    presets = get_enabled_presets(config.enabled_presets)

    results: list[CandidateResult] = []
    for preset in presets:
        output_path = out_dir / preset.output_name(source_path, suffix=f".{config.output_format}")
        render_candidate(
            input_path=source_path,
            output_path=output_path,
            ffmpeg_filter=preset.ffmpeg_filter,
            ffmpeg_binary=config.ffmpeg_binary,
        )
        output_metrics = analyze_loudness(output_path, ffmpeg_binary=config.ffmpeg_binary)
        score, reasons = score_candidate(output_metrics, config.scoring)
        results.append(
            CandidateResult(
                preset=preset,
                output_path=output_path,
                source_metrics=source_metrics,
                output_metrics=output_metrics,
                score=score,
                reasons=reasons,
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)

    (out_dir / "analysis.json").write_text(
        json.dumps(
            {
                "source_file": str(source_path),
                "source_metrics": source_metrics.to_dict(),
                "candidates": [r.to_dict() for r in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (out_dir / "ranking.json").write_text(
        json.dumps(
            [
                {
                    "rank": idx + 1,
                    "preset": result.preset.name,
                    "score": result.score,
                    "output_path": str(result.output_path),
                }
                for idx, result in enumerate(results)
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    return results
