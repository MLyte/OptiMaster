# ISSUES_BRAINSTORM_2026-04-22

## Taches prioritaires (MVP + usage)
- [x] Ajouter un historique local leger des sessions (sans cloud, sans compte).
- [x] Exposer cet historique dans l'interface graphique pour consultation rapide.
- [x] Ajouter une couverture de tests sur le comportement de persistance de l'historique.

## Notes
- L'historique est limite aux 200 sessions les plus recentes.
- Le stockage est effectue en JSONL local (`~/.optimaster/session_history.jsonl`).
