# Packaging Windows - Decision log (Phase 5)

## 1) Decision: PyInstaller retenu pour la V1

Decision prise le **22 avril 2026** pour OptiMaster V1:

- **PyInstaller** retenu pour le packaging initial.
- **Nuitka** garde en option d'optimisation future.

### Pourquoi ce choix

- cycle de mise en place plus court pour une release 1.0
- meilleur ratio simplicite / fiabilite pour livrer vite
- moins de friction pour embarquer des ressources externes (FFmpeg + presets + docs)

## 2) FFmpeg bundle - strategie

Le build Windows doit embarquer:

- `ffmpeg.exe`
- `ffprobe.exe`

Convention recommandee:

- dossier runtime: `vendor/ffmpeg/bin/`
- fallback au `PATH` systeme si non present

Verification minimum post-build:

1. lancer l'app sur une machine Windows "propre"
2. confirmer que `ffmpeg -version` et `ffprobe -version` sont detectables via l'app
3. executer une analyse puis une optimisation complete
4. verifier que `analysis.json` et `ranking.json` sont produits

## 3) Procedure build/release reproductible

### Pre-requis

- Python 3.11+
- dependances du projet installees
- PyInstaller installe

### Commandes

```bash
python -m pip install -e .
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name OptiMaster --collect-all PySide6 src/optimaster/__main__.py
```

### Checklist release

1. nettoyer `dist/` et `build/`
2. rebuild complet
3. test smoke:
   - ouverture GUI
   - import WAV/FLAC
   - analyse
   - optimisation
   - export
4. archiver `dist/OptiMaster/` en zip versionne
5. publier notes de version et hash du zip
