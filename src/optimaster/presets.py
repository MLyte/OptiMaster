from __future__ import annotations

from optimaster.models import CandidatePreset


BUILTIN_PRESETS: dict[str, CandidatePreset] = {
    "transparent_trim": CandidatePreset(
        name="transparent_trim",
        description="Simple transparent gain reduction.",
        ffmpeg_filter="volume=-1.5dB",
    ),
    "safe_limit": CandidatePreset(
        name="safe_limit",
        description="Trim first, then apply a safe limiter.",
        ffmpeg_filter="volume=-2dB,alimiter=limit=-1dB",
    ),
    "sweet_spot": CandidatePreset(
        name="sweet_spot",
        description="Middle ground between transparency and safe finish.",
        ffmpeg_filter="volume=-1.7dB,alimiter=limit=-1dB",
    ),
    "gentle_glue": CandidatePreset(
        name="gentle_glue",
        description="Very light glue compression plus safe limiting.",
        ffmpeg_filter="acompressor=threshold=-6dB:ratio=1.5:attack=10:release=80,volume=-1.0dB,alimiter=limit=-1dB",
    ),
}


def get_enabled_presets(names: list[str]) -> list[CandidatePreset]:
    presets: list[CandidatePreset] = []
    for name in names:
        if name not in BUILTIN_PRESETS:
            raise KeyError(f"Unknown preset: {name}")
        presets.append(BUILTIN_PRESETS[name])
    return presets
