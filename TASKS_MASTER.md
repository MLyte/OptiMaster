# TASKS_MASTER - Production execution backlog

Ce document est derive de `PROJECT_PRODUCTION_PLAN.md` et sert de suivi executable du projet.

## Legende
- [x] termine
- [~] en cours
- [ ] a faire

## Phase 0 - Cadrage produit
- [x] Positionnement produit clarifie dans la documentation principale (`README.md` + plan produit).
- [x] Scope MVP confirme: Windows desktop local-first, sans compte, sans cloud.
- [~] Microcopies UI utilisateur a formaliser dans une spec dediee GUI.

## Phase 1 - Durcissement du moteur
- [x] Separation moteur/CLI via une couche de service (`EngineService`).
- [x] Introduction d'erreurs applicatives structurees (`AppError`, erreurs FFmpeg/input/parse).
- [x] Validation d'entree explicite (existence et formats supportes WAV/FLAC).
- [x] Modeles metier enrichis (`SourceAnalysis`, `OptimizationSession`, `OptimizationMode`, `SourceProfile`).
- [x] Pipeline conserve mais encapsule autour du service layer.
- [x] Tests unitaires enrichis sur classification/scoring/selection de presets.

## Phase 2 - Automatisation mastering V1
- [x] Classification de source introduite (`classify_source`).
- [x] Table de decision profile + mode -> presets introduite (`select_presets_for_profile`).
- [x] Modes utilisateur ajoutes cote CLI/config (`safe`, `balanced`, `louder`).
- [x] Scoring ameliore avec comparaison a la source (agressivite + dynamique).
- [x] Raisons textuelles de scoring enrichies pour diagnostics utilisateur.

## Phase 3 - GUI PySide6 MVP
- [x] Creer le squelette de l'application PySide6 (fenetre principale + worker thread).
- [x] Implementer le parcours complet import -> analyse -> optimisation -> top 3 -> export.
- [x] Ajouter gestion d'etats UI: vide, analyse en cours, optimisation en cours, erreurs.
- [~] Affiner la hierarchie visuelle, les microcopies et le polish de l'interface.

## Phase 4 - Finitions d'usage
- [x] A/B listening basique (notes d'ecoute + notation).
- [x] Historique local leger des sessions (preferences JSON).
- [x] Ameliorations visuelles et microcopies (preview waveform + controles GUI).

## Phase 5 - Packaging Windows
- [ ] Decider PyInstaller vs Nuitka (benchmark demarrage + taille binaire).
- [ ] Integration et verification FFmpeg bundle.
- [ ] Procedure build/release reproductible.

## Phase 6 - QA/Beta/1.0
- [ ] Definir corpus audio de validation.
- [ ] Executer matrice de tests manuels sur parcours principal.
- [ ] Ajuster scoring/presets d'apres retours pilote.
- [ ] Preparer release candidate et 1.0.
