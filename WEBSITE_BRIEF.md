# Brief IA - Site vitrine open source OptiMaster

Utilise ce brief pour creer une page vitrine moderne pour le projet open source OptiMaster.

## Objectif

Creer une landing page publique qui fait connaitre OptiMaster, explique clairement son utilite, et invite les visiteurs a tester, ameliorer et contribuer au projet sur GitHub.

Lien GitHub principal :
https://github.com/MLyte/OptiMaster

Page releases :
https://github.com/MLyte/OptiMaster/releases

## Produit

OptiMaster est une application locale de finition audio pour fichiers WAV et FLAC.

Elle analyse un premaster, genere plusieurs candidats de mastering avec FFmpeg, mesure les resultats, puis aide l'utilisateur a comparer, ecouter en A/B et exporter la meilleure version.

Le projet est en beta publique, open source sous licence MIT, et cherche des testeurs/contributeurs pour ameliorer l'UX, le packaging Windows, les choix audio, le scoring, les presets et les cas limites FFmpeg.

## Statut actuel

Version beta :
`2026.4.24`

Build public recommande :
`OptiMaster-v2026.4.24-beta.2-windows-x64.zip`

OptiMaster affiche son runtime dans l'en-tete et la barre de titre pour aider les testeurs a identifier le build utilise :
- `2026.4.24-python` pour l'app lancee depuis le code source
- `2026.4.24-exe` pour l'executable package

Windows est la cible principale actuelle. FFmpeg doit etre installe et disponible dans le `PATH`.

## Positionnement

OptiMaster n'est pas un "mastering magique en un clic".

C'est un assistant local, prudent et transparent pour :
- analyser un morceau
- comprendre le profil source
- choisir un objectif de loudness
- proposer plusieurs versions
- comparer avant / apres
- ecouter A/B
- exporter proprement
- apprendre ce que les mesures LUFS, True Peak, LRA et dynamique impliquent

Ton souhaite :
- clair
- moderne
- direct
- accessible aux musiciens non techniques
- honnete sur le statut beta
- motivant pour les contributeurs

## Public

Public principal :
- producteurs bedroom / home studio
- beatmakers
- artistes independants
- ingenieurs son curieux
- developpeurs interesses par audio, Python, FFmpeg, PySide6, packaging Windows et UX

Le site doit parler autant aux createurs audio qu'aux personnes capables d'ameliorer l'outil.

## Message central

Headline proposee :
`A local open source audio finishing assistant.`

Alternative plus expressive :
`Mastering candidates you can measure, compare, and improve.`

Sous-titre :
`OptiMaster analyzes WAV and FLAC premaster files, renders safe mastering candidates, shows before/after metrics, and helps you export a cleaner final version.`

## CTA

CTA principal :
`View on GitHub`

Lien :
https://github.com/MLyte/OptiMaster

CTA secondaire important :
`Download beta`

Lien :
https://github.com/MLyte/OptiMaster/releases

CTA secondaires :
- `Read the README`
- `Report an issue`
- `Try the beta`
- `Improve the UI`
- `Test a Windows build`

Les CTA doivent clairement pousser vers GitHub, les releases beta et la contribution.

## Sections recommandees

### 1. Hero

Elements a afficher :
- Nom : OptiMaster
- Badge : Public beta / MIT open source
- Mention de build : `2026.4.24 beta.2`
- Phrase courte sur l'utilite
- CTA GitHub
- CTA Download beta
- Apercu visuel inspire d'une app audio moderne : waveform, before/after, candidates, progress, A/B

Le hero doit montrer que l'app est deja utilisable, mais encore ouverte aux retours.

### 2. Why it exists

Messages :
- Les outils de mastering peuvent etre opaques.
- OptiMaster rend le process plus lisible : mesures, candidats, raisons de score, comparaison.
- Le but est d'aider a decider, pas de remplacer l'oreille.
- Les exports doivent rester verifies sur de vrais systemes d'ecoute.

### 3. What it does

Mettre en evidence :
- import WAV / FLAC
- analyse FFmpeg
- diagnostics de profil source
- mesures LUFS, True Peak, LRA et dynamique
- workflow Source / Versions / Listen-Export
- modes Clean / safe, Balanced master et Push louder
- cibles LUFS rapides pour streaming, SoundCloud, club/DJ, hard/raw et tests extremes
- recommandation LUFS automatique apres analyse
- cible LUFS custom dans la GUI
- option True Peak strict
- recherche de la version propre la plus forte
- controle du temps disponible : Fast preview, Balanced, Most careful
- variantes de comparaison plus prudentes en mode Most careful
- fallback technique OptiMaster quand une cible est trop agressive
- classement avec raisons de score
- comparaison avant / apres
- ecoute A/B dans la GUI
- waveform preview et visualisation de lecture
- progression de rendu avec pourcentage, temps ecoule, ETA et annulation
- noms d'export propres et incrementaux
- historique local de session
- notes d'ecoute et preferences locales
- CLI pour analyse, rendu, batch processing, presets et listening notes

### 4. Workflow

Presenter en 5 etapes simples :
- Choose a source
- Analyze the source
- Pick a target and time budget
- Render candidates
- Compare, listen A/B, and export

Le site peut traduire ce workflow en interface visuelle : source file, target selector, render queue, ranked candidates, final export.

### 5. Beta download

Expliquer simplement :
- Les builds publics sont publies via GitHub Releases.
- Le fichier pour non-developpeurs est un `.zip` Windows portable.
- Le nom attendu pour la beta actuelle est `OptiMaster-v2026.4.24-beta.2-windows-x64.zip`.
- Il faut dezipper l'archive, lancer `OptiMaster.exe`, puis verifier que FFmpeg est disponible.
- Les archives sont generees par GitHub Actions et ne sont pas committees dans le repo.

Cette section doit etre rassurante, courte et pratique.

### 6. Built for contributors

Inviter a aider sur :
- UX/UI
- microcopy
- Windows packaging
- audio scoring
- presets par genres / plateformes
- tests sur fichiers reels
- cas limites FFmpeg
- test coverage
- docs
- release smoke tests

Faire sentir que le projet cherche des oreilles critiques et des regards UX, pas seulement du code.

### 7. Honest beta note

Dire clairement :
- Windows-first for now
- FFmpeg required
- beta quality
- packaging still evolving
- loudness targets can be pushed too far
- loudest-clean search can take longer
- metrics guide the decision but do not replace listening
- session history and preferences stay local, not cloud-synced
- exports should be checked on real monitoring systems

### 8. Final CTA

Repeter le lien GitHub et la page Releases avec une phrase chaleureuse :
`Try it, break it, improve it.`

## Direction visuelle

Creer une page 2026, premium mais pas corporate.

Style souhaite :
- dark mode audio tool
- fond sobre, pas trop bleu Windows
- accent teal ou jaune discret
- waveforms, meters, before/after panels
- candidats classes
- etats de progression lisibles
- controles inspires d'une app audio : sliders, toggles, badges, meters
- cards propres mais pas trop marketing
- grands espaces maitrises
- typographie nette
- interface inspiree SaaS/audio workstation, pas landing page crypto

Ne pas faire :
- page trop marketing
- promesse "AI mastering" magique
- visuels stock generiques
- trop de gradients violets
- jargon audio inaccessible
- UI qui ressemble a un vieux `.exe` Windows
- CTA de download plus visible que la prudence beta

## Textes courts utilisables

`OptiMaster is a local-first mastering companion for people who want options, not black boxes.`

`Render multiple candidates, compare the numbers, listen A/B, then export the version that actually makes sense.`

`Choose how much time OptiMaster can spend: fast preview, balanced ranking, or a more careful comparison pass.`

`Open source, beta, and looking for sharp ears and sharp eyes.`

`Built with Python, PySide6, and FFmpeg.`

`MIT licensed. Contributions welcome.`

`Windows-first beta. FFmpeg required. Your ears still make the final call.`

## Donnees projet

Nom :
OptiMaster

Version beta :
2026.4.24

Build public :
2026.4.24-beta.2

Licence :
MIT

Repository :
https://github.com/MLyte/OptiMaster

Releases :
https://github.com/MLyte/OptiMaster/releases

Tech :
Python, PySide6, FFmpeg, PyYAML, PyInstaller

Plateforme cible actuelle :
Windows first

## Contraintes de sortie pour l'IA

Creer une landing page prete a publier, avec :
- contenu en anglais
- design responsive desktop/mobile
- structure claire
- CTA GitHub visibles
- CTA GitHub Releases visible
- section contribution
- mention beta, MIT, Windows-first et FFmpeg
- pas de dependance a un backend

Si l'IA genere du code, preferer une page statique simple :
- `index.html`
- `styles.css`
- `script.js` seulement si necessaire

Le resultat doit donner envie de tester et d'ameliorer OptiMaster, pas seulement de le telecharger.
