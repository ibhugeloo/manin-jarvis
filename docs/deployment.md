---
name: Jarvis deployment — bootstrap portable multi-Mac
description: Stack Jarvis (brief, vault-search, session-recap, dashboard, telegram-bot, routines) packagée comme repo Git dans `~/Documents/GIT PROD/manin-jarvis/` avec un bootstrap.sh idempotent qui déploie/met à jour/désinstalle. Utiliser pour installer Jarvis sur une nouvelle machine.
type: reference
---

Système mis en place le 2026-05-05.

## Localisation

**Source canonique de toute la stack Jarvis** : `~/Documents/GIT PROD/manin-jarvis/`

Comme le vault Obsidian est synchronisé entre les Mac, cette source est disponible partout. Le `bootstrap.sh` lit cette source et déploie localement.

## Structure du dossier Jarvis

```
~/Documents/GIT PROD/manin-jarvis/
├── bootstrap.sh                      # script de déploiement
├── README.md
├── bin/
│   ├── jarvis-brief.sh
│   ├── jarvis-session-recap.sh
│   └── vault-search
├── share/
│   └── brief-prompt.md
├── LaunchAgents/
│   └── com.example.jarvis.brief.plist.template   # __HOME__ substitué à l'install
└── claude-config/
    ├── CLAUDE.md.imports.txt          # bloc balisé BEGIN/END pour ~/.claude/CLAUDE.md
    └── settings.hooks.json            # hook SessionEnd pour fusion dans settings.json
```

## Déploiement sur une nouvelle machine

```bash
cd ~/Documents/GIT PROD/manin-jarvis
./bootstrap.sh
```

Pré-requis : Mac, Claude Code installé, Homebrew, vault Obsidian synchronisé.
Le script installe automatiquement `ripgrep` si absent.

## Modes du bootstrap

| Commande | Effet |
|---|---|
| `./bootstrap.sh` | Installe ou met à jour (idempotent). |
| `./bootstrap.sh --doctor` | Diagnostic complet, n'écrit rien. |
| `./bootstrap.sh --uninstall` | Retire symlinks et hooks. Préserve toutes les données du vault. |

## Mécanique

- **Scripts et prompt** : `~/.local/bin/jarvis-*` et `~/.local/share/jarvis/brief-prompt.md` sont des **symlinks** vers la source canonique. Toute édition de la source prend effet immédiatement.
- **LaunchAgent plist** : copié (avec substitution de `__HOME__`) dans `~/Library/LaunchAgents/`. Re-bootstrapper après modification du template.
- **`~/.claude/settings.json`** : fusion non destructive du hook `SessionEnd` via `jq -s '.[0] * .[1]'`. Backup `.bak.YYYYMMDD-HHMMSS` créé.
- **`~/.claude/CLAUDE.md`** : bloc balisé `# === BEGIN JARVIS IMPORTS / END ===` injecté en tête. Backup créé. Bloc remplacé proprement à chaque re-run.

## Quand re-bootstrapper

- Après modification du template plist (`LaunchAgents/*.template`)
- Après ajout/retrait d'une mémoire transverse (mettre à jour `claude-config/CLAUDE.md.imports.txt` puis re-run)
- Après modification de `claude-config/settings.hooks.json`

Les modifications dans `bin/` ou `share/` ne nécessitent **pas** de re-bootstrap (symlinks).

## Multi-Mac : précaution

Si l'utilisateur déploie Jarvis sur plusieurs Mac, le LaunchAgent du brief 7h30 risque de s'exécuter sur **chaque** machine simultanément, ce qui peut créer des conflits sur `Brief/YYYY-MM-DD.md` via Obsidian Sync. Recommandation : n'activer le brief que sur **un** Mac à la fois (`launchctl unload` sur les autres).

## Gotchas connus

- **`launchctl list | grep -q` + `set -e -o pipefail`** : SIGPIPE de launchctl tue le pipe avec exit 141, ce qui le fait échouer. Le bootstrap utilise `launchctl print "gui/$UID/<label>"` à la place.
- **Username différent** : tout est paramétré via `$HOME` / `__HOME__`. Pas de hardcode de `youruser`.
- **Vault non synchro** : le bootstrap échoue proprement (exit 1) avec un message clair.
