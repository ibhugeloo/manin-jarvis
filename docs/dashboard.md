---
name: Dashboard graphique Jarvis (localhost:7474)
description: Interface web locale qui agrège l'état complet de Jarvis (briefs, repos, agents, sessions, bot, logs) en bento minimaliste. Lancée à la demande via `jarvis-ui`.
type: reference
---

Système ajouté le 2026-05-05.

## Lancement

```bash
jarvis-ui              # lance le serveur + ouvre le navigateur
jarvis-ui --no-open    # lance sans ouvrir le navigateur
jarvis-ui --port 8000  # autre port
```

Si déjà actif, `jarvis-ui` réouvre simplement le navigateur sans relancer le serveur.

## URL

`http://localhost:7474`

## Composants

| Élément | Chemin |
|---|---|
| Wrapper CLI | `~/.local/bin/jarvis-ui` (symlink) |
| Serveur Python | `~/.local/bin/jarvis-ui-server.py` (copie, TCC) |
| Source canonique | `~/Documents/GIT PROD/manin-jarvis/bin/` |
| Logs serveur | `~/.local/var/log/jarvis-ui.log` |

Pas de LaunchAgent — le dashboard est démarré à la demande pour ne pas laisser un port HTTP ouvert en permanence.

## Sections du dashboard

1. **Brief du jour** (large, à gauche) — onglets Matin / Soir / Hebdo / Mensuel / Évaluation, avec preview rendue depuis le markdown
2. **Repos GIT PROD** — liste status (clean / dirty / stale > 30j), modifs, commits non pushés
3. **Bot Telegram** — alive/dead, pid, username, compteur d'historique, dernier échange
4. **Agents lancés** — état des 7 LaunchAgents Jarvis (cron jobs)
5. **Sessions Claude récentes** — top 5, titre + date + projet + bullets "Ce qui a été fait"
6. **Activité système** — dernière ligne de chaque log (brief, routines, bot, notion-export, session-recap)

## Stack technique

- Python 3 stdlib uniquement (`http.server`, `subprocess`, `pathlib`) — zéro dépendance
- HTML/CSS/JS embarqués dans le `.py`
- Polices Google Fonts : Instrument Serif (titres) + Geist Sans/Mono (corps/code)
- Bento grid CSS, palette warm-monochrome, accents pastel selon directives `minimalist-ui`
- Auto-refresh toutes les 30s, `r` pour forcer

## API endpoints (consultable via curl)

| Endpoint | Données |
|---|---|
| `GET /api/repos` | Liste repos GIT PROD |
| `GET /api/agents` | État des LaunchAgents |
| `GET /api/briefs` | Briefs matin/soir/hebdo/mensuel/évaluation |
| `GET /api/sessions` | 5 derniers récaps de session |
| `GET /api/telegram` | État bot Telegram |
| `GET /api/logs` | Dernière ligne de chaque log Jarvis |

## Évolutions futures possibles

- POST endpoints pour déclencher manuellement (run brief, restart bot, ...)
- WebSocket pour push en temps réel des nouveaux briefs / sessions
- Historique graphique (volume de sessions par jour, etc.)
- Mode dark
- Vue mobile optimisée
