from __future__ import annotations

import argparse
import json
from pathlib import Path

from optimaster.config import load_config
from optimaster.errors import AppError
from optimaster.models import OptimizationMode
from optimaster.presets import BUILTIN_PRESETS
from optimaster.service import EngineService


def _batch_target_dir(output_dir: str | Path, source: Path, index: int, seen: dict[str, int]) -> Path:
    base_dir = Path(output_dir)
    stem_key = source.stem.casefold()
    count = seen.get(stem_key, 0)
    seen[stem_key] = count + 1
    suffix = f"-{index:02d}" if count > 0 else ""
    return base_dir / f"{source.stem}{suffix}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="optimaster", description="Local FFmpeg-based mastering helper")
    parser.add_argument("--config", help="Path to YAML config file", default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a source file")
    analyze.add_argument("input_file")

    sub.add_parser("presets", help="List built-in presets")

    optimize = sub.add_parser("optimize", help="Render and score multiple candidates")
    optimize.add_argument("input_file")
    optimize.add_argument("--output-dir", default="renders")
    optimize.add_argument(
        "--mode",
        choices=[mode.value for mode in OptimizationMode],
        default=None,
        help="Optimization mode: safe, balanced, or louder",
    )

    batch = sub.add_parser("optimize-batch", help="Run optimization for multiple source files")
    batch.add_argument("input_files", nargs="+", help="WAV/FLAC files to optimize")
    batch.add_argument("--output-dir", default="renders")
    batch.add_argument(
        "--mode",
        choices=[mode.value for mode in OptimizationMode],
        default=None,
        help="Optimization mode: safe, balanced, or louder",
    )

    note = sub.add_parser("add-note", help="Add a listening note and rating for a preset")
    note.add_argument("preset_name")
    note.add_argument("--rating", type=int, required=True, choices=[1, 2, 3, 4, 5])
    note.add_argument("--preferences", default="renders/preferences.json")

    return parser


def cmd_analyze(input_file: str, config_path: str | None) -> int:
    cfg = load_config(config_path)
    service = EngineService(config=cfg)
    analysis = service.analyze_source(input_file)
    print(json.dumps(analysis.to_dict(), indent=2))
    return 0


def cmd_presets() -> int:
    for preset in BUILTIN_PRESETS.values():
        print(f"- {preset.name}: {preset.description}")
        print(f"  filter: {preset.ffmpeg_filter}")
    return 0


def cmd_optimize(input_file: str, output_dir: str, mode: str | None, config_path: str | None) -> int:
    cfg = load_config(config_path)
    selected_mode = OptimizationMode(mode) if mode else cfg.default_mode
    service = EngineService(config=cfg)
    session = service.optimize(input_file=input_file, output_dir=output_dir, mode=selected_mode)

    print("\nOptiMaster ranking\n")
    for idx, result in enumerate(session.candidates, start=1):
        m = result.output_metrics
        print(
            f"{idx}. {result.preset.name} | score={result.score} | "
            f"LUFS={m.integrated_lufs} | TP={m.true_peak_dbtp} | LRA={m.lra_lu}"
        )
        print(f"   {result.output_path}")
        print(f"   reasons: {'; '.join(result.reasons)}")
    return 0


def cmd_optimize_batch(input_files: list[str], output_dir: str, mode: str | None, config_path: str | None) -> int:
    cfg = load_config(config_path)
    service = EngineService(config=cfg)
    selected_mode = OptimizationMode(mode) if mode else cfg.default_mode

    print(f"Running batch on {len(input_files)} file(s)...")
    seen_stems: dict[str, int] = {}
    for index, input_file in enumerate(input_files, start=1):
        source = Path(input_file)
        target_dir = _batch_target_dir(output_dir, source, index, seen_stems)
        session = service.optimize(input_file=source, output_dir=target_dir, mode=selected_mode)
        best = session.best_candidate.preset.name if session.best_candidate else "none"
        print(f"- {source.name}: best={best} | session={session.session_id} | output={target_dir}")
    return 0


def cmd_add_note(preset_name: str, rating: int, preferences: str, config_path: str | None) -> int:
    cfg = load_config(config_path)
    service = EngineService(config=cfg, preference_path=Path(preferences))
    path = service.add_listening_note(preset_name=preset_name, rating=rating)
    print(f"Saved listening note for {preset_name} (rating={rating}) in {path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "analyze":
            return cmd_analyze(args.input_file, args.config)
        if args.command == "presets":
            return cmd_presets()
        if args.command == "optimize":
            return cmd_optimize(args.input_file, args.output_dir, args.mode, args.config)
        if args.command == "optimize-batch":
            return cmd_optimize_batch(args.input_files, args.output_dir, args.mode, args.config)
        if args.command == "add-note":
            return cmd_add_note(args.preset_name, args.rating, args.preferences, args.config)
    except AppError as exc:
        print(str(exc))
        return 1

    parser.error("Unknown command")
    return 2
