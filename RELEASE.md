# Release Process

OptiMaster is an open source source-first project.

Compiled applications are release artifacts, not Git-tracked source files.

## Branch Model

- `main`: source code, tests, docs, packaging config.
- `codex/*`, `feature/*`, `fix/*`: short-lived work branches.
- No `compiled`, `dist`, or binary-only branch.

## Release Flow

1. Finish and test the source changes.
2. Tag the version:

   ```powershell
   git tag v2026.4.24-beta.1
   git push origin v2026.4.24-beta.1
   ```

3. GitHub Actions builds the Windows portable archive.
4. GitHub Releases receives:
   - `OptiMaster-{tag}-windows-x64.zip`
   - `SHA256SUMS.txt`

## Versioning

Use calendar-based beta tags while the app is pre-1.0:

```text
vYYYY.M.D-beta.N
```

Example:

```text
v2026.4.24-beta.1
```

## Current Beta Policy

- Windows is the first supported packaged platform.
- Linux AppImage is planned after the Windows workflow is stable.
- FFmpeg must be installed separately and available on `PATH`.
- Build outputs must not be committed to Git.
