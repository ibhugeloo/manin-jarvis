---
name: Jarvis-mobile — bot Telegram + notifications
description: Bridge Telegram ↔ Claude Code. Le bot reçoit les messages du boss et les passe à `claude -p`. CLI `jarvis-notify` permet aux scripts (briefs, routines) de pousser des notifs Telegram.
type: reference
---

Système ajouté le 2026-05-05.

## Composants

| Élément | Rôle |
|---|---|
| `jarvis-telegram-setup` | Setup interactif initial (BotFather → token → chat_id) |
| `jarvis-telegram-bot.py` | Bot Python en long-polling, lancé par launchd 24/7 |
| `jarvis-notify "<msg>"` | CLI one-shot pour pousser une notif Telegram |
| `share/telegram-system-prompt.md` | Persona/règles du bot pour les réponses |
| `~/.config/jarvis/telegram.env` | Token + chat_id (fichier sensible, chmod 600) |

## Première installation (à faire une fois par Mac)

```bash
# 1. Créer le bot dans Telegram via @BotFather → récupérer le token
# 2. Lancer le setup interactif
jarvis-telegram-setup
# 3. Suivre les étapes (envoyer /start au bot pour détecter le chat_id)
# 4. Re-lancer le bootstrap pour activer le LaunchAgent du bot
~/Documents/GIT PROD/manin-jarvis/bootstrap.sh
```

## Architecture

- **Long-polling** Telegram (pas de webhook) → pas besoin de serveur public, fonctionne depuis le Mac
- **Mac quasi 24/7** → bot toujours dispo. Si Mac éteint, le bot ne répond pas (limitation actuelle).
- **Authentification** : seuls les messages provenant du `CHAT_ID` configuré sont traités. Tout autre expéditeur est silencieusement ignoré.
- **Mémoire conversationnelle** : 5 derniers tours user/assistant gardés dans `~/.local/share/jarvis/telegram-history.jsonl`. `/clear` réinitialise.
- **Modèle utilisé** : Sonnet (compromis vitesse/qualité pour chat).

## Commandes du bot (texte commençant par `/`)

| Commande | Effet |
|---|---|
| `/start`, `/help` | Liste des commandes |
| `/status` | Sortie de `jarvis-status` |
| `/brief` | Brief matinal du jour |
| `/soir` | Récap soir du jour |
| `/clear` | Efface l'historique conversationnel |

Tout autre message → traité par Claude (avec MCPs, vault, etc.).

## CLI `jarvis-notify`

```bash
jarvis-notify "Hello, boss"                          # notif simple
jarvis-notify "*Important*" --markdown                # markdown Telegram
jarvis-notify "Sync OK" --silent                      # sans son/vibration
echo "long message" | jarvis-notify                   # depuis stdin
```

Utilisé par les scripts internes (jarvis-brief, jarvis-routine, notion-export) pour pousser leurs résultats sur Telegram.

## Cas d'usage typiques

- *"où en est ClientCo ?"* → `jarvis-status` côté ClientCo + actions ouvertes
- *"j'ai un RDV à quelle heure demain ?"* → Calendar lookup
- *"rappelle-moi ce qu'on a vu hier sur Jarvis"* → lit le dernier récap de session
- *"où sont mes credentials de la SCI Example ?"* → vault-search puis fallback Notion
- *"crée un draft mail au juriste pour annuler dimanche"* → crée un Gmail draft, demande validation

Le bot a accès à **tous les MCPs** (Notion, Gmail, Calendar, Drive, Supabase, Vercel) via `claude -p`. Il agit selon les règles de `feedback_action_proactive.md` (proactif sur les drafts, prudent sur les envois externes).

## Logs

```bash
tail -f ~/.local/var/log/jarvis-telegram-bot.log
```

## Désactiver temporairement

```bash
launchctl unload ~/Library/LaunchAgents/com.example.jarvis.telegram-bot.plist
# Réactiver
launchctl load -w ~/Library/LaunchAgents/com.example.jarvis.telegram-bot.plist
```

## Limites V1

- **Pas de vision** : seuls les messages texte sont traités. Photos/stickers/vocaux → réponse générique. À évoluer en V2 (Whisper local pour vocaux, Claude vision pour photos).
- **Mac dépendant** : si Mac éteint, bot inactif. Solution V2 : déployer sur le homelab Coolify.
- **Latence 5-15s** par message (overhead `claude -p`). Pas optimal mais acceptable pour chat.
- **Multi-Mac** : si bot tourne sur 2 Macs, les deux récupéreront chaque message. Recommandation : n'activer le LaunchAgent que sur **un** Mac.
