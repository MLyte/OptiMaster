# OptiMaster

OptiMaster is a local audio finishing assistant for WAV and FLAC premaster files.

It analyzes a source file, renders several mastering candidates with FFmpeg, measures the results, then helps you compare and export the best version. It is designed for cautious, repeatable finishing work, not for one-click miracle mastering.

## Public Beta

This project is in beta and is meant to be tested.

Expect rough edges, especially around packaging, edge-case audio files, and UI polish. The app is useful today for local experiments, but you should still verify exports with your normal monitoring chain before release.

Good beta feedback includes:
- files that fail to analyze or render
- moments where the workflow feels unclear
- candidate choices that sound worse than expected
- confusing loudness or true-peak results
- Windows packaging and shortcut/icon issues

## What It Does

OptiMaster currently supports:
- WAV / FLAC import
- source loudness analysis with FFmpeg
- source profile diagnostics
- Safe / Balanced / Louder optimization modes
- custom target LUFS in the GUI
- strict true-peak option
- multiple rendered candidates per session
- an OptiMaster technical fallback when a custom LUFS target is too aggressive
- ranked recommendations with scoring reasons
- before / after comparison for LUFS, true peak, dynamics, and score
- A/B playback inside the GUI
- waveform preview and playback visualization
- export with clean incremental filenames
- local session history
- CLI usage for analysis, rendering, batch processing, presets, and listening notes

## What It Is Not

OptiMaster does not replace a mastering engineer.

It does not guarantee a release-ready master, does not know your creative intent, and does not judge translation on real playback systems. It gives you controlled candidates and useful measurements so you can make a better decision.

## Requirements

- Windows is the primary target right now
- Python 3.11+
- FFmpeg available on `PATH`
- A local checkout of this repository

Python dependencies are declared in [pyproject.toml](pyproject.toml). The GUI uses PySide6.

## Install From Source

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
ffmpeg -version
```

If `ffmpeg -version` fails, install FFmpeg and make sure `ffmpeg.exe` is available on `PATH`.

## Launch The App

```powershell
optimaster-gui
```

Fallback:

```powershell
python -c "from optimaster.gui import run; raise SystemExit(run())"
```

## Recommended GUI Workflow

1. Choose a WAV or FLAC premaster.
2. Analyze the source.
3. Set the mode and optional target LUFS.
4. Render candidates.
5. Compare the recommended version, your LUFS-target version, and the OptiMaster technical fallback.
6. Listen A/B.
7. Export the selected version.

Exports are suggested one folder above `renders` with incremental names such as `Track_export_01.wav`.

## CLI Quick Start

Show help:

```powershell
optimaster --help
```

Analyze a file:

```powershell
optimaster analyze "C:\path\to\track.wav"
```

Render and score candidates:

```powershell
optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Choose a mode:

```powershell
optimaster optimize "C:\path\to\track.wav" --mode safe
optimaster optimize "C:\path\to\track.wav" --mode balanced
optimaster optimize "C:\path\to\track.wav" --mode louder
```

Batch process files:

```powershell
optimaster optimize-batch "C:\path\to\a.wav" "C:\path\to\b.wav" --output-dir ".\renders"
```

List built-in presets:

```powershell
optimaster presets
```

Use a YAML config:

```powershell
optimaster --config ".\config.example.yaml" optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Add a listening note:

```powershell
optimaster add-note transparent_trim --rating 4 --preferences ".\renders\preferences.json"
```

## Outputs

Each optimization session can produce:
- rendered candidate audio files
- `analysis.json`
- `ranking.json`
- optional `preferences.json`
- waveform preview images for the GUI

The rendered candidates in `renders` are working files. Use the GUI export action for a clean final filename.

## Packaging Status

Packaging is still beta. The current Windows packaging direction is documented in [WINDOWS_PACKAGING.md](WINDOWS_PACKAGING.md).

The intended release build uses PyInstaller with the bundled OptiMaster icon:

```powershell
pyinstaller --noconfirm --windowed --name OptiMaster --icon src/optimaster/assets/optimaster_icon.ico --collect-all PySide6 src/optimaster/__main__.py
```

## Testing

Run the test suite:

```powershell
python -m pytest -q
```

On some Windows setups, pytest may fail because the default temp directory is not writable. In that case, redirect temp files into the workspace:

```powershell
$env:TEMP="C:\www\OptiMaster\.tmp2"
$env:TMP="C:\www\OptiMaster\.tmp2"
New-Item -ItemType Directory -Force -Path .tmp2 | Out-Null
python -m pytest -q --basetemp .pytest-run -p no:cacheprovider
```

## Known Beta Notes

- FFmpeg must be installed separately for source runs.
- The GUI is Windows-first and still evolving.
- Target LUFS can be pushed too high; OptiMaster now renders a technical fallback so you can compare instead of restarting.
- Loudness metrics are technical guidance, not a final listening decision.
- Session history and preferences are local files, not cloud-synced.

## License

MIT
