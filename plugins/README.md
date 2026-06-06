# Jarvis plugins — convention V1

> Inspiré du plugin system de Hermes Agent (Nous Research). Architecture modulaire pour ajouter des capacités sans toucher au core de Jarvis.

## Pourquoi

Aujourd'hui les composants Jarvis (briefs, routines, vault-search, telegram-bot, etc.) vivent à plat dans `bin/`, `share/`, `LaunchAgents/`. Ça marche mais ne scale pas : si demain on ajoute 5 nouvelles capacités (ShopApp workflow, Apple Health bridge, votre broker live, Pushover, etc.), `bin/` devient un fourre-tout.

La convention **plugin** isole chaque capacité dans son propre dossier, avec ses propres scripts/prompts/cron/mémoires. Le core de Jarvis reste minimaliste et stable.

## Structure d'un plugin

```
plugins/<nom-du-plugin>/
├── plugin.yaml              # metadata (description, type, hooks, deps)
├── prompts/                 # fragments markdown injectables dans les routines
│   └── *.md
├── commands/                # scripts CLI exposés (copiés vers ~/.local/bin/)
│   └── *.sh ou *.py
├── routines/                # LaunchAgents (cron jobs) du plugin
│   └── *.plist.template
├── memory/                  # règles auto-loadées en mémoire transverse
│   └── *.md
└── README.md                # doc du plugin
```

## Format `plugin.yaml`

```yaml
name: shop-app
version: 0.1.0
description: Workflows métier pour la boutique TCG du boss
author: your-name
type: business  # core | business | personal | experimental

# Quand le plugin est-il actif ?
enabled: true

# Plugins requis (chargés avant celui-ci)
depends_on:
  - core

# Commandes exposées (chemins relatifs au plugin)
commands:
  - commands/jarvis-shop-app-add.sh
  - commands/jarvis-shop-app-ship.py

# Cron jobs à enregistrer
launch_agents:
  - routines/shop-app-daily-stock-check.plist.template

# Fragments de prompts injectés dans les routines core
prompt_injections:
  - target: brief-prompt.md
    section: business
    file: prompts/shop-app-brief-fragment.md

# Mémoires à auto-loader dans CLAUDE.md
memory:
  - memory/shop-app-conventions.md

# Variables d'environnement requises
env_required:
  - STRIPE_API_KEY    # documenté, pas stocké
```

## Cycle de vie

1. **Discovery** : le bootstrap scanne `plugins/*/plugin.yaml` au démarrage
2. **Resolution** : ordonne par `depends_on` (graphe topologique)
3. **Install** : pour chaque plugin enabled :
   - Copie `commands/*` → `~/.local/bin/`
   - Render + load `routines/*.plist.template` → `~/Library/LaunchAgents/`
   - Append `memory/*` au bloc imports `CLAUDE.md`
   - Inject `prompts/*` dans les fragments correspondants des prompts core
4. **Doctor** : vérifie qu'aucun plugin n'a de conflit (commande dupliquée, etc.)
5. **Uninstall** : `bootstrap.sh --uninstall-plugin <nom>` pour retirer proprement

## État actuel — V1 lite

**Ce qui est fait** :
- Convention documentée (ce README)
- Structure `plugins/` créée
- Plugin exemple `example-skeleton/` qui montre la forme

**Ce qui n'est PAS fait** :
- Le bootstrap ne **discover** pas encore les plugins automatiquement
- Le core Jarvis (briefs, telegram-bot, etc.) n'est **pas migré** en plugins
- Pas de mécanisme `plugin_injections` (les prompts core n'ont pas encore de placeholders `__INCLUDE: ...__`)

**Pourquoi V1 lite** :
- Évite un refacto destructif d'un système qui marche
- Pose les rails pour quand un nouveau besoin émergera (ShopApp, Apple Health, votre broker live)
- Le premier "vrai" plugin servira de validation de la convention

## Prochains plugins à monter (ordre indicatif)

1. **`plugins/ibkr/`** (Tier S #1) — pull votre broker positions via `ib_insync`, push dans le brief
2. **`plugins/shop-app/`** (Tier S #4) — workflows métier de la boutique TCG
3. **`plugins/voice/`** (Tier S #2) — Whisper local pour transcription vocale Telegram
4. **`plugins/homelab/`** (Tier A) — healthcheck SSH des VMs Proxmox
5. **`plugins/health/`** (Tier A) — bridge Apple Health → vault

Chaque plugin sera autonome et désactivable. Le core reste léger.

## Nommage

- `<nom>` en `kebab-case`, court et descriptif
- Préfixe pour les groupes : `business-shop-app`, `personal-health`, etc. (optionnel)
- Pas d'overlap entre plugins sur les commandes exposées (le bootstrap warn sinon)

## Comment contribuer un plugin

1. Créer `plugins/<nom>/plugin.yaml` minimal
2. Ajouter ce qu'on veut (commands, routines, memory, prompts)
3. Tester en isolation : copier manuellement les fichiers vers `~/.local/bin/` etc.
4. Quand le bootstrap aura le support plugins (V2), il fera tout automatiquement.
