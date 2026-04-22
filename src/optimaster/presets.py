from __future__ import annotations

from optimaster.models import CandidatePreset, OptimizationMode, SourceProfile


BUILTIN_PRESETS: dict[str, CandidatePreset] = {
    "do_almost_nothing": CandidatePreset(
        name="do_almost_nothing",
        description="Minimal trim for already good sources.",
        ffmpeg_filter="volume=-0.8dB",
        families=(SourceProfile.ALMOST_READY, SourceProfile.TOUCH_MINIMALLY),
    ),
    "transparent_trim": CandidatePreset(
        name="transparent_trim",
        description="Simple transparent gain reduction.",
        ffmpeg_filter="volume=-1.5dB",
        families=(SourceProfile.VERY_HOT, SourceProfile.TOUCH_MINIMALLY, SourceProfile.NEEDS_FINISH),
    ),
    "safe_limit": CandidatePreset(
        name="safe_limit",
        description="Trim first, then apply a safe limiter.",
        ffmpeg_filter="volume=-2dB,alimiter=limit=-1dB",
        families=(SourceProfile.VERY_HOT, SourceProfile.NEEDS_FINISH, SourceProfile.DYNAMIC_OK),
    ),
    "sweet_spot": CandidatePreset(
        name="sweet_spot",
        description="Middle ground between transparency and safe finish.",
        ffmpeg_filter="volume=-1.7dB,alimiter=limit=-1dB",
        families=(SourceProfile.NEEDS_FINISH, SourceProfile.DYNAMIC_OK),
    ),
    "gentle_glue": CandidatePreset(
        name="gentle_glue",
        description="Very light glue compression plus safe limiting.",
        ffmpeg_filter="acompressor=threshold=-6dB:ratio=1.5:attack=10:release=80,volume=-1.0dB,alimiter=limit=-1dB",
        families=(SourceProfile.NEEDS_FINISH, SourceProfile.LOW_DYNAMICS),
    ),
}


MODE_PRESET_ORDER: dict[OptimizationMode, tuple[str, ...]] = {
    OptimizationMode.SAFE: ("do_almost_nothing", "transparent_trim", "safe_limit"),
    OptimizationMode.BALANCED: (
        "do_almost_nothing",
        "transparent_trim",
        "safe_limit",
        "sweet_spot",
        "gentle_glue",
    ),
    OptimizationMode.LOUDER: ("transparent_trim", "safe_limit", "sweet_spot", "gentle_glue"),
}


def get_enabled_presets(names: list[str]) -> list[CandidatePreset]:
    presets: list[CandidatePreset] = []
    for name in names:
        if name not in BUILTIN_PRESETS:
            raise KeyError(f"Unknown preset: {name}")
        presets.append(BUILTIN_PRESETS[name])
    return presets


def select_presets_for_profile(
    profile: SourceProfile,
    mode: OptimizationMode,
    enabled_presets: list[str],
) -> list[CandidatePreset]:
    selected: list[CandidatePreset] = []
    enabled_set = set(enabled_presets)
    for preset_name in MODE_PRESET_ORDER[mode]:
        if preset_name not in enabled_set:
            continue
        preset = BUILTIN_PRESETS[preset_name]
        if not preset.families or profile in preset.families:
            selected.append(preset)
    if selected:
        return selected

    # Fallback if no direct profile match
    return [BUILTIN_PRESETS[name] for name in MODE_PRESET_ORDER[mode] if name in enabled_set]
