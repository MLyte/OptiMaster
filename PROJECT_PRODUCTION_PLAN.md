# OptiMaster - Plan complet de production

## Résumé

OptiMaster sera développé comme une **application desktop Windows locale**, avec une **interface GUI légère en PySide6** au-dessus d'un **moteur Python + FFmpeg**. La première release publique sera **gratuite**, **sans compte**, **sans serveur**, et centrée sur un usage simple: charger un fichier, analyser la source, générer plusieurs finitions prudentes, classer les résultats, écouter les meilleurs candidats, puis exporter celui retenu.

Le produit ne doit pas être présenté comme un "mastering automatique magique". Sa vraie proposition de valeur est de fournir un **assistant de finition/mastering prudent, mesuré et reproductible**, surtout utile pour des exports déjà forts ou presque terminés, afin d'éviter les erreurs classiques de surtraitement.

Le repo actuel fournit déjà une base technique exploitable:
- CLI Python
- analyse loudness via FFmpeg
- génération de candidats
- scoring simple
- export de `analysis.json` et `ranking.json`

Ce plan sert de document maître pour piloter la production, guider Codex, et suivre l'avancement du projet.

---

## Vision produit

### Problème auquel l'app répond

Le problème principal n'est pas "comment masteriser n'importe quel morceau automatiquement", mais plutôt:

> Comment aider un utilisateur à finaliser rapidement et proprement un premaster déjà avancé, sans le dégrader, sans le surcomprimer, et sans dépasser des seuils de sécurité audio.

Les erreurs que l'app doit aider à éviter:
- pumping
- écrasement de la dynamique
- true peaks trop élevés
- rendu trop agressif
- perte de temps à tester des réglages à l'aveugle
- manque de méthode reproductible

### Promesse produit

OptiMaster doit être positionné comme:

> Un assistant local de finition/mastering qui teste plusieurs passes prudentes sur un export audio, mesure les résultats, puis recommande l'option la plus sûre et la plus équilibrée.

### Public cible

Cibles prioritaires:
- producteurs indépendants
- beatmakers
- artistes auto-produits
- home studios
- ingénieurs son cherchant un outil rapide de finition prudente

Non-cibles pour le MVP:
- studios de mastering haut de gamme
- workflows complexes temps réel dans DAW
- mastering cloud collaboratif
- automation avancée multi-genres dès V1

---

## Décisions produit déjà retenues

### Décisions principales

- Plateforme initiale: **Windows**
- Format: **application desktop**
- Architecture de diffusion: **local-first**
- Traitement audio: **100% local**
- Interface publique: **GUI**
- Interface technique conservée: **CLI**
- Stack GUI: **PySide6**
- Moteur audio: **Python + FFmpeg**
- Release V1: **gratuite**
- Compte utilisateur: **non**
- Serveur: **non**
- Cloud: **hors scope V1**
- Collaboration: **hors scope V1**
- Paiement/licence: **hors scope V1**
- Librairie UI web type Preline: **non retenue**

### Conséquences de ces décisions

- le moteur actuel Python est conservé et renforcé
- la GUI ne remplace pas la CLI, elle l'encapsule
- aucune logique métier dépendante d'un backend distant
- pas d'architecture SaaS à construire
- effort principal sur la robustesse, l'UX et le packaging Windows
- l'automatisation mastering doit rester prudente et explicable

---

## Principes produit à respecter

### Principes de conception

- faire peu, mais bien
- privilégier la sécurité audio à la démonstration
- rendre la logique lisible
- laisser la décision finale à l'utilisateur
- réduire la friction au maximum
- éviter toute esthétique ou wording "IA magique"
- construire un outil crédible, pas un effet marketing

### Principes de mastering

- ne pas appliquer un traitement lourd par défaut
- ne pas viser une transformation spectaculaire
- pénaliser fortement les true peaks dangereux
- préserver la dynamique dès que possible
- éviter une cible LUFS unique rigide pour tous les cas
- rester proche de la source si elle est déjà correcte
- préférer un rendu "légèrement prudent" à un rendu "impressionnant mais risqué"

---

## Architecture cible

### Vue d'ensemble

Le projet doit évoluer vers 4 couches claires:

1. **Core audio engine**
2. **Service layer applicatif**
3. **GUI desktop Windows**
4. **Packaging et release**

### 1. Core audio engine

Responsabilités:
- validation des fichiers d'entrée
- appel FFmpeg
- analyse loudness
- génération des candidats
- scoring
- sérialisation des résultats
- gestion des erreurs audio/techniques

Le moteur doit être utilisable sans dépendre de la CLI.

### 2. Service layer applicatif

Responsabilités:
- orchestration des sessions locales
- gestion de progression
- formatage des diagnostics utilisateur
- adaptation des résultats pour la GUI
- gestion des préférences locales
- logs applicatifs
- historique local léger plus tard

### 3. GUI desktop

Responsabilités:
- sélection du fichier
- affichage des métriques source
- lancement de l'optimisation
- affichage des résultats
- comparaison simple
- export
- affichage des erreurs et statuts

### 4. Packaging et release

Responsabilités:
- construction d'un exécutable ou installateur Windows
- intégration de FFmpeg
- gestion du premier lancement
- distribution des builds
- documentation de dépannage
- versioning

---

## Interfaces publiques à stabiliser

Le moteur doit converger vers des interfaces stables que la GUI et la CLI peuvent consommer.

### Interfaces métier attendues

- analyse d'un fichier source
- lancement d'une session d'optimisation
- récupération de la progression
- récupération des résultats classés
- récupération des diagnostics utilisateur
- récupération d'erreurs structurées

### Modèles de données attendus

Le système devra standardiser au minimum:

- `AppConfig`
- `ScoringConfig`
- `SourceAnalysis`
- `CandidatePreset`
- `CandidateResult`
- `OptimizationSession`
- `OptimizationMode`
- `UserFacingDiagnostic`
- `AppError`

### Données minimales exposées à la GUI

Pour une source:
- chemin du fichier
- format
- durée
- sample rate si disponible
- métriques source
- diagnostic texte

Pour chaque candidat:
- nom
- description
- chaîne de traitement
- métriques sortie
- score
- raisons du score
- chemin du rendu
- statut réussite/échec

Pour une session:
- identifiant local
- date
- mode d'optimisation
- fichier source
- liste des candidats
- meilleur candidat
- statut global
- chemins d'export

---

## Produit V1

### Fonctionnalités obligatoires

- sélectionner un fichier local WAV/FLAC
- vérifier la présence de FFmpeg
- analyser la source
- afficher LUFS, true peak et LRA
- afficher un diagnostic source compréhensible
- générer plusieurs candidats prudents
- rescorrer les candidats
- afficher un top 3
- montrer les raisons du classement
- exporter le candidat choisi
- écrire `analysis.json`
- écrire `ranking.json`
- gérer les erreurs proprement

### Fonctionnalités fortement souhaitées en V1 si le temps le permet

- drag and drop
- modes utilisateur `Safe`, `Balanced`, `Louder`
- écoute A/B simple
- historique local des sessions récentes
- messages de diagnostic plus détaillés

### Hors scope V1

- cloud
- compte
- sync
- collaboration
- paiement
- abonnement
- plugin DAW
- batch processing massif
- apprentissage automatique des préférences
- analyse musicale complexe par genre
- visualisations avancées

---

## UX cible

### Décision UX

Le produit public ne sera pas "terminal-only".
La CLI reste disponible pour:
- développement
- automatisation locale
- debug
- tests

La GUI sera le point d'entrée principal pour un utilisateur final.

### Parcours utilisateur principal

1. Ouvrir l'application
2. Sélectionner ou glisser un fichier
3. Voir l'analyse source
4. Choisir un mode si exposé
5. Lancer l'optimisation
6. Attendre la génération des candidats
7. Voir les meilleurs résultats
8. Comparer
9. Exporter le rendu retenu

### Structure d'écran recommandée

#### Zone 1 - Import

- bouton de sélection
- drag and drop
- nom du fichier
- informations techniques de base

#### Zone 2 - Analyse source

- integrated LUFS
- true peak
- LRA
- diagnostic clair
- avertissement si la source est déjà très forte

#### Zone 3 - Optimisation

- bouton lancer
- mode de traitement
- progression
- statut des candidats testés

#### Zone 4 - Résultats

- top 3
- score
- raisons
- métriques des candidats
- écoute comparative
- export

### États UI à prévoir

- état vide
- fichier invalide
- analyse en cours
- optimisation en cours
- optimisation réussie
- optimisation partiellement échouée
- erreur FFmpeg
- export réussi
- export échoué

---

## Direction visuelle

### Intentions visuelles

L'interface doit évoquer:
- un outil de studio fiable
- un environnement audio moderne
- une utility technique premium
- une expérience sobre et claire

### Recommandations visuelles

- fond sombre graphite/anthracite
- accent cyan, vert technique ou ambre discret
- typographie très lisible
- cartes métriques contrastées
- hiérarchie visuelle forte
- peu d'animations
- pas de look SaaS générique
- pas d'identité "startup IA"

### Décision sur Preline UI

Preline UI n'est pas utilisé.
Le projet ne suit pas une architecture web-first, et la couche d'interface doit être conçue directement dans l'écosystème PySide6 / Qt.

---

## Plan mastering automatisé

### Philosophie générale

L'app ne doit pas prétendre prendre seule la décision de mastering finale.
La bonne automatisation pour OptiMaster est:

- analyser automatiquement
- choisir une famille de traitements prudents
- générer plusieurs candidats
- mesurer et scorer les résultats
- recommander
- laisser l'utilisateur comparer et décider

### Pipeline mastering cible

#### 1. Validation d'entrée

Le système doit vérifier:
- lisibilité du fichier
- format supporté
- accès disque
- disponibilité FFmpeg
- compatibilité minimale du média

Erreurs à capturer:
- fichier absent
- format non supporté
- fichier corrompu
- FFmpeg absent
- rendu impossible

#### 2. Analyse source

Métriques MVP:
- integrated LUFS
- true peak
- LRA
- threshold loudness si récupéré
- durée
- informations de format utiles

Métriques ultérieures possibles:
- short-term loudness résumé
- crest factor
- répartition spectrale grossière
- énergie low/mid/high
- clipping probable
- silence tête/queue
- largeur stéréo simple

#### 3. Classification de la source

Le moteur doit identifier un profil simple, par exemple:
- déjà très hot
- presque prête
- besoin d'une simple finition
- marge faible
- dynamique correcte
- dynamique trop faible
- mieux vaut ne presque rien toucher

Cette classification pilotera les familles de candidats.

#### 4. Familles de chaînes de traitement

Le moteur doit reposer sur un nombre réduit de familles explicables, par exemple:
- `transparent_trim`
- `safe_limit`
- `sweet_spot`
- `gentle_glue`
- `do_almost_nothing`
- `louder_but_safe` plus tard
- `dynamic_preserve` plus tard
- `tone_tidy` plus tard

Chaque famille doit rester:
- prudente
- lisible
- contrôlable
- comparable

#### 5. Re-analyse des candidats

Chaque rendu doit être re-mesuré.
Le système doit comparer:
- niveau
- sécurité true peak
- dynamique
- stabilité globale par rapport à la source

#### 6. Scoring

Le scoring V1 doit intégrer:
- true peak sûr
- LUFS dans une plage cible
- dynamique préservée
- pénalité forte si unsafe
- pénalité si rendu trop écrasé

Le scoring V1.1 pourra ajouter:
- cohérence tonale avec la source
- bonus lié au profil détecté
- différenciation par mode utilisateur
- pénalité si transformation trop visible

#### 7. Recommandation

La sortie produit doit idéalement présenter:
- un rendu recommandé
- une option plus dynamique
- une option un peu plus forte

#### 8. Décision humaine finale

L'utilisateur final choisit le rendu à exporter.
Cette étape n'est pas un manque du produit: elle fait partie de sa crédibilité.

---

## Phasage de production

## Phase 0 - Cadrage produit

### Objectif

Transformer les décisions actuelles en cadre produit stable.

### Livrables

- vision produit courte
- proposition de valeur finale
- backlog MVP / V1.1 / plus tard
- messages produit et diagnostics de base
- critères de qualité audio

### Tâches à produire pour l'IA

- formaliser le positioning
- définir personas et anti-personas
- écrire les messages UI principaux
- documenter les cas d'usage prioritaires
- fixer les critères d'acceptation produit

### Critères de sortie

- scope MVP fermé
- promesse produit stable
- aucun flou sur Windows / desktop / local / sans compte

---

## Phase 1 - Durcissement du moteur

### Objectif

Rendre le moteur fiable, modulaire et exploitable par une GUI.

### Travaux

- isoler la logique métier de la CLI
- stabiliser les modèles métier
- durcir la gestion des erreurs FFmpeg
- améliorer la lisibilité du scoring
- préparer l'extensibilité des presets et modes
- ajouter davantage de tests

### Livrables

- moteur réorganisé
- service layer de base
- objets de sortie normalisés
- logs exploitables

### Tâches à produire pour l'IA

- proposer la nouvelle architecture interne
- découper les responsabilités entre moteur et CLI
- écrire la matrice des erreurs
- définir les types métier stables
- renforcer les tests unitaires et d'intégration

### Critères de sortie

- le moteur peut être invoqué sans passer par la CLI
- les erreurs principales sont structurées
- les résultats sont stables et sérialisables

---

## Phase 2 - Automatisation mastering V1

### Objectif

Faire évoluer le moteur d'un simple multi-presets vers une logique de décision audio prudente.

### Travaux

- introduire une classification simple de la source
- relier profils source et familles de presets
- améliorer le scoring
- enrichir les raisons textuelles
- ajouter les modes `Safe`, `Balanced`, `Louder` si retenus en V1

### Livrables

- stratégie mastering V1 documentée
- moteur de recommandation plus crédible
- meilleurs diagnostics

### Tâches à produire pour l'IA

- table de décision profil -> chaînes
- règles de scoring détaillées
- messages de diagnostic audio
- cas de test métier
- comparaison du comportement selon les modes

### Critères de sortie

- les candidats proposés dépendent du contexte source
- la recommandation paraît cohérente
- les raisons de classement sont compréhensibles

---

## Phase 3 - GUI PySide6 MVP

### Objectif

Construire une interface desktop simple et publiable.

### Travaux

- structure de l'application Qt
- écran principal
- sélection de fichier
- affichage de l'analyse
- lancement optimisation
- progression
- affichage résultats
- export
- gestion d'erreurs UI

### Livrables

- première app GUI complète
- thème visuel initial
- intégration moteur <-> GUI

### Tâches à produire pour l'IA

- spec UX détaillée
- hiérarchie de composants/fenêtres
- états UI
- messages utilisateur
- architecture des appels asynchrones / worker threads

### Critères de sortie

- un utilisateur non technique peut traiter un morceau sans terminal
- le parcours complet fonctionne de bout en bout
- la GUI reste simple et claire

---

## Phase 4 - Finitions d'usage

### Objectif

Renforcer la crédibilité et l'utilité concrète à l'usage.

### Travaux

- écoute A/B
- comparaison simple
- historique local léger
- amélioration de la lisibilité des résultats
- meilleur polish visuel
- meilleurs états de progression

### Livrables

- expérience utilisateur plus mature
- comparaison plus pratique
- app plus convaincante en beta

### Tâches à produire pour l'IA

- concevoir le comportement A/B
- définir les états de l'historique local
- proposer les microcopies finales
- lister les cas limites de lecture/export
- affiner le design system minimal

### Critères de sortie

- l'utilisateur peut comparer sans confusion
- les décisions d'export sont facilitées
- le produit paraît cohérent et abouti

---

## Phase 5 - Packaging et release Windows

### Objectif

Préparer une release publique installable.

### Travaux

- choisir l'outil de packaging
- définir la stratégie FFmpeg
- préparer l'installation
- gérer les chemins et logs
- produire un build reproductible
- documenter le premier lancement

### Livrables

- build Windows distribuable
- procédure de build
- guide utilisateur court
- guide de dépannage

### Tâches à produire pour l'IA

- comparer PyInstaller et Nuitka
- recommander une stratégie pour FFmpeg
- rédiger la checklist de release
- écrire la documentation de démarrage
- écrire une FAQ de troubleshooting

### Critères de sortie

- installation simple
- démarrage fiable
- erreurs connues documentées
- build reproductible

---

## Phase 6 - QA, beta et release 1.0

### Objectif

Fiabiliser le produit avant diffusion plus large.

### Travaux

- tests sur corpus réel
- validation humaine des rendus
- retours utilisateurs pilotes
- triage des bugs
- ajustement scoring/presets
- corrections packaging

### Livrables

- beta
- release candidate
- version 1.0

### Tâches à produire pour l'IA

- matrice de tests utilisateur
- grille d'évaluation qualité audio
- format de collecte feedback
- backlog de corrections
- plan de triage et priorisation

### Critères de sortie

- pas de bug bloquant sur le parcours principal
- résultats jugés utiles sur corpus pilote
- installation et utilisation stables

---

## Backlog macro priorisé

### P0

- durcissement du moteur
- séparation logique métier / CLI
- gestion d'erreurs structurée
- modèles de données stables
- GUI MVP
- pipeline complet import -> analyse -> optimisation -> résultats -> export
- logs
- packaging minimal Windows

### P1

- modes `Safe/Balanced/Louder`
- écoute A/B
- historique local
- diagnostics enrichis
- amélioration de l'ergonomie des exports

### P2

- familles de chaînes supplémentaires
- visualisation légère
- presets utilisateur
- batch léger
- site vitrine de téléchargement
- préparation d'un modèle de licence plus tard si nécessaire

---

## Plan de tests

### Tests unitaires

- parsing des sorties FFmpeg
- chargement des configs
- sélection des presets
- scoring
- classification source
- erreurs sur presets inconnus
- erreurs sur FFmpeg absent

### Tests d'intégration

- analyse d'un vrai fichier test
- pipeline complet
- sérialisation des résultats
- appels service layer -> moteur
- appels GUI -> service layer

### Tests GUI

- chargement d'un fichier
- analyse
- optimisation
- progression
- affichage des résultats
- export
- affichage des erreurs

### Tests packaging

- installation sur Windows propre
- FFmpeg disponible
- chemins avec espaces
- droits standard utilisateur
- premier lancement
- lecture/écriture des fichiers de sortie

### Validation audio humaine

Constituer un corpus de référence avec:
- morceau très hot
- morceau plus dynamique
- mix sombre
- mix bright
- morceau presque prêt
- cas où il faut presque ne rien toucher

Objectifs:
- juger si les recommandations sont prudentes
- vérifier la cohérence des scores
- valider que le moteur n'abîme pas la source
- ajuster progressivement les règles

---

## Observabilité locale

Même sans serveur, le produit doit prévoir:
- logs horodatés
- version de l'application
- version FFmpeg détectée
- journal d'erreurs exploitable
- capture des exceptions
- informations de session utiles au support

But:
- simplifier la beta
- rendre le debug plus rapide
- éviter les retours impossibles à reproduire

---

## Critères d'acceptation produit V1

La V1 peut être considérée comme atteinte si:

- un utilisateur Windows non technique peut traiter un morceau sans terminal
- l'app analyse localement un fichier et propose plusieurs rendus
- les résultats sont classés avec des raisons compréhensibles
- l'utilisateur peut exporter facilement
- aucun compte n'est requis
- aucun serveur n'est requis
- les erreurs principales sont bien gérées
- l'installation est simple
- le moteur reste prudent et crédible sur le corpus de validation

---

## Risques principaux

### Risque 1 - Trop promettre

Réponse:
- cadrer le produit comme assistant de finition prudent
- bannir les messages "perfect master" ou "AI mastering miracle"

### Risque 2 - GUI trop ambitieuse

Réponse:
- un seul écran principal
- peu de fonctions
- pas de complexité accessoire en V1

### Risque 3 - Packaging fragile

Réponse:
- tester le packaging tôt
- ne pas repousser FFmpeg et l'installation à la fin

### Risque 4 - Automatisation audio peu crédible

Réponse:
- rester conservateur
- valider sur corpus réel
- garder la décision finale humaine

### Risque 5 - Dette de structure

Réponse:
- stabiliser l'architecture moteur avant de construire l'interface
- ne pas empiler la GUI directement sur la CLI

---

## Hypothèses et choix par défaut

- Windows-first est maintenu
- la première release publique est gratuite
- aucun compte utilisateur n'est introduit
- aucun backend n'est créé
- le moteur Python existant est conservé
- PySide6 est la GUI retenue
- Preline UI n'est pas retenu
- la CLI reste disponible
- la GUI est l'interface principale pour le public
- le mastering reste semi-automatisé et explicable
- la décision d'export finale reste humaine

---

## Utilisation de ce document par Codex

Ce document doit servir de **source de vérité principale** pour le projet.

Utilisation recommandée:
1. lire ce document avant toute implémentation
2. en dériver un fichier `TASKS_MASTER.md`
3. découper le travail en tâches unitaires avec dépendances
4. traiter les phases dans l'ordre
5. ne pas lancer la GUI avant d'avoir durci le moteur
6. ne pas introduire de serveur, compte ou cloud sans décision explicite ultérieure

Format de tâche recommandé pour `TASKS_MASTER.md`:
- titre
- phase
- contexte
- objectif
- entrées
- sortie attendue
- dépendances
- contraintes
- critères d'acceptation
