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

## Installation (Windows-first)

Python 3.11+ recommended.

1) Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

2) Install FFmpeg and verify it is on `PATH`:

```powershell
ffmpeg -version
```

3) Install OptiMaster in editable mode:

```powershell
python -m pip install -e .
```

The GUI dependency (`PySide6`) is included in project dependencies.

> If `pip install -e .` fails because of restricted network/proxy, use an environment
> with internet access (or an internal package mirror), then rerun the same command.

## Tutoriel — lancer l'application

### 1) Lancer le CLI

From the repository root (with your virtualenv active):

```powershell
optimaster --help
```

If entry points are not available in your shell, use module mode:

```powershell
python -m optimaster --help
```

### 2) Analyser un fichier audio

```powershell
optimaster analyze "C:\path\to\track.wav"
```

### 3) Lancer une optimisation complète

```powershell
optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Modes available:

```powershell
optimaster optimize "C:\path\to\track.wav" --mode safe
optimaster optimize "C:\path\to\track.wav" --mode balanced
optimaster optimize "C:\path\to\track.wav" --mode louder
```

### 4) Afficher les presets

```powershell
optimaster presets
```

### 5) Utiliser un fichier de config YAML

```powershell
optimaster optimize "C:\path\to\track.wav" --config ".\config.example.yaml"
```

### 6) Lancer l'application desktop (GUI)

```powershell
optimaster-gui
```

If needed, fallback to module mode:

```powershell
python -c "from optimaster.gui import run; raise SystemExit(run())"
```

Current GUI v0 includes:
- drag and drop or file picker for WAV/FLAC
- source analysis with profile and diagnostics
- Safe / Balanced / Louder mode selection
- full optimization run with progress feedback
- ranked candidate table with scoring reasons
- export of the selected rendered candidate

## Audit "install now" (snapshot: 2026-04-22)

Checks run in this repository snapshot:

- `pytest -q` fails if the package is not installed into the environment (`ModuleNotFoundError: optimaster`).
- `PYTHONPATH=src pytest -q` passes (`4 passed`).
- `PYTHONPATH=src python -m optimaster --help` works (CLI command tree is valid).
- GUI import currently fails in this container because `PySide6` is not installed.
- `ffmpeg -version` fails in this container because FFmpeg is missing from `PATH`.

Interpretation for a real Windows install **right now**:
- the codebase itself is testable and CLI-ready,
- but a fresh machine still needs the runtime prerequisites installed successfully:
  1) Python deps (`pip install -e .`),
  2) FFmpeg in `PATH`.

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
