# OptiMaster

Local audio finishing assistant for hot premaster files.

OptiMaster is a Python app that automates a prudent, reproducible finishing workflow:
- analyze an input WAV/FLAC with FFmpeg
- classify the source profile (very hot, almost ready, etc.)
- generate restrained mastering candidates adapted to the profile
- re-analyze each candidate and score them
- recommend the most balanced result while keeping final choice human

It is intentionally modest: it does **not** pretend to create a universal "perfect master".
It helps you find the best local, safe, repeatable finishing pass for a given export.

## Current scope

MVP:
- CLI first
- local only
- FFmpeg-based
- source-aware candidate selection
- Safe / Balanced / Louder modes
- analysis + scoring + export
- desktop GUI v0 for import, analysis, ranking, and export

Planned later:
- batch processing
- listening notes / preference learning
- waveform preview

## Why this project exists

Some exports are already very hot. Heavy automatic mastering can create pumping, unstable balance,
and ugly true peaks. OptiMaster instead tries a few restrained chains and picks the best candidate
using measurable rules.

## Project structure

```text
OptiMaster/
├── README.md
├── PROJECT_PRODUCTION_PLAN.md
├── TASKS_MASTER.md
├── pyproject.toml
├── config.example.yaml
├── src/
│   └── optimaster/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── errors.py
│       ├── ffmpeg.py
│       ├── gui.py
│       ├── models.py
│       ├── pipeline.py
│       ├── presets.py
│       ├── scoring.py
│       └── service.py
└── tests/
    └── test_scoring.py
```

## Installation

Python 3.11+ recommended.

```bash
pip install -e .
```

FFmpeg must be available on `PATH`.
The GUI also requires `PySide6`, which is included in the project dependencies.

Test:
```bash
ffmpeg -version
```

## Quick start

Analyze a file:

```bash
optimaster analyze "C:\path\to\track.wav"
```

Run the full optimization pipeline:

```bash
optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Choose the optimization mode:

```bash
optimaster optimize "C:\path\to\track.wav" --mode safe
optimaster optimize "C:\path\to\track.wav" --mode balanced
optimaster optimize "C:\path\to\track.wav" --mode louder
```

Show the built-in presets:

```bash
optimaster presets
```

Use a YAML config:

```bash
optimaster optimize "C:\path\to\track.wav" --config ".\config.example.yaml"
```

Launch the desktop GUI:

```bash
optimaster-gui
```

Current GUI v0 includes:
- drag and drop or file picker for WAV/FLAC
- source analysis with profile and diagnostics
- Safe / Balanced / Louder mode selection
- full optimization run with progress feedback
- ranked candidate table with scoring reasons
- export of the selected rendered candidate

## Built-in logic

The default strategy is:
- classify source behavior before processing
- if the source file is already hot, avoid aggressive gain-up presets
- if true peak is too close to zero, prefer trim / safe limit presets
- preserve dynamics when LRA is already healthy
- penalize outputs with unsafe true peaks
- penalize transformations too far from source loudness

## Example outputs

OptiMaster writes:
- rendered candidate WAV files
- `analysis.json`
- `ranking.json`

## License

MIT
