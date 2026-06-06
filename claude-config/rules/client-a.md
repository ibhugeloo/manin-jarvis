---
paths:
  - "**/client-a/**"
  - "**/client-a-diagnostic/**"
  - "**/client-a-accueil/**"
  - "**/client-a-fleet/**"
  - "**/client-a-intranet/**"
  - "**/ClientA/**"
  - "**/Projects/client-a-*"
canonical_sources:
  - "Obsidian/vault/ClientA/_index.md"
  - "Obsidian/vault/Claude/Memory/decisions.md (E2E 2026-05-20)"
last_reviewed: 2026-06-06
---

# Rule projet — ClientA (client payeur)

Chargée mécaniquement quand je touche le code d'un repo `client-a-*`. Garde-fous durs ; source canonique = `Obsidian/ClientA/_index.md` + `decisions.md`.

- **Tâche de build/feature non-triviale → pipeline `/jarvis-ship`** (Research→Plan→Execute→Review→Ship gaté). Fix trivial / lecture / question → direct, pas de sur-process.
- **Client qui paye → auto-critique non-négociable** (SOUL §5) avant tout "prêt à pousser" : lister 🔴/🟡/🟢 ce qui peut casser, mitiger maintenant ce qui est mitigeable.
- **Tests E2E Playwright obligatoires** (decisions 2026-05-20) avant de considérer livrable : 1 flow/rôle + 1/feature critique + auth réelle. Typecheck + unit ≠ prêt prod. Cleanup via RPC SECURITY DEFINER, préfixes `E2E-`/`TEST-`.
- **Jamais de DELETE programmatique en prod** (API/SQL) — passer par le dashboard (agents.md §14).
- **Nom d'usage = "le boss", jamais "<surname>"** sur tout livrable client/public/RGPD/audit/email (profil.md). Le `git config user.name` légal ne fait pas foi.
- **Git client : email `you@example.com`** (agents.md §8) — sinon builds Vercel KO.
- **Données sensibles bénéficiaires (RGPD)** : signed URLs, bucket privé, pas de fuite en logs/Sentry. Vérifier l'intégration réelle, pas juste les tests unitaires.
- Lire `Obsidian/ClientA/_index.md` pour le contexte métier (diagnostic terrain, agents de terrain).
