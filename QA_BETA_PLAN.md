# QA / Beta / 1.0 - Plan d'execution (Phase 6)

Date de preparation: **22 avril 2026**

## 1) Corpus audio de validation

Corpus minimal defini pour la beta:

1. premaster pop moderne (deja fort, quasi fini)
2. mix hip-hop dense (basses saillantes)
3. morceau acoustique dynamique
4. mix electrique agressif (risque de true peak)
5. source volontairement faible en niveau
6. source deja limitee (cas "touch minimally")

Formats de test:

- WAV 24-bit / 44.1 kHz
- WAV 24-bit / 48 kHz
- FLAC 24-bit / 48 kHz

## 2) Matrice de tests manuels (parcours principal)

Pour chaque fichier du corpus:

1. import depuis la GUI
2. analyse source
3. optimisation en mode `safe`
4. optimisation en mode `balanced`
5. optimisation en mode `louder`
6. verification top 3 et raisons de ranking
7. ecoute A/B (source vs candidat)
8. export candidat selectionne
9. verification presence + validite JSON (`analysis.json`, `ranking.json`)

## 3) Ajustement scoring/presets (retours pilote)

Boucle de feedback:

1. capturer les retours qualitatifs de 3 a 5 utilisateurs pilotes
2. enregistrer les cas "trop agressif" / "trop faible" / "degradation percue"
3. ajuster scoring (penalites true peak, agressivite, dynamique)
4. relancer la matrice sur les cas regressifs

## 4) Gate release candidate (RC)

Critere "RC ready":

- 0 crash bloquant sur matrice principale
- exports valides sur 100% du corpus
- moins de 5% de cas juges "degradation evidente" par le panel pilote
- packaging Windows valide sur 2 machines cibles minimum

## 5) Gate release 1.0

Critere "1.0 ready":

- checklist RC complete
- README et guide utilisateur finalises
- changelog publie
- artefact binaire signe/hache et archive
