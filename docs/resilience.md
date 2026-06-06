---
name: claude-p-robust + auto-skills + plugin system V1 (inspirations Hermes)
description: Trois mécaniques inspirées d'Hermes Agent intégrées à Jarvis le 2026-05-06. Wrapper robust, auto-création de skills, convention plugin system.
type: reference
---

Système ajouté le 2026-05-06.

## 1. Wrapper `claude-p-robust.sh`

**But** : protéger les routines critiques (briefs, mensuel, etc.) contre les hoquets API Claude.

**Comportement** :
- 2 retries avec backoff exponentiel (5s, 10s)
- Fallback de modèle : Opus → Sonnet → Haiku
- Log structuré dans `~/.local/var/log/claude-p-robust.log`
- Notif Telegram si échec définitif après tous les modèles

**Usage** : drop-in replacement pour `claude -p`. Les scripts core (jarvis-brief, jarvis-routine, notion-export) l'utilisent automatiquement avec fallback sur `claude -p` direct si le wrapper est absent.

## 2. Auto-création de skills (extension session-recap)

**But** : que Jarvis détecte automatiquement les patterns/résolutions valant la peine d'être enregistrés en mémoire, sans qu'le boss le demande.

**Mécanique** :
- À chaque `SessionEnd`, le hook `jarvis-session-recap.sh` analyse le transcript
- Si la session contient une résolution non triviale (5+ tool calls, erreur résolue, pattern récurrent), Claude propose un draft de skill séparé par `<<<SKILL>>>`
- Le draft est écrit dans `~/Documents/Obsidian/vault/Claude/Memory/proposed/<slug>.md`
- Notif Telegram silencieuse à le boss : *"📚 Skill proposé : ..."*

**Workflow le boss** :
1. Voir notif Telegram
2. Aller dans `Memory/proposed/` du vault
3. Si pertinent : éditer + déplacer dans `Memory/` (devient permanent)
4. Si non pertinent : supprimer

C'est la version "auto-mémoire active" promise dans `feedback_action_proactive.md`, désormais déclenchée systématiquement.

## 3. Plugin system V1 lite

**Convention documentée dans** : `~/Documents/GIT PROD/manin-jarvis/plugins/README.md`

**État V1** :
- Structure documentée (squelette `plugins/example-skeleton/`)
- Le core de Jarvis n'est PAS migré en plugins (ça marche, on n'y touche pas)
- Le bootstrap ne discover pas encore les plugins automatiquement (V2)

**Quand un nouveau plugin est utile** :
- Capacité métier (ShopApp workflows, votre broker live, Apple Health)
- Capacité optionnelle (voice in/out via Whisper)
- Intégration externe (Stripe, Coolify, etc.)

**Forme attendue** :
```
plugins/<nom>/
├── plugin.yaml          # metadata
├── prompts/             # fragments injectables
├── commands/            # CLI exposés
├── routines/            # cron LaunchAgents
├── memory/              # règles auto-loadées
└── README.md
```

Quand le bootstrap V2 saura discover, les plugins seront automatiquement déployés. En attendant, structure documentée pour ne pas avoir à inventer la convention le jour où un vrai besoin émerge.
