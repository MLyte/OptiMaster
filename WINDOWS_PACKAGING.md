# Windows Packaging

OptiMaster uses PyInstaller for the first public beta builds.

The repository stays source-only: do not commit `dist/`, `build/`, `.spec`, `.zip`, or `.exe` files. Windows executables are generated from Git tags by GitHub Actions and attached to GitHub Releases.

## Release Output

The Windows beta release produces a portable archive:

```text
OptiMaster-{tag}-windows-x64.zip
```

Inside the archive, users launch:

```text
OptiMaster.exe
```

## FFmpeg Strategy

For the first beta release, FFmpeg is not bundled.

Users must install FFmpeg separately and make sure `ffmpeg.exe` and `ffprobe.exe` are available on `PATH`. Bundling FFmpeg can be revisited later as a dedicated packaging task because it adds distribution, size, and maintenance considerations.

## Local Build Command

Install dependencies:

```powershell
python -m pip install -e .
python -m pip install pyinstaller
```

Build the GUI executable:

```powershell
pyinstaller --noconfirm --windowed --name OptiMaster --icon src/optimaster/assets/optimaster_icon.ico --collect-all PySide6 --hidden-import optimaster.assets --collect-data optimaster --add-data "src/optimaster/assets;optimaster/assets" src/optimaster/gui.py
```

Important: `src/optimaster/__main__.py` launches the CLI. The Windows GUI executable must build from `src/optimaster/gui.py`.
The `optimaster/assets` data must be bundled too, otherwise the frozen app cannot load its icon at startup.

## Release Checklist

1. Run the test suite.
2. Create a tag such as `v2026.4.24-beta.1`.
3. Let GitHub Actions build the Windows archive.
4. Download the release archive on Windows.
5. Smoke test:
   - open `OptiMaster.exe`
   - import a WAV or FLAC file
   - analyze the source
   - create versions
   - listen A/B
   - export the final file
   - start a new analysis without restarting the app
6. Check that the app icon appears on the executable.
7. Publish release notes and the generated checksum.
