# Plan d'engagement d'un(e) UX/UI Designer Senior + audit initial d'OptiMaster

## 1) Mandat à confier immédiatement

**Objectif business :** améliorer la clarté du parcours de mastering, réduire les erreurs de manipulation, et augmenter le taux d'export final réussi au premier essai.

**Objectif produit :** transformer la GUI v0 en expérience orientée workflow (import → analyse → optimisation → comparaison → export), avec des retours d'état explicites et une hiérarchie visuelle plus lisible.

## 2) Profil recherché (Senior UX/UI)

Recruter un profil capable de couvrir **produit + exécution** :

- 6+ ans en UX/UI sur logiciels desktop pro ou outils créatifs (audio, DAW, vidéo, data tools).
- Maîtrise des audits heuristiques (Nielsen), architecture d'information, prototypage (Figma), design system, handoff dev.
- Expérience prouvée en optimisation de parcours complexes à étapes.
- Capacité à transformer des métriques techniques (LUFS, dBTP, LRA) en éléments compréhensibles pour des utilisateurs non experts.
- Culture de validation : tests utilisateurs rapides, itérations courtes, décisions pilotées par KPIs.

## 3) Plan d'intervention (4 semaines)

### Semaine 1 — Cadrage & audit expert
- Kickoff (90 min) : objectifs, contraintes techniques PySide6, priorités produit.
- Audit heuristique complet de l'interface actuelle.
- Cartographie des parcours critiques :
  1. Importer un fichier valide.
  2. Lancer l'analyse.
  3. Choisir un mode et optimiser.
  4. Comprendre le ranking.
  5. Exporter le meilleur candidat.
- Diagnostic des points de friction + score de sévérité (critique / majeur / mineur).

### Semaine 2 — Recherche légère & stratégie UX
- 5 entretiens utilisateurs (ingés son / beatmakers / producteurs indépendants).
- Synthèse jobs-to-be-done + niveaux d'expertise (débutant, intermédiaire, expert).
- Définition des principes UX (guidage, sécurité audio, explicabilité des scores).
- Priorisation des améliorations (Impact / Effort).

### Semaine 3 — Conception UI
- Wireframes low-fi des écrans clés.
- Prototype high-fi du flux principal (desktop).
- Standardisation des composants (boutons, alertes, états de progression, tableaux, aides contextuelles).
- Règles d'accessibilité (contrastes, taille typographique, focus clavier).

### Semaine 4 — Validation & handoff
- Tests utilisateurs modérés (5 sessions) sur prototype.
- Ajustements finaux.
- Livraison du kit de handoff : specs UI, comportements, microcopies, états d'erreur, tokens.
- Plan de rollout par lots (quick wins puis refonte structurelle).

## 4) Audit initial de l'application actuelle (constats)

## Forces
- Le workflow central est déjà visible (session, contrôles, analyse, résultats).
- Les actions principales existent et sont explicites : analyse, optimisation, export.
- Les résultats sont structurés en tableau avec détail complémentaire.
- Le système expose des feedbacks de progression via statut + barre de progression.

## Frictions UX/UI à traiter en priorité

1. **Densité cognitive élevée sur un écran unique**  
   Toutes les étapes sont affichées simultanément, ce qui peut noyer l'utilisateur novice.

2. **Guidage insuffisant du parcours**  
   L'interface ne matérialise pas un stepper clair (Étape 1/2/3/4). L'utilisateur doit inférer la séquence.

3. **Microcopies principalement techniques**  
   Les métriques LUFS/TP/LRA sont affichées sans couche pédagogique intégrée.

4. **Hiérarchie visuelle perfectible**  
   Les blocs “Source analysis”, “Recommended candidate”, “Top candidates” sont présents mais peuvent être mieux priorisés selon l'avancement.

5. **États d'erreur et prévention**  
   Bonne base de validation de format audio, mais manque d'aides préventives (ex. "fichier déjà très hot, mode Safe recommandé").

6. **Confiance décisionnelle**  
   Le score est affiché, mais la logique de recommandation mérite une présentation plus narrative (Pourquoi ce preset est premier ? Quel compromis ?).

## 5) Quick wins (implémentables rapidement)

1. Ajouter un bandeau d'étapes en haut : **1 Import → 2 Analyse → 3 Optimisation → 4 Export**.
2. Ajouter des "info-bulles" sur LUFS, True Peak, LRA avec seuils recommandés.
3. Mettre en avant une carte "Prochaine action recommandée" dynamique.
4. Introduire des états vides plus pédagogiques dans le tableau des candidats.
5. Améliorer la lisibilité des risques (couleurs/labels) pour true peak trop proche de 0 dBTP.
6. Clarifier le texte du bouton d'export avec le nom du preset sélectionné.

## 6) Livrables attendus du designer senior

- Audit UX complet (heuristiques + parcours + sévérité).
- UX strategy one-pager (personas, JTBD, principes).
- Prototype Figma desktop couvrant le flux principal.
- UI kit minimal (couleurs, typo, composants, états).
- Spécification de handoff priorisée en tickets (P0/P1/P2).
- Plan d'expérimentation avec KPIs :
  - temps moyen jusqu'au premier export,
  - taux d'erreur de parcours,
  - taux d'acceptation de la recommandation #1,
  - satisfaction perçue (SUS / score interne).

## 7) Message de recrutement prêt à publier (copier/coller)

**Titre :** UX/UI Designer Senior (Desktop Audio Tool)

Nous cherchons un(e) UX/UI Designer Senior pour auditer et améliorer l'expérience de notre application desktop Python (PySide6) dédiée au mastering audio assisté.

**Mission (4 semaines, renouvelable) :**
- Réaliser un audit UX/UI expert de l'existant.
- Reconcevoir le parcours utilisateur clé (import, analyse, optimisation, export).
- Livrer un prototype high-fidelity + design system léger.
- Préparer le handoff complet pour l'équipe de développement.

**Compétences requises :**
- Expérience confirmée sur des outils desktop techniques.
- Maîtrise UX research légère, audit heuristique, Figma, design system.
- Capacité à simplifier des données techniques en décisions utilisateur claires.
- Français courant requis, anglais technique apprécié.

**Pour candidater :** envoyez portfolio + 2 cas concrets d'amélioration de workflows complexes + disponibilité.

## 8) Mode de collaboration recommandé

- Cadence : 2 points fixes par semaine (30-45 min).
- Outils : Figma + board tickets + revues asynchrones.
- Gouvernance : Product décide, Designer recommande, Dev valide la faisabilité.
- Definition of Done UX : validé par test utilisateur + faisabilité technique + métriques de succès définies.

---

Si besoin, ce document peut être transformé en **brief agence** (format appel d'offres) ou en **scorecard d'entretien** pour comparer les candidats sur des critères objectifs.
