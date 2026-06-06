---
name: Session-mémoire — récap automatique en fin de session Claude Code
description: Hook SessionEnd qui génère un récap structuré du transcript via Haiku et l'écrit dans le vault. Permet de retrouver le contexte des sessions passées.
type: reference
---

Système mis en place le 2026-05-05.

## Composants

| Élément | Chemin |
|---|---|
| Hook script | `~/.local/bin/jarvis-session-recap.sh` |
| Push Notion (background) | `~/.local/bin/jarvis-notion-session-push.sh` |
| Configuration hook | `~/.claude/settings.json` (clé `hooks.SessionEnd`) |
| Récaps générés (Obsidian) | `~/Documents/Obsidian/vault/Claude/Sessions/YYYY-MM-DD-HHMM-<session_id>-<topic>.md` |
| Récaps poussés (Notion) | sous-pages de **Inbox Jarvis** (`<your-notion-inbox-page-id>`) |
| Logs récap | `~/.local/var/log/jarvis-session-recap.log` |
| Logs push Notion | `~/.local/var/log/jarvis-notion-session-push.log` |

## Déclenchement

- **Automatique** : à chaque fin de session Claude Code (event `SessionEnd` — typiquement déclenché par `/exit` ou `/clear`).
- **Garde anti-récursion** : variable `JARVIS_RECAP_RUNNING=1` pour empêcher la rentrée infinie quand le script appelle lui-même `claude -p`. Le push Notion ajoute aussi `JARVIS_NOTION_PUSH_RUNNING=1`.
- **Skip auto** : transcript < 8 lignes JSONL (sessions triviales).
- **Multi-terminaux** : trois `/exit` simultanés = trois récaps + trois pages Notion indépendantes (chaque session a son propre `transcript_path`).

## Format du récap

Markdown avec frontmatter YAML (date, projet, session_id) puis sections :

- `# Session YYYY-MM-DD — <sujet>`
- `## Contexte`
- `## Ce qui a été fait`
- `## Décisions clés`
- `## Fichiers touchés`
- `## Reste à faire`
- `## À retenir pour les prochaines sessions`

Sections vides → `_RAS_`.

## Push Notion automatique (depuis 2026-05-06)

Après écriture du récap dans `Sessions/`, le hook lance `jarvis-notion-session-push.sh` en **background détaché** (`nohup ... &`). Le push :

1. Lit le frontmatter du récap (date, projet, titre).
2. Compose un prompt pour `claude -p --model haiku --dangerously-skip-permissions`.
3. Le subprocess Haiku appelle l'outil MCP `mcp__claude_ai_Notion__notion-create-pages` avec `parent.page_id = <your-notion-inbox-page-id>` (Inbox Jarvis).
4. Notif Telegram silencieuse avec le titre + URL.

**Toutes les sessions sont sauvegardées sans filtre** (décision 2026-05-06) — l'audit mensuel (`routine-mensuel`) trie les pages utiles vs déchets dans Inbox Jarvis. Le filtrage Haiku amont aurait été coûteux et fragile ; mieux : tout pousser, ranger une fois par mois.

## Comment Jarvis l'utilise

Au début d'une nouvelle session, si le boss demande *"continue ce qu'on faisait hier"* ou *"où on en était sur X"* :

1. Lister les récaps récents : `ls -t ~/Documents/Obsidian/vault/Claude/Sessions/*.md | head -5`
2. Lire le ou les récaps pertinents (filtrer par projet/topic).
3. Reprendre le fil avec le contexte chargé.

## Commandes utiles

```bash
# Voir les récaps récents
ls -lt ~/Documents/Obsidian/vault/Claude/Sessions/ | head -10

# Voir les logs du hook
tail -f ~/.local/var/log/jarvis-session-recap.log

# Test manuel (avec un transcript existant)
echo '{"session_id":"<id>","transcript_path":"/chemin/vers/transcript.jsonl","cwd":"...","reason":"clear","hook_event_name":"SessionEnd"}' \
  | ~/.local/bin/jarvis-session-recap.sh

# Désactiver temporairement : retirer la clé "hooks" de ~/.claude/settings.json
# Réactiver : remettre la clé
```

## Coûts

- 1 appel Haiku par session (≈ 0.001-0.005$ selon longueur du transcript).
- Disque : ~1-3 KB par récap, négligeable.
- Latence : 5-30s en fin de session (asynchrone, ne bloque pas la fermeture).

## Limites connues

- **Transcripts > 800 lignes JSONL** : seuls les 200 premiers et 600 derniers événements sont passés à Haiku (le milieu est omis avec un marqueur). Risque de manquer une décision prise au milieu d'une longue session.
- **Filename** : slug ASCII basé sur le titre généré par Haiku — peut être imprécis si Haiku formule mal.
- **Pas de SessionStart hook pour l'instant** : Jarvis ne charge pas automatiquement le dernier récap au démarrage. À considérer en V2 si l'usage le justifie.
