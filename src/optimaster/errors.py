from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    details: str | None = None

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message}: {self.details}"
        return f"[{self.code}] {self.message}"


class InputFileError(AppError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(code="input_file_error", message=message, details=details)


class FfmpegNotAvailableError(AppError):
    def __init__(self, details: str | None = None):
        super().__init__(
            code="ffmpeg_not_available",
            message="FFmpeg is not available on PATH or not executable",
            details=details,
        )


class FfmpegExecutionError(AppError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(code="ffmpeg_execution_error", message=message, details=details)


class LoudnessParseError(AppError):
    def __init__(self, details: str | None = None):
        super().__init__(
            code="loudness_parse_error",
            message="Could not parse FFmpeg loudness output",
            details=details,
        )
