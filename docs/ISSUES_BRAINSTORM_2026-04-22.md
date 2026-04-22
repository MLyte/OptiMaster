# Réunion multi-agents — Brainstorming état actuel OptiMaster

**Date**: 22 avril 2026  
**Format**: revue du code + brainstorming structuré (produit, audio, QA, DX, GUI, packaging)  
**Objectif**: identifier les fonctionnalités manquantes et les manques de rigueur/justesse à transformer en issues actionnables.

---

## 1) Participants simulés et angle d'analyse

- **Agent Produit**: valeur utilisateur, priorisation MVP.
- **Agent Audio**: cohérence loudness/scoring/presets.
- **Agent Backend**: robustesse service/pipeline/erreurs.
- **Agent GUI/UX**: usage réel desktop, clarté et feedback.
- **Agent QA**: couverture tests et non-régression.
- **Agent Release/Packaging**: prêt Windows, distribution.

---

## 2) Constat global

### Points forts confirmés

1. Le projet a une base claire (CLI + service + GUI) et une proposition de valeur prudente bien alignée avec la documentation.
2. La classification source + sélection de presets par mode existe déjà et est lisible.
3. Le scoring compare sortie et source (pas uniquement une cible absolue), ce qui améliore la prudence.

### Faiblesses majeures observées

1. **Rigueur QA insuffisante**: très peu de tests, essentiellement scoring.
2. **Robustesse partielle** du pipeline face aux échecs de rendu preset (pas de mode « best effort » explicite).
3. **Validation config incomplète** (formats, presets inconnus, garde-fous incohérences de seuils).
4. **Manques produit V1 déjà identifiés mais non implémentés**: A/B listening, historique local.
5. **Packaging/release Windows** encore non cadré techniquement.

---

## 3) Décisions de la réunion (issues à créer)

> Priorité: P0 = critique, P1 = important, P2 = amélioration.

## ISSUE-01 (P0) — Couverture de tests insuffisante sur les parcours critiques

**Problème**  
Les tests ne couvrent presque que `scoring`/`presets`. Les couches FFmpeg, service, exports JSON, erreurs et flux GUI ne sont pas sécurisées par des tests ciblés.

**Impact**  
Risque élevé de régression silencieuse sur l’orchestration réelle.

**Décision**  
Créer une suite de tests en 3 niveaux:
- unitaires purs (classification, scoring, config validation),
- unitaires mockés FFmpeg (service/pipeline),
- tests d’intégration minimaux de session (fichiers de sortie + ranking).

**Critères d’acceptation**
- Tests pour les branches d’erreur FFmpeg indisponible/exécution/parse.
- Test de `EngineService.optimize` avec mocks: progression, tri score, écriture exports.
- Vérification stricte du schéma minimal de `analysis.json` et `ranking.json`.

---

## ISSUE-02 (P0) — Durcir la validation de configuration utilisateur

**Problème**  
Le chargement YAML accepte des valeurs potentiellement incohérentes (ex: bornes inversées, format de sortie non valide, presets inconnus).

**Impact**  
Comportements inattendus ou crash tardif dans le pipeline.

**Décision**  
Introduire une validation explicite post-load avec erreurs structurées.

**Critères d’acceptation**
- Refus clair si `target_lufs_min > target_lufs_max`.
- Refus clair si `ideal_true_peak_max > hard_true_peak_max`.
- Refus clair si `output_format` non supporté.
- Refus clair si preset inconnu dans `enabled_presets`.

---

## ISSUE-03 (P1) — Gérer les échecs partiels de candidats (best effort)

**Problème**  
Actuellement un échec de rendu/analyse sur un preset peut interrompre toute optimisation.

**Impact**  
Expérience fragile sur des lots réels, perte de temps utilisateur.

**Décision**  
Mode « best effort » par défaut: continuer avec les autres presets, marquer le candidat en échec, finaliser la session.

**Critères d’acceptation**
- Session produite même si ≥1 preset échoue.
- `CandidateResult.success=False` + message `error` renseigné.
- Ranking ne contient que les candidats réussis (ou section séparée des échecs).

---

## ISSUE-04 (P1) — Stabiliser le parsing loudness FFmpeg

**Problème**  
Le parsing repose sur le texte `summary` et regex fixes; robustesse limitée selon variations d’output FFmpeg.

**Impact**  
Risque de `LoudnessParseError` non déterministe selon environnements.

**Décision**  
Ajouter un parsing plus défensif + corpus de sorties FFmpeg de référence.

**Critères d’acceptation**
- Fixtures de logs FFmpeg réels (au moins 3 variantes).
- Parsing validé par tests parametrés.
- Message d’erreur enrichi (champ manquant identifié).

---

## ISSUE-05 (P1) — Implémenter l’écoute A/B basique (objectif V1)

**Problème**  
La roadmap et `TASKS_MASTER` listent l’A/B listening, mais ce n’est pas livré.

**Impact**  
Manque une brique critique de décision utilisateur avant export.

**Décision**  
Ajouter dans la GUI une comparaison A/B simple (source vs candidat sélectionné).

**Critères d’acceptation**
- Contrôles play/stop source et candidat.
- Changement rapide A/B sans relancer optimisation.
- Indication visuelle claire de la piste en cours.

---

## ISSUE-06 (P1) — Historique local des sessions

**Problème**  
Pas d’historique persistant des runs, malgré besoin identifié.

**Impact**  
Perte de traçabilité et de reproductibilité côté utilisateur.

**Décision**  
Enregistrer un historique léger local (date, input, mode, top résultat, dossier export).

**Critères d’acceptation**
- Fichier d’index local append-only ou petite base SQLite.
- Affichage des 10 dernières sessions dans la GUI.
- Action « ouvrir dossier export » depuis l’historique.

---

## ISSUE-07 (P2) — Explicabilité du scoring pour l’utilisateur final

**Problème**  
Les raisons de scoring existent mais restent techniques et parfois peu pédagogiques.

**Impact**  
Confiance utilisateur limitée sur la recommandation « best candidate ».

**Décision**  
Introduire un double niveau de raisons: technique + langage utilisateur.

**Critères d’acceptation**
- Chaque règle de scoring retourne une raison technique + une phrase vulgarisée.
- GUI affiche version vulgarisée; export JSON conserve les deux.

---

## ISSUE-08 (P2) — Packaging Windows reproductible

**Problème**  
Le plan mentionne PyInstaller/Nuitka et bundle FFmpeg, mais sans procédure automatisée.

**Impact**  
Risque de blocage release et de builds non reproductibles.

**Décision**  
Créer pipeline de build versionné + checklist de release.

**Critères d’acceptation**
- Choix outillage acté (benchmark démarrage/taille).
- Script build one-command.
- Document release: versioning, artefacts, smoke tests.

---

## ISSUE-09 (P2) — Gouvernance des presets et calibration audio

**Problème**  
Les presets sont statiques, peu de garde-fous de calibration inter-styles.

**Impact**  
Qualité perçue inégale selon matière source.

**Décision**  
Mettre en place un protocole de calibration avec corpus audio de validation.

**Critères d’acceptation**
- Corpus de test documenté (cas hot, dynamique, bass-heavy, etc.).
- Mesure avant/après tracée dans un rapport simple.
- Ajustements presets/scoring justifiés par données.

---

## 4) Ordre de réalisation recommandé

1. ISSUE-01 (tests)  
2. ISSUE-02 (validation config)  
3. ISSUE-03 (best effort)  
4. ISSUE-04 (parsing FFmpeg)  
5. ISSUE-05 + ISSUE-06 (valeur utilisateur GUI V1)  
6. ISSUE-08 + ISSUE-09 (industrialisation + qualité audio continue)

---

## 5) Résultat attendu après ce lot

- Fiabilité moteur nettement plus élevée.
- Meilleure tolérance aux erreurs réelles FFmpeg.
- Décision utilisateur améliorée (A/B + historique + explicabilité).
- Trajectoire claire vers une release Windows reproductible.

