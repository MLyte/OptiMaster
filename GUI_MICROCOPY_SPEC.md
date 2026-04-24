# OptiMaster - Spécification microcopies GUI (MVP)

Ce document formalise les microcopies du MVP desktop (PySide6).
Objectif: ton clair, rassurant, orienté "assistant prudent" et non "mastering magique".

## Principes de rédaction
- Dire à l'utilisateur ce qui se passe maintenant.
- Expliquer l'action suivante attendue.
- Utiliser un vocabulaire concret audio (analyse, rendu, export).
- Eviter les promesses absolues.

## Etats principaux

### Etat vide (au lancement)
- Hero: `Drop a WAV or FLAC premaster here`
- Sous-texte:
  `Analyze your source, run careful finishing passes,
  then review and export the best candidate.`
- Statut: `Ready. Choose a source file to begin.`

### Fichier sélectionné
- Statut: `Source selected. Run analysis or optimization when ready.`

### Analyse en cours
- Statut progressif (moteur): messages techniques du worker.

### Analyse terminée
- Statut: `Analysis complete. You can now run optimization.`
- Diagnostic source par défaut si vide:
  `Run analysis to inspect source profile and safety checks.`

### Optimisation en cours
- Statut progressif (moteur): messages techniques du worker.

### Optimisation terminée
- Statut: `Optimization complete. Review ranking and export your preferred render.`
- Détails candidat:
  - Placeholder: `Candidate details and scoring reasons appear here.`
  - Sans candidat: `No candidate available.`

### Erreur
- Statut: `Task failed. Check the error dialog for details.`
- Erreurs de précondition:
  - `Choose a WAV or FLAC file first.`
  - `Select a rendered candidate before exporting.`

### Export
- Dialogue succès:
  - Titre: `Export complete`
  - Message: `Copied <preset> to: <destination>`

## Libellés de sections
- Session
- Controls
- Source analysis
- Recommended candidate
- Top candidates

## Boutons
- Choose file
- Choose output
- Load config
- Analyze source
- Run optimization
- Export selected candidate

## Validation future (post-MVP)
- Ajouter variantes FR/EN localisées.
- Tester compréhension des messages sur un panel beta.
- Uniformiser le niveau de détail des messages d'erreur FFmpeg.
