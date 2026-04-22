from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from optimaster.models import LoudnessMetrics


SUMMARY_RE = {
    "integrated": re.compile(r"Input Integrated:\s+(-?\d+(?:\.\d+)?)\s+LUFS"),
    "true_peak": re.compile(r"Input True Peak:\s+([+-]?\d+(?:\.\d+)?)\s+dBTP"),
    "lra": re.compile(r"Input LRA:\s+(-?\d+(?:\.\d+)?)\s+LU"),
    "threshold": re.compile(r"Input Threshold:\s+(-?\d+(?:\.\d+)?)\s+LUFS"),
}


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_ffmpeg_available(ffmpeg_binary: str) -> None:
    result = _run([ffmpeg_binary, "-version"])
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg not available: {result.stderr or result.stdout}".strip())


def analyze_loudness(file_path: str | Path, ffmpeg_binary: str = "ffmpeg") -> LoudnessMetrics:
    path = str(file_path)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-nostats",
        "-i",
        path,
        "-af",
        "loudnorm=print_format=summary",
        "-f",
        "null",
        "NUL" if Path(path).drive else "/dev/null",
    ]
    result = _run(cmd)
    text = f"{result.stdout}\n{result.stderr}"

    def extract(name: str) -> float:
        match = SUMMARY_RE[name].search(text)
        if not match:
            raise RuntimeError(f"Could not parse {name} from FFmpeg output:\n{text}")
        return float(match.group(1))

    return LoudnessMetrics(
        integrated_lufs=extract("integrated"),
        true_peak_dbtp=extract("true_peak"),
        lra_lu=extract("lra"),
        threshold_lufs=extract("threshold"),
    )


def render_candidate(
    input_path: str | Path,
    output_path: str | Path,
    ffmpeg_filter: str,
    ffmpeg_binary: str = "ffmpeg",
) -> None:
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-af",
        ffmpeg_filter,
        str(output_path),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed:\n{result.stderr or result.stdout}")
