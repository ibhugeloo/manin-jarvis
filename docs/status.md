---
name: jarvis-status — vue groupe cross-projet
description: CLI rapide qui scanne tous les repos GIT PROD et donne leur état (branche, commits non pushés, modifs, dernier commit, jours d'inactivité).
type: reference
---

Outil ajouté le 2026-05-05.

## Usage

```bash
jarvis-status              # affichage humain coloré
jarvis-status --json       # sortie JSON pour pipe vers d'autres outils
```

## Sortie type

```
● example-app           [main] — 3 days ago
    25 fichiers modifiés
○ portfolio-site         [main] — 9 weeks ago
    55 fichiers modifiés
    61j sans commit
✓ agency-site             [main] — 3 days ago
```

Légende :
- `✓` (vert) : repo clean, synchronisé
- `●` (jaune) : modifs locales OU commits non pushés
- `○` (rouge) : inactif depuis >30 jours

## Quand l'utiliser

- Au début d'une session si le boss demande *"tour d'horizon"*, *"où en est-on ?"*, *"que se passe-t-il sur mes projets ?"*
- Avant d'ouvrir un projet : voir s'il a des changements pending qui méritent de re-checker
- Comme source de données pour le brief matinal et le récap soir (déjà intégré dans les prompts)

## Implémentation

- Pure bash + git, pas de Claude requis (latence < 1s)
- Skip propre des dossiers non-Git (vérifie `git rev-parse --is-inside-work-tree` avant)
- Détecte aussi les **wrappers** (dossier non-Git contenant un repo enfant) — descend d'un niveau pour exposer le vrai repo, conformément à `lessons.md` #10. (Note 2026-05-06 : `agency-app` a été aplati, plus de wrapper actif aujourd'hui — la logique reste pour de futurs cas.)

## Composants

| Élément | Chemin |
|---|---|
| Script | `~/.local/bin/jarvis-status` (symlink → vault) |
| Source canonique | `~/Documents/GIT PROD/manin-jarvis/bin/jarvis-status` |
