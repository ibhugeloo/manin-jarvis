# Module Finance — Pilotage earnings du portefeuille (votre broker)

## Rôle

Module de **pilotage** (pas de production) du plugin Claude Code `finance-jarvis` (`~/Documents/GIT DEV/finance/finance-jarvis/`). Chaque matin à 6h00 (votre fuseau local), il :

1. Lit le calendrier earnings (`config/finance.yaml`)
2. Détecte les earnings **publiés depuis le dernier passage** non encore analysés
3. Déclenche pour chacun une analyse Carlson + Delmas (le plugin `earnings-plugin` fait le travail)
4. Écrit le rapport dans `~/Documents/Obsidian/vault/Holding/Earnings/<TICKER>-<DATE>.md`
5. Push Telegram un message synthétique avec l'**action concrète** par ticker

**Séparation claire** :
- `finance-jarvis/` (repo distinct, plugin Claude Code) = la mécanique d'analyse, `portfolio.yaml`, slash commands
- `manin-jarvis/` (ce module) = le pilote qui déclenche l'analyse au bon moment

## Architecture

```
~/Documents/GIT PROD/manin-jarvis/
├── bin/jarvis-finance.sh                      # orchestrateur (déployé vers ~/.local/bin/)
├── share/finance-prompt.md                    # prompt LLM (déployé vers ~/.local/share/jarvis/)
├── config/finance.yaml                        # calendrier earnings (lu en place)
├── LaunchAgents/com.example.jarvis.finance.plist.template
└── docs/finance.md                            # ce fichier
```

```
~/Documents/GIT DEV/finance/finance-jarvis/          # plugin Claude Code (repo séparé)
└── plugins/earnings-plugin/
    ├── portfolio.yaml                         # source de vérité positions + thèses
    ├── commands/                              # /earnings-watch, /earnings-calendar
    └── ...
```

```
~/Documents/Obsidian/vault/Holding/Earnings/    # output (FS = état persisté)
├── NVDA-2026-05-28.md
├── GOOG-2026-04-29.md
└── ...
```

## Workflow type

```
6h00 RE — launchd fire
  ↓
jarvis-finance.sh
  ↓ snapshot avant des notes existantes
  ↓ invoke claude --print --model opus avec finance-prompt.md
       ↓ Claude lit config/finance.yaml + portfolio.yaml du plugin
       ↓ filtre les earnings du jour ou passés sans note
       ↓ pour chaque ticker : WebFetch IR + WebSearch consensus + analyse
       ↓ Write <TICKER>-<DATE>.md dans Obsidian/Holding/Earnings/
  ↓ snapshot après → diff = nouvelles notes
  ↓ pour chaque nouvelle note :
     - extrait l'action concrète + 3 lignes de thèse
     - push Telegram via jarvis-notify
  ↓ notification macOS systématique
```

## Comment ajouter un earnings au calendrier

Quand une société du portefeuille annonce sa date d'earnings (sur son site IR ou via la presse) :

1. Ouvrir `~/Documents/GIT PROD/manin-jarvis/config/finance.yaml`
2. Ajouter sous `earnings_calendar:` :

```yaml
- ticker: NVDA              # doit matcher portfolio.yaml du plugin
  date: 2026-05-28          # date de publication officielle (YYYY-MM-DD)
  period: Q1 2027           # passé tel quel à l'analyse
  time: AMC                 # BMO | AMC | intraday
```

3. Commit + push (le repo `manin-jarvis` est versionné)
4. Le prochain run à 6h00 (ou immédiat via `~/.local/bin/jarvis-finance.sh`) prendra l'entrée en compte.

**Pas besoin de modifier le yaml manuellement après l'analyse** — l'état "déjà analysé" est déduit de la présence du fichier `<TICKER>-<DATE>.md` dans Obsidian. Le yaml peut donc rester avec toutes les entrées historiques sans grossir l'analyse (tout ce qui a déjà une note est skippé silencieusement).

## Run manuel (tests / rattrapage)

```bash
~/.local/bin/jarvis-finance.sh
```

Exécution synchrone, écriture dans `~/.local/var/log/jarvis-finance.log`. Idempotent : si toutes les notes existent déjà, sortie immédiate sans rien écrire.

## Activation

Comme tous les modules Jarvis, déployer via :

```bash
cd ~/Documents/GIT\ PROD/manin-jarvis
./bootstrap.sh
```

Le bootstrap copie `bin/jarvis-finance.sh` → `~/.local/bin/`, `share/finance-prompt.md` → `~/.local/share/jarvis/`, charge le LaunchAgent `com.example.jarvis.finance` dans `~/Library/LaunchAgents/`.

Vérifier le LaunchAgent :

```bash
launchctl list | grep finance
```

## Pourquoi 6h00 RE

- US AMC (after market close) = clôture US ~22h-1h RE → earnings sortis avant 6h RE ✓
- US BMO (before market open) = ouverture US ~15h30 RE → **non couvert**, pour V1 acceptable
- EU BMO (Hermès, etc.) = ~7h-8h Paris = ~9h-10h RE → **non couvert ce matin**, sera capturé au lendemain matin

V2 possible : ajouter un 2e fire à 22h00 RE pour capturer les earnings du jour. Dossier de réflexion uniquement, à valider avant de doubler la fréquence (coût Opus × 2/jour).

## Limites V1

- **Calendrier édité main** — pas d'auto-fetch du calendrier earnings depuis Yahoo/Investing. le boss met à jour le yaml par trimestre (28 entries/an pour 7 tickers, ~5 min de boulot par trimestre).
- **Une seule passe par jour** — earnings BMO US ratés ce matin, capturés J+1.
- **Sources publiques uniquement** — pas de FactSet/Daloopa (cohérent avec la philosophie du plugin `finance-jarvis`).
- **Pas de tracking prix continu** — V2 si besoin (alerte drawdown intraday, dividende coupé).

## Troubleshooting

| Symptôme | Diagnostic |
|---|---|
| Pas de fichier généré alors qu'un earnings est dans le yaml | Date `entry.date` > today, ou note `<TICKER>-<entry.date>.md` existe déjà. Vérifier `~/.local/var/log/jarvis-finance.log`. |
| Telegram pas reçu malgré nouvelle note | Vérifier `jarvis-notify` configuré (cf. `docs/telegram.md`). Test : `~/.local/bin/jarvis-notify "test"`. |
| LaunchAgent ne fire pas à 6h00 | `launchctl list \| grep finance` doit retourner la ligne. Sinon : `./bootstrap.sh`. Mac éteint à 6h00 → fire au prochain wake. |
| Erreur "claude binary not found" | Réinstaller Claude Code CLI. Vérifier `~/.local/bin/claude`. |
| Note générée mais incomplète (`_(source indisponible)_` partout) | IR site bloque WebFetch ou consensus introuvable via WebSearch. Vérifier manuellement, éventuellement compléter à la main et préfixer la note suivante via le prompt. |

## Ressources liées

- `~/Documents/GIT DEV/finance/finance-jarvis/README.md` — le plugin Claude Code et ses slash commands
- `Obsidian/vault/Files/investment_agent.md` — philosophie d'investissement Carlson/Delmas
- `Obsidian/vault/Claude/Memory/profil.md` (section Finance) — positions, stratégie, broker
- `~/Documents/GIT PROD/manin-jarvis/docs/watchtower.md` — module sœur (pattern identique pour les projets clients)
