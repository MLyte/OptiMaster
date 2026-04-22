# OptiMaster

Local audio finishing assistant for hot premaster files.

OptiMaster is a small Python app that automates the workflow we tested manually:
- analyze an input WAV/FLAC with FFmpeg
- generate several safe mastering candidates
- re-analyze each candidate
- score them
- recommend the most balanced result

It is intentionally modest: it does **not** pretend to create a universal "perfect master".
It helps you find the best local, safe, repeatable finishing pass for a given export.

## Current scope

MVP:
- CLI first
- local only
- FFmpeg-based
- configurable presets
- analysis + scoring + export

Planned later:
- small desktop GUI
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
├── pyproject.toml
├── .gitignore
├── config.example.yaml
├── src/
│   └── optimaster/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── ffmpeg.py
│       ├── presets.py
│       ├── scoring.py
│       └── pipeline.py
├── scripts/
│   └── bootstrap.ps1
└── tests/
    └── test_scoring.py
```

## Installation

Python 3.11+ recommended.

```bash
pip install -e .
```

FFmpeg must be available on `PATH`.

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

Show the built-in presets:

```bash
optimaster presets
```

Use a YAML config:

```bash
optimaster optimize "C:\path\to\track.wav" --config ".\config.example.yaml"
```

## Built-in logic

The default strategy is:
- if the source file is already hot, avoid aggressive gain-up presets
- if true peak is too close to zero, prefer trim / safe limit presets
- preserve dynamics when LRA is already healthy
- penalize outputs with unsafe true peaks
- prefer outputs that remain musically close to the source

## Example outputs

OptiMaster writes:
- rendered candidate WAV files
- `analysis.json`
- `ranking.json`

## Suggested name

**OptiMaster** works well:
- short
- clear
- sounds like a utility, not fake magic
- good fit for a CLI and a GUI later

## License

MIT
