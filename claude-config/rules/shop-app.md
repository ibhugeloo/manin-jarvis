---
paths:
  - "**/shop-app/**"
  - "**/shop-app-shop/**"
  - "**/ShopApp/**"
  - "**/Projects/shop-app*"
canonical_sources:
  - "Obsidian/vault/ShopApp/_index.md"
  - "Obsidian/vault/Claude/Memory/dreams.md §4 (PAUSE)"
last_reviewed: 2026-06-06
---

# Rule projet — ShopApp (Pokémon)

Chargée quand je touche le code ShopApp. Source canonique = `Obsidian/ShopApp/_index.md` + `dreams.md §4`.

- **⏸️ PAUSE proactive depuis 2026-05-09** : ne RIEN suggérer/surveiller de proactif sur ShopApp. Actions ad hoc **seulement** sur demande explicite du boss (build, achat, vérif authenticité). Ne pas créer de mission MOS.
- **Infra** : front sur **Vercel**, base Supabase **self-hostée en VM dédiée sur Srv2** (migré du mutualisé apps-coolify le 2026-06-03), exposée via tunnel Cloudflare. Une VM = une base = ce projet.
- **Tâche de build/feature non-triviale → pipeline `/jarvis-ship`** (Research→Plan→Execute→Review→Ship gaté). Fix trivial / lecture / question → direct, pas de sur-process.
- **Client/perso payeur potentiel (boutique)** → si build : auto-critique SOUL §5, jamais de DELETE programmatique prod (agents.md §14).
- Git : email `you@example.com` (agents.md §8).
