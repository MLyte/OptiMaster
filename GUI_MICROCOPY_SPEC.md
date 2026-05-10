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
- En plus du pourcentage, afficher une liste d'etapes avec diodes:
  fichier audio, moteur audio, mesure source, profil source, pret.

### Analyse terminée
- Statut: `Analysis complete. You can now run optimization.`
- Diagnostic source par défaut si vide:
  `Run analysis to inspect source profile and safety checks.`

### Optimisation en cours
- Statut progressif (moteur): messages techniques du worker.
- En plus du pourcentage, afficher une liste d'etapes avec diodes:
  preparation, rendu candidats, mesure versions, score technique, fichiers session, pret A/B.

### Optimisation terminée
- Statut: `Rendering complete. Review the recommended version.`
- Détails candidat:
  - Hint: `Recommended version is selected. Compare it in A/B, or click another row to change it.`
  - CTA suivant: `Compare in A/B`
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
  - Suite: `Export complete. Start a new analysis when you are ready.`

## Hiérarchie d'action
- `stepAction`: action dominante de l'étape courante (analyser, créer les passes).
- `primaryAction`: action finale uniquement (export).
- Les aides (`storyLabel`, `statusHint`, `renderStatus`) restent discrètes pour ne pas concurrencer le CTA.
- L'export final vit dans l'écran A/B, pas dans l'étape de choix des versions.
- L'utilisateur peut choisir n'importe quelle version B dans l'écran A/B, la comparer à A, puis exporter cette version.
- Dans le tableau Versions, double-clic ou Entrée sur une ligne ouvre l'étape A/B.
- L'étape Versions sert à choisir dans la liste scorée; l'étape A/B sert à comparer et télécharger.

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
