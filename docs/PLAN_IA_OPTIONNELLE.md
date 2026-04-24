# Plan d’intégration IA optionnelle (gratuit + open source)

## Objectif
Ajouter une couche IA utile pour la décision de mastering **sans rendre l’application dépendante d’un service payant**.

## Problème UX clair
L’utilisateur obtient des mesures techniques et plusieurs candidats, mais il manque une aide “humaine” pour relier rapidement les résultats à une intention créative (ex: plus agressif, plus propre, meilleure traduction smartphone).

## Amélioration concrète
Introduire un **Copilote d’intention** en mode optionnel:
- par défaut: fonctionnement actuel (non-IA, déterministe)
- optionnel: explications en langage naturel + recommandations guidées selon l’intention utilisateur

---

## Principes produit à respecter
1. **IA non obligatoire**: l’app reste pleinement utilisable sans IA.
2. **Priorité local/offline**: pas d’API externe requise pour l’usage principal.
3. **Open source first**: composants et intégrations compatibles avec un usage communautaire.
4. **Coût nul par défaut**: aucune facture côté utilisateur pour le flux standard.

---

## Périmètre MVP (itération 1)
### Inclus
- Un bloc UI “Copilote (beta)” activable/désactivable.
- Saisie d’intention simple (3 axes):
  - Densité (aéré ↔ dense)
  - Impact (soft ↔ punchy)
  - Brillance (doux ↔ brillant)
- Génération d’une synthèse textuelle courte:
  - “Pourquoi ce candidat”
  - “Risques de traduction probables”
  - “Prochain test d’écoute conseillé”

### Exclu (plus tard)
- Fine-tuning de modèle.
- Envoi cloud obligatoire.
- Automatisation complète des décisions artistiques.

---

## Architecture fonctionnelle (sans refactor)
1. **Core existant inchangé**: analyse, rendu, scoring, ranking restent la source de vérité.
2. **Adaptateur IA optionnel**:
   - entrée: métriques + ranking + intention utilisateur
   - sortie: résumé explicatif structuré
3. **Fallback natif**: si IA indisponible, afficher un texte template basé sur les règles actuelles.

---

## Backlog de livraison (3 étapes max)
1. **UI d’intention + toggle IA**
   - ajouter les champs d’intention
   - ajouter un interrupteur “Activer l’assistance IA locale (beta)”
2. **Adaptateur IA local + fallback**
   - brancher un provider local optionnel
   - implémenter un fallback déterministe si provider absent
3. **Validation UX + garde-fous**
   - tester clarté des explications
   - vérifier que le parcours sans IA reste identique et stable

---

## Critères d’acceptation
- L’application fonctionne à l’identique avec l’IA désactivée.
- Aucun compte ni clé API n’est nécessaire pour le workflow principal.
- Les explications IA sont courtes, compréhensibles, et jamais présentées comme vérité absolue.
- En cas d’échec IA, l’utilisateur garde des recommandations exploitables via fallback.

---

## Risques & mitigation
- **Risque**: confusion sur le caractère “automatique” de l’IA.
  - **Mitigation**: microcopy explicite “assistant de décision, pas remplacement ingénieur”.
- **Risque**: latence locale.
  - **Mitigation**: réponses limitées (format court), option de désactivation.
- **Risque**: dérive de coût si cloud activé plus tard.
  - **Mitigation**: cloud en option avancée, jamais par défaut.

---

## Microcopy proposée
- Toggle: **“Activer l’assistance IA locale (beta)”**
- Aide: **“Optionnel. Le mastering reste entièrement utilisable sans IA.”**
- Disclaimer: **“Le copilote propose des pistes; la décision finale reste à l’écoute.”**

---

## Définition de succès
- Taux d’activation du copilote (opt-in) > 25% en beta test.
- Diminution des hésitations avant export (mesurée via feedback session).
- Pas d’augmentation du taux d’échec du flux principal (non-IA).

---

## Note d’implémentation future
Commencer par une version strictement locale et textuelle. Reporter toute complexité (multi-modèles, cloud, personnalisation avancée) après validation UX terrain.
