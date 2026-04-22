from __future__ import annotations

import argparse
import json
from pathlib import Path

from optimaster.config import load_config
from optimaster.errors import AppError
from optimaster.models import OptimizationMode
from optimaster.pipeline import run_pipeline
from optimaster.presets import BUILTIN_PRESETS
from optimaster.service import EngineService


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
    results = run_pipeline(input_file=input_file, output_dir=output_dir, config=cfg, mode=selected_mode)

    print("\nOptiMaster ranking\n")
    for idx, result in enumerate(results, start=1):
        m = result.output_metrics
        print(
            f"{idx}. {result.preset.name} | score={result.score} | "
            f"LUFS={m.integrated_lufs} | TP={m.true_peak_dbtp} | LRA={m.lra_lu}"
        )
        print(f"   {result.output_path}")
        print(f"   reasons: {'; '.join(result.reasons)}")
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
    except AppError as exc:
        print(str(exc))
        return 1

    parser.error("Unknown command")
    return 2
