# OptiMaster

Assistant local de finition audio pour premaster chauds, basé sur Python + FFmpeg.

OptiMaster automatise un workflow prudent et reproductible :
- analyser un fichier WAV/FLAC
- classifier le profil de la source (très chaude, presque prête, etc.)
- générer plusieurs candidats de finition adaptés au profil
- ré-analyser chaque candidat et les scorer
- recommander le rendu le plus équilibré, en laissant la décision finale à l'humain

L'outil n'essaie pas de remplacer un ingénieur mastering : il vise une optimisation locale, mesurée et explicable.

---

## Audit de l'état actuel (22 avril 2026)

### 1) État global

**Statut : MVP fonctionnel (CLI + GUI) avec moteur métier structuré.**

Ce qui est en place et exploitable aujourd'hui :
- moteur de traitement encapsulé dans `EngineService`
- CLI opérationnelle (`analyze`, `optimize`, `presets`)
- GUI PySide6 v0 avec import, analyse, optimisation, classement et export
- scoring explicable (raisons textuelles)
- export de session en JSON (`analysis.json`, `ranking.json`)
- tests unitaires sur scoring/classification/sélection de presets

### 2) Couverture fonctionnelle réellement disponible

#### ✅ Implémenté
- Validation d'entrée (existence + formats supportés WAV/FLAC).
- Vérification de disponibilité FFmpeg.
- Analyse loudness via filtre `loudnorm=print_format=summary`.
- Classification de la source (`very_hot`, `almost_ready`, `needs_finish`, `low_dynamics`, `dynamic_ok`).
- Modes d'optimisation `safe`, `balanced`, `louder`.
- Sélection de presets selon profil source + mode utilisateur.
- Rendu de candidats via FFmpeg.
- Scoring multicritère (true peak, LUFS cible, LRA, écart à la source).
- Tri des candidats par score et recommandation du meilleur.
- Exports JSON de session et ranking.
- Interface GUI avec thread worker, barre de progression et export du candidat sélectionné.

#### ⚠️ Partiellement implémenté / à compléter
- Packaging utilisateur final (pas d'installateur ou binaire distribué prêt).
- A/B listening intégré : non disponible.
- Historique local des sessions : non disponible.
- Polissage UX/microcopies : en cours.
- Tests encore concentrés sur la logique métier (pas de tests GUI, pas de tests d'intégration FFmpeg de bout en bout).

### 3) Vérifications effectuées pendant cet audit

Contexte de vérification : environnement CI/dev sans accès Internet sortant, sans FFmpeg préinstallé.

- `PYTHONPATH=src python -m pytest -q` → **4 tests passés**.
- `PYTHONPATH=src python -m optimaster --help` → **CLI accessible**.
- `PYTHONPATH=src python -m optimaster presets` → **presets exposés correctement**.
- `ffmpeg -version` → **FFmpeg absent dans l'environnement d'audit**.
- `python -m pip install -e .` → **échec en environnement offline (dépendances build non récupérables)**.

### 4) Risques / points d'attention

- Le moteur dépend de FFmpeg sur `PATH` : sans FFmpeg, l'analyse/rendu ne peuvent pas s'exécuter.
- Les tests unitaires ne couvrent pas encore les appels FFmpeg réels ni les interactions GUI.
- En environnement offline, l'installation editable peut échouer si les dépendances ne sont pas déjà présentes en cache.
- Le positionnement produit est “assistant prudent”, ce qui est cohérent ; la doc doit continuer à éviter tout wording de mastering “magique”.

### 5) Priorités recommandées (ordre court terme)

1. Ajouter un jeu minimal de tests d'intégration moteur (avec mock FFmpeg ou fixture audio).
2. Ajouter tests de non-régression CLI (au moins `analyze`/`optimize` sur fixtures).
3. Finaliser microcopies GUI + états d'erreur utilisateur.
4. Mettre en place stratégie de packaging Windows (PyInstaller ou Nuitka) + procédure de release.
5. Préparer un petit corpus audio de validation produit.

---

## Portée actuelle

MVP :
- CLI first
- local only
- FFmpeg-based
- sélection des candidats selon le profil source
- modes Safe / Balanced / Louder
- analyse + scoring + export
- GUI desktop v0 (import, analyse, ranking, export)

Prévu plus tard :
- batch processing
- notes d'écoute / apprentissage des préférences
- preview waveform

## Installation

Python 3.11+ recommandé.

```bash
pip install -e .
```

Si vous êtes en environnement hors-ligne, l'installation peut échouer si les dépendances ne sont pas déjà disponibles localement.

FFmpeg doit être disponible sur `PATH`.
La GUI nécessite `PySide6` (déclaré dans les dépendances du projet).

Vérification :
```bash
ffmpeg -version
```

## Démarrage rapide

Analyser un fichier :

```bash
optimaster analyze "C:\path\to\track.wav"
```

Lancer la pipeline complète :

```bash
optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"
```

Choisir le mode :

```bash
optimaster optimize "C:\path\to\track.wav" --mode safe
optimaster optimize "C:\path\to\track.wav" --mode balanced
optimaster optimize "C:\path\to\track.wav" --mode louder
```

Lister les presets :

```bash
optimaster presets
```

Utiliser un fichier YAML de config :

```bash
optimaster optimize "C:\path\to\track.wav" --config ".\config.example.yaml"
```

Lancer la GUI :

```bash
optimaster-gui
```

## Sorties générées

OptiMaster écrit :
- rendus WAV/FLAC des candidats
- `analysis.json`
- `ranking.json`

## Licence

MIT
