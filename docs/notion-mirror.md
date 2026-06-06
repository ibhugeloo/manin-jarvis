---
name: notion-export — mirror Notion → vault
description: Cron quotidien (6h30) qui exporte en Markdown les pages Notion listées dans `notion-pages.txt` vers `~/Documents/Obsidian/vault/Notion-Mirror/`. Permet à vault-search de couvrir aussi Notion.
type: reference
---

Système ajouté le 2026-05-05 (squelette ; liste des pages à compléter par le boss).

## Pourquoi

Le MCP Notion a des limites structurelles (cf. `reference_notion_second_cerveau.md`) :
- Wikis databases : `notion-fetch` renvoie le schéma, pas le corps
- Recherche sémantique partielle (highlights tronqués)

Solution : **mirror local** des pages stratégiques de Notion vers le vault. Une fois en local, `vault-search` les retrouve aussi bien que les notes Obsidian natives, et `grep`/`find` fonctionnent dessus.

## Configuration

le boss désigne les pages à mirrorer en éditant :

```
~/Documents/GIT PROD/manin-jarvis/notion-pages.txt
```

Une URL ou un ID Notion par ligne. Les lignes vides et `#` sont ignorées.

**Recommandations** (à appliquer avec le boss au moment du peuplement) :
- Cibler les pages **sensibles** (credentials, contacts, codes) — c'est là que vault-search est aujourd'hui aveugle
- Cibler les pages **consultées souvent**
- Pour les bases (databases), mettre l'URL de la base — le script exporte les pages enfants directs (max 50)

## Schedule

- **Tous les jours 6h30** (avant le brief matinal de 7h30, pour que vault-search ait des données fraîches)
- LaunchAgent : `com.example.jarvis.notion-export`

## Sortie

```
~/Documents/Obsidian/vault/Notion-Mirror/
├── _sync-status.md                 # status du dernier run
├── <page-slug>.md                  # une page = un fichier
└── <db-slug>/                      # une database = un dossier
    └── <child-slug>.md
```

Chaque fichier inclut un **frontmatter** :
```yaml
---
source: notion
notion_url: https://...
notion_id: <UUID>
title: <titre original>
last_synced: YYYY-MM-DD HH:MM
---
```

## Commandes

```bash
# Lister ce qui serait exporté (sans rien faire)
notion-export.sh --dry-run

# Forcer un export immédiat
notion-export.sh

# Logs
tail -f ~/.local/var/log/jarvis-notion-export.log

# Status du dernier sync
cat ~/Documents/Obsidian/vault/Notion-Mirror/_sync-status.md
```

## Limites connues

- **Notion API rate limits** : 3 req/sec pour les utilisateurs gratuits. Si liste > 50 pages, le script peut être lent.
- **Pages en lecture seule pour le boss** : si une page Notion est partagée avec lui mais qu'il n'en est pas propriétaire, l'export peut échouer selon les permissions du token Notion attaché au MCP.
- **Pas de delta sync** : chaque run écrase tout. Si le boss édite un mirror localement, les changements seront écrasés au prochain run.
- **Slugs dépendants du titre** : si le boss renomme une page Notion, le slug changera et le fichier sera dupliqué (l'ancien restant orphelin). À nettoyer manuellement.

## Effet de bord positif

Une fois le mirror peuplé, **vault-search couvre Notion**. Le trou XiVO/credentials est comblé : tout ce qui est sensible vit en local et reste interrogeable même hors connexion.
