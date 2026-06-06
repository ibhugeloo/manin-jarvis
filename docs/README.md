# Jarvis — Documentation des sous-systèmes

Doc technique des sous-systèmes Jarvis. Anciennement dans `Memory/reference_jarvis_*.md` ; déplacée ici le 2026-05-06 (cf. `lessons.md` § 18).

`Memory/` reste pour la mémoire cognitive (SOUL, profil, feedback, pointeurs externes). `docs/` est versionné avec le code qu'il documente.

## Index

### Cron / routines
- [brief-quotidien.md](brief-quotidien.md) — brief matinal 7h30
- [watchtower.md](watchtower.md) — surveillance projets clients 7h00 (séparé du brief perso)
- [routines.md](routines.md) — soir, hebdo, mensuel, evaluation
- [evaluation.md](evaluation.md) — auto-évaluation mensuelle
- [finance.md](finance.md) — analyse earnings portefeuille (votre broker)
- [memory-backup.md](memory-backup.md) — sync Memory/Sessions/Projects vers GitHub privé

### Outils CLI
- [status.md](status.md) — `jarvis-status` (vue groupe repos)
- [vault-search-v1.md](vault-search-v1.md) — recherche Haiku + ripgrep (legacy)
- [vault-search-v2.md](vault-search-v2.md) — recherche sémantique locale (sqlite-vec + e5)
- [dashboard.md](dashboard.md) — `jarvis-ui` sur localhost:7474

### Intégrations
- [telegram.md](telegram.md) — bot Telegram 24/7 + `jarvis-notify`
- [notion-mirror.md](notion-mirror.md) — export Notion vers vault

### Hooks Claude Code
- [session-recap.md](session-recap.md) — hook SessionEnd

### Majordomes
- [majordomes.md](majordomes.md) — vue d'ensemble Jarvis / Alfred / Leo (qui fait quoi, où, comment)
- [alfred.md](alfred.md) — wrapper Alfred (sysadmin homelab, Opus 4.7 via `--system-prompt`)
- [leo.md](leo.md) — Leo V2 (Hermes Agent, GPT-5.5 self-hosted) : contradicteur + majordome de secours, pair de Jarvis

### Qualité & régression
- [tests/doctrine/README.md](../tests/doctrine/README.md) — suite de régression comportementale (vouvoiement, refus bluff, confirmation actions, slot vide, git email projet client)

### Méta
- [deployment.md](deployment.md) — bootstrap.sh, structure, doctor
- [resilience.md](resilience.md) — claude-p-robust, auto-skills, plugins V1
