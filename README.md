# OptiMaster

Local audio finishing assistant for hot premaster files.

OptiMaster is a Python app that automates a prudent, reproducible finishing workflow:
- analyze an input WAV or FLAC with FFmpeg
- classify the source profile
- generate restrained finishing candidates adapted to the source
- re-analyze each candidate and score them
- recommend the most balanced result while keeping final choice human

It is intentionally modest: it does not claim to create a universal "perfect master".

## Current Scope

MVP:
- CLI first
- local only
- FFmpeg-based
- source-aware candidate selection
- Safe / Balanced / Louder modes
- analysis + scoring + export
- desktop GUI for import, analysis, ranking, playback, and export

Implemented in the current codebase:
- batch processing via `optimaster optimize-batch`
- listening notes / preference learning via `optimaster add-note`
- waveform preview in the GUI source panel
- local session history in the GUI
- A/B listening playback in the GUI

## Installation

Windows-first setup:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
ffmpeg -version
```

Requirements:
- Python 3.11+
- FFmpeg available on `PATH`

The GUI dependency `PySide6` is included in the project dependencies.

## Quick Start

Show the CLI:

```powershell
optimaster --help
```

Fallback if entry points are not available:

```powershell
python -m optimaster --help
```

Analyze a file:

```powershell
optimaster analyze "C:\path\to\track.wav"
```

Run a full optimization:

```powershell
optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Choose the mode:

```powershell
optimaster optimize "C:\path\to\track.wav" --mode safe
optimaster optimize "C:\path\to\track.wav" --mode balanced
optimaster optimize "C:\path\to\track.wav" --mode louder
```

Run batch optimization:

```powershell
optimaster optimize-batch "C:\path\to\a.wav" "C:\path\to\b.wav" --output-dir ".\renders"
```

List presets:

```powershell
optimaster presets
```

Use a YAML config:

```powershell
optimaster optimize "C:\path\to\track.wav" --config ".\config.example.yaml"
```

Launch the GUI:

```powershell
optimaster-gui
```

Fallback:

```powershell
python -c "from optimaster.gui import run; raise SystemExit(run())"
```

## GUI Features

Current GUI includes:
- drag and drop or file picker for WAV/FLAC
- source analysis with profile and diagnostics
- Safe / Balanced / Louder mode selection
- full optimization run with progress feedback
- ranked candidate table with scoring reasons
- waveform preview in the source summary
- local session history
- A/B listening playback
- listening note capture for the selected candidate
- export of the selected rendered candidate

## Validation Snapshot

Validated in this environment on April 24, 2026:
- `python -m pip install -e .`: passed
- `python -m pytest -q`: passed when temp directories were redirected away from restricted Windows temp locations
- `python -m optimaster --help`: passed
- `python -m optimaster presets`: passed
- `python -m optimaster analyze .tmp\sample.wav`: passed
- `python -m optimaster optimize .tmp\sample.wav --output-dir .tmp\renders`: passed
- `python -m optimaster optimize-batch ...`: passed
- `python -m optimaster add-note ...`: passed
- GUI import (`from optimaster.gui import MainWindow`): passed
- `ffmpeg -version`: passed

Note about `pytest` on this machine:
- some runs fail if `pytest` uses the default Windows temp directory because that temp location has permission issues
- the project tests themselves pass when `TMP` / `TEMP` and `--basetemp` are redirected to writable directories

## Built-In Logic

Default strategy:
- classify source behavior before processing
- avoid aggressive gain-up presets when the source is already hot
- prefer safer true-peak margins
- preserve dynamics when possible
- penalize unsafe true peaks
- penalize transformations that move too far from source loudness

## Outputs

OptiMaster writes:
- rendered candidate audio files
- `analysis.json`
- `ranking.json`
- optional `preferences.json`

## License

MIT
