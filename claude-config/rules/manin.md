---
paths:
  - "**/agency-studio/**"
  - "**/agency-app/**"
  - "**/agency-website/**"
  - "**/Agency/**"
  - "**/Agency-app/**"
  - "**/Projects/agency-*"
canonical_sources:
  - "Obsidian/vault/Claude/Memory/reference_platform.md"
  - "Obsidian/vault/Agency/Index.md"
  - "Obsidian/vault/Agency-app/_index.md"
  - "Obsidian/vault/Claude/Memory/decisions.md (rebrand 2026-06-02 a 06-04)"
last_reviewed: 2026-06-06
---

# Rule projet — Agency (agence, ex-Agency)

Chargée quand je touche le code Agency. Source canonique = `Memory/reference_platform.md` + `decisions.md` 2026-06-02→06-04.

- **Infra cible (Phase 4 faite 2026-06-04)** : vitrine `agency.example` (repo `agency-website`) sur **Vercel** ; command center `app.agency.example` (repo `agency-app`, ex-`agency-app`) sur **Coolify homelab** derrière tunnel Cloudflare. `agency.example`/`agency-app`/`app-dev.agency.example` **morts** — ne plus les utiliser.
- **Gate pré-action externe** (SOUL §6.bis) : avant de dire "redéploie/pousse sur X", vérifier l'infra cible ci-dessus. Ne pas formuler en question ouverte une infra déjà documentée.
- **Gotcha Coolify prouvé** : PATCH fqdn avec `force_domain_override:true` → 500 SQL. Utiliser `{"domains":"..."}` seul.
- **Déployer sur le worker `apps-coolify`, jamais `localhost`** (l'orchestrateur = SPOF, decisions 2026-06-03).
- **Tâche de build/feature non-triviale → pipeline `/jarvis-ship`** (Research→Plan→Execute→Review→Ship gaté). Fix trivial / lecture / question → direct, pas de sur-process.
- **Client payeur en bout de chaîne → auto-critique SOUL §5 + E2E** comme tout projet client. Jamais de DELETE programmatique prod (agents.md §14).
- **MCP Supabase ne voit PAS la base `agency-app`** (compte `you@example.com` non relié) → reconnaître la limite, ne pas bluffer une query.
- Git client : email `you@example.com` (agents.md §8).
