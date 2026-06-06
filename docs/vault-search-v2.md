---
name: vault-search V2 — recherche sémantique vraie (sqlite-vec)
description: CLI `vault-search-v2` qui fait du cosine similarity sur des embeddings locaux (multilingual-e5-small) stockés dans sqlite-vec. Couvre les requêtes subtiles que la V1 (query-expansion + ripgrep) rate.
type: reference
---

Système ajouté le 2026-05-06.

## Usage

```bash
vault-search-v2 "<question>"            # top 10 résultats
vault-search-v2 "<question>" -k 5       # top 5
vault-search-v2 "<question>" -s vault   # filtre par source (vault, jarvis-repo-docs)
vault-search-v2 "<question>" --full     # affiche les chunks complets
vault-search-v2 "<question>" --json     # sortie JSON pour pipe
```

## Différence avec V1

| Aspect | V1 (`vault-search`) | V2 (`vault-search-v2`) |
|---|---|---|
| Méthode | Haiku génère keywords → ripgrep | Embedding local → cosine similarity |
| Latence cold start | 5-10s (claude headless + MCPs) | 5-8s (chargement modèle PyTorch) |
| Latence après | identique | identique |
| Couverture sémantique | ~70% (rate sans le bon mot) | ~95% (trouve par concept) |
| Coût | 1 appel Haiku par recherche | 0 (tout local) |
| Réseau requis | oui (API Claude) | non |

**Quand utiliser V1 vs V2** :
- V2 par défaut. Plus précis, gratuit, hors ligne.
- V1 si V2 down OU pour comparer.

## Exemples concrets

| Question | V1 trouve ? | V2 trouve ? |
|---|---|---|
| *"ma stratégie d'allocation PEA"* | ⚠️ rate si la note dit "pondération" | ✓ trouve `Ressources/investment-agent.md` |
| *"qu'est-ce qui me motive"* | ⚠️ trop abstrait | ✓ trouve `profil.md` + objectifs personnels |
| *"comment je gère mon homelab"* | ⚠️ rate si pas le mot "homelab" | ✓ trouve `Homelab/*.md` par concept |
| *"recettes mauriciennes"* | ✓ par mot exact | ✓ + autres notes liées (rougail, achards) |

## Composants

| Élément | Chemin |
|---|---|
| CLI wrapper | `~/.local/bin/vault-search-v2` (symlink) |
| CLI Python | `~/.local/bin/vault-search-v2.py` (copie, TCC) |
| Indexer | `~/.local/bin/jarvis-vault-index` (wrapper) + `.py` (copie) |
| Venv Python | `~/.local/share/jarvis/venv/` (~500 MB avec PyTorch) |
| DB | `~/.local/share/jarvis/vault.db` (sqlite-vec, ~5 MB pour 1000 chunks) |
| Modèle | cache HuggingFace : `~/.cache/huggingface/` (~470 MB) |
| LaunchAgent | `com.example.jarvis.vault-index` — cron quotidien 3h30 |
| Logs | `~/.local/var/log/jarvis-vault-index.log` |

## Indexation

- **Sources** : vault Obsidian complet (sauf `.obsidian/`, `.trash/`, `Brief/`) + `manin-jarvis/` (lessons.md, README, prompts) hors `memory/`, `sessions/`, `obsidian-projects/` (mirrors qui causeraient des doublons).
- **Chunking** : par paragraphe (`\n\n`), cap target 600 chars, max 1500. Frontmatter YAML strippé.
- **Embedding** : `multilingual-e5-small` (384 dims, FR/EN, prefix `passage:` pour docs et `query:` pour questions).
- **Incrémental** : la cron quotidienne ne réindexe que les fichiers dont `mtime` ET `hash` ont changé (évite les `touch` parasites).
- **Cleanup** : fichiers supprimés du filesystem sont retirés de la DB.

## Commandes utiles

```bash
# Stats
jarvis-vault-index --stats

# Full reindex (purge + recrée tout, ~30-60s)
jarvis-vault-index --full

# Voir le log
tail -f ~/.local/var/log/jarvis-vault-index.log

# Inspecter la DB directement
sqlite3 ~/.local/share/jarvis/vault.db
> SELECT source, COUNT(*) FROM files GROUP BY source;
```

## Quand Jarvis l'utilise

À privilégier sur V1 dans les sessions Claude Code, le bot Telegram, et les routines (briefs/évaluation). Si le boss demande *"où j'ai noté X"* ou *"qu'est-ce que je pense de Y"* : V2 d'abord.

V1 reste utile uniquement pour :
- Recherches d'identifiants exacts (UUID, email, nom de fichier) — utiliser `grep -r` directement
- Si la DB sqlite-vec est corrompue ou pas à jour — fallback temporaire

## Limitations

- **Cold start ~5-8s** au premier appel (chargement PyTorch + modèle). Les appels suivants dans la même session sont instantanés.
- **Modèle multilingual** : excellent en FR/EN mais peut être moins précis sur du jargon ultra-spécifique (ex: marques streetwear obscures).
- **Pas de filtres temporels natifs** : pour "notes des 30 derniers jours", filtrer après la recherche par `modified_at` du fichier.
- **TCC macOS** : si le cron planté avec "Operation not permitted", grant Full Disk Access au binaire Python du venv (~/.local/share/jarvis/venv/bin/python) dans System Settings → Privacy.

## Évolution V3 possible

- Filtres avancés : `vault-search-v2 "X" --since "30d" --tag "finance"`
- Re-ranking via Claude pour les top 5 (si on veut une réponse synthétisée plutôt qu'une liste)
- Hybrid search : combiner V1 (keyword) + V2 (semantic) avec score fusionné
- Indexer Telegram history pour retrouver les conversations passées par sens
