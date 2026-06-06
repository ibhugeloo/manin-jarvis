---
name: Brief quotidien Jarvis (cron local 7h30)
description: Système de brief matinal automatique. Cron launchd qui invoque Claude headless chaque matin et écrit un résumé dans le vault Obsidian.
type: reference
---

Système mis en place le 2026-05-05.

## Composants

| Élément | Chemin |
|---|---|
| Wrapper script | `~/.local/bin/jarvis-brief.sh` |
| Prompt instruction | `~/.local/share/jarvis/brief-prompt.md` |
| LaunchAgent plist | `~/Library/LaunchAgents/com.example.jarvis.brief.plist` |
| Output (briefs) | `~/Documents/Obsidian/vault/Brief/YYYY-MM-DD.md` |
| Logs | `~/.local/var/log/jarvis-brief.log` (+ `.stdout.log` / `.stderr.log`) |

## Schedule
- **Tous les jours 7h30** (weekends inclus, validé par le boss).
- launchd `StartCalendarInterval` — rattrape automatiquement si le Mac dormait à l'heure prévue.
- `RunAtLoad: false` — pas de lancement au boot, uniquement à l'heure planifiée.

## Sources scannées par le brief
1. Google Calendar (jour + lendemain) via MCP
2. Gmail (`is:unread is:important`, top 5) via MCP
3. Repos `~/Documents/GIT PROD/*` (commits non pushés, modifs locales, repos inactifs >7j)
4. Vault Obsidian — `todo.md` divers, Roadmap, ShopApp/todo, etc.
5. Notion `Inbox Jarvis` (sous-pages non rangées)

## Format de sortie (Markdown)
Sections fixes : 📅 Aujourd'hui · 🔮 Demain · 📧 Mails · 💻 Repos · 📝 Actions · 📥 Inbox · 🎯 Suggestion. Chaque section vide → `_RAS_`.

## Commandes utiles

```bash
# Lancer le brief manuellement (test)
~/.local/bin/jarvis-brief.sh

# Voir les logs
tail -f ~/.local/var/log/jarvis-brief.log

# Désactiver temporairement
launchctl unload ~/Library/LaunchAgents/com.example.jarvis.brief.plist

# Réactiver
launchctl load -w ~/Library/LaunchAgents/com.example.jarvis.brief.plist

# Vérifier que l'agent est chargé
launchctl list | grep jarvis

# Forcer un déclenchement immédiat (bypass schedule)
launchctl start com.example.jarvis.brief
```

## Maintenance / extensions futures
- **V2** : ajouter sources votre broker (portefeuille) quand MCP votre broker disponible.
- **V2** : ajouter alertes proactives (RDV dans 1h sans préparation, dossier ClientCo inactif >X jours).
- **V2** : push iOS via Pushover ou Apple Shortcuts pour notifications hors Mac.
- **Modifier l'heure** : éditer le plist (`Hour` / `Minute`) puis `launchctl unload && launchctl load -w`.
- **Modifier les sources** : éditer `~/.local/share/jarvis/brief-prompt.md` directement.
