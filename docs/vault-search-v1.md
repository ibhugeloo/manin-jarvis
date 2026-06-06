---
name: vault-search — recherche sémantique légère sur le vault
description: CLI qui expand une requête en langage naturel via Claude Haiku puis lance ripgrep sur le vault Obsidian. À utiliser à la place de grep/find quand la formulation peut différer.
type: reference
---

Outil mis en place le 2026-05-05.

## Usage

```bash
vault-search "<question en langage naturel>"
```

Exemples :
- `vault-search "où sont mes credentials d'alternance"`
- `vault-search "trail à Mafate"`
- `vault-search "comment je gère les backups Proxmox"`

## Fonctionnement

1. Le script demande à **Claude Haiku** (`claude -p --model haiku`) de générer 10 termes connexes courts (synonymes, abréviations, jargon).
2. Construit un pattern alterné (`terme1|terme2|...`).
3. Lance `ripgrep` sur le vault avec smart-case + contexte ±1 ligne, exclut `.obsidian/`, `.trash/`, `Brief/`.
4. Retourne les hits avec fichier + numéro de ligne.

Latence typique : 5-10 secondes (l'essentiel vient du chargement de claude headless).

## Quand l'utiliser (à la place de grep/find)

- Recherche par **concept** plutôt que par mot exact (ex : *"sécurité réseau homelab"* trouvera des notes parlant de VLAN, firewall, iptables).
- Quand on suspecte qu'le boss a noté l'info avec une formulation différente (jargon, abréviation, ancien nom).
- Première passe avant de tomber sur grep/find si le vocabulaire est connu.

## Quand NE PAS l'utiliser

- Recherche d'un nom de fichier précis → `find`.
- Recherche d'un identifiant exact (UUID, email, ID Notion) → `grep -r`.
- Recherche dans Notion → utiliser `mcp__claude_ai_Notion__notion-search` (limites connues : voir `reference_notion_second_cerveau.md`).

## Limites

- **Ne lit pas Notion** : si l'info n'est qu'en Notion, ce script renvoie vide. C'est attendu.
- **Pas de vrai sémantique** : la recherche reste à base de grep, donc *"déménagement"* ne matchera pas littéralement *"je quitte mon appart"* sauf si l'expansion de Claude Haiku produit la bonne variante. Couvre 70% des cas.
- **Coûte une requête Haiku** par appel (négligeable mais non nul).

## Composants

| Élément | Chemin |
|---|---|
| Script | `~/.local/bin/vault-search` |
| Dépendances | `claude` (CLI), `ripgrep` (`brew install ripgrep`) |

## Évolution future (V2)

Si la précision devient insuffisante : passer à un vrai RAG local avec `sentence-transformers` (modèle `multilingual-e5-small`, ~470 MB), embeddings stockés en SQLite, ré-indexation par cron. Multiplie par 3-5x la pertinence pour les requêtes subtiles.
