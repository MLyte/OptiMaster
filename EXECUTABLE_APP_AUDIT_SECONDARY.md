# OptiMaster executable beta - secondary audit notes

These items are not blockers for the current UI pass, but they should be tracked before a broader public beta release.

## Post-export QA matrix

- Export the selected candidate, then start a new analysis without restarting the app.
- Export twice to confirm incremental filenames behave as expected.
- Cancel the export dialog and verify no state changes.
- Change source after rendering candidates and verify old candidates are no longer playable/exportable.
- Start a new analysis after playback is active and verify playback stops.
- Try export when the target file is locked by another app.

## Render file policy

- Clarify which files are working renders inside `renders/`.
- Clarify that the final export is copied one folder above `renders/` with an `OptiMaster_export_XX` suffix.
- Decide whether old render folders should be cleaned manually, kept forever, or managed by the app later.

## FFmpeg runtime behavior

- Document what happens when FFmpeg is missing from `PATH`.
- Decide whether the app should automatically prefer `vendor/ffmpeg/bin/ffmpeg.exe` when bundled.
- Add a GUI-level diagnostic for the resolved FFmpeg path.
- Add a packaging smoke test on a clean Windows machine.

## Windows beta edge cases

- Files locked by a DAW during analysis or export.
- Output folders without write permission.
- Very long paths and non-ASCII filenames.
- Very long tracks that make progress appear stalled.
- Missing audio codecs or unsupported media despite `.wav` / `.flac` extension.

## Release checklist

- GUI executable opens without a terminal window.
- App icon appears in the window, taskbar, shortcut, and Start menu.
- WAV import works.
- FLAC import works.
- Analyze completes.
- Render completes.
- Export completes.
- New analysis works without restarting.
- Error dialogs are user-readable in windowed mode.
