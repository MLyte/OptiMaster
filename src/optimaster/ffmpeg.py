from __future__ import annotations

import re
import subprocess
from pathlib import Path

from optimaster.errors import (
    FfmpegExecutionError,
    FfmpegNotAvailableError,
    InputFileError,
    LoudnessParseError,
)
from optimaster.models import LoudnessMetrics


SUMMARY_RE = {
    "integrated": re.compile(r"Input Integrated:\s+(-?\d+(?:\.\d+)?)\s+LUFS"),
    "true_peak": re.compile(r"Input True Peak:\s+([+-]?\d+(?:\.\d+)?)\s+dBTP"),
    "lra": re.compile(r"Input LRA:\s+(-?\d+(?:\.\d+)?)\s+LU"),
    "threshold": re.compile(r"Input Threshold:\s+(-?\d+(?:\.\d+)?)\s+LUFS"),
}

SUPPORTED_EXTENSIONS = {".wav", ".flac"}


def _subprocess_window_options() -> dict[str, object]:
    if not hasattr(subprocess, "STARTUPINFO"):
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        **_subprocess_window_options(),
    )


def validate_input_file(file_path: str | Path) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise InputFileError(message="Input file does not exist", details=str(path))
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise InputFileError(
            message="Unsupported input format",
            details=f"{path.suffix} (supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))})",
        )
    return path


def assert_ffmpeg_available(ffmpeg_binary: str) -> None:
    result = _run([ffmpeg_binary, "-version"])
    if result.returncode != 0:
        raise FfmpegNotAvailableError(details=(result.stderr or result.stdout).strip())


def analyze_loudness(file_path: str | Path, ffmpeg_binary: str = "ffmpeg") -> LoudnessMetrics:
    path = validate_input_file(file_path)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "loudnorm=print_format=summary",
        "-f",
        "null",
        "NUL" if path.drive else "/dev/null",
    ]
    result = _run(cmd)
    text = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0:
        raise FfmpegExecutionError(message="FFmpeg analysis failed", details=text.strip())

    def extract(name: str) -> float:
        match = SUMMARY_RE[name].search(text)
        if not match:
            raise LoudnessParseError(details=text.strip())
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
    input_validated = validate_input_file(input_path)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-y",
        "-i",
        str(input_validated),
        "-af",
        ffmpeg_filter,
        str(output_path),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise FfmpegExecutionError(message="FFmpeg render failed", details=(result.stderr or result.stdout).strip())


def render_waveform_preview(
    input_path: str | Path,
    output_path: str | Path,
    ffmpeg_binary: str = "ffmpeg",
) -> Path:
    input_validated = validate_input_file(input_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-y",
        "-i",
        str(input_validated),
        "-filter_complex",
        "showwavespic=s=1180x180:colors=0x1f8f7b",
        "-frames:v",
        "1",
        str(destination),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise FfmpegExecutionError(
            message="FFmpeg waveform preview failed",
            details=(result.stderr or result.stdout).strip(),
        )
    return destination
