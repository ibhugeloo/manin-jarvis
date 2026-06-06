---
description: Audit stack & sécurité d'un projet en prod (invoque le skill stack-security-audit en séance)
---

# /jarvis-audit — audit stack & sécurité en séance

Rend le workflow d'audit (aujourd'hui un script/skill hors-séance) **orchestrable en conversation**. Cible : `$ARGUMENTS` (nom du projet, ex. `client-a-diagnostic`).

Pattern Command → Skill :

1. Charger la doctrine du projet (rule `~/.claude/rules/<projet>.md` + WARM si besoin).
2. Invoquer le skill **`stack-security-audit`** sur la cible : croiser versions installées vs dernières stables, CVE (GitHub Advisories / `npm audit` / Supabase advisors), erreurs Sentry actives, runtime Vercel.
3. Produire un rapport priorisé **🔴 critique / 🟡 à surveiller / 🟢 mineur** avec fixes concrets.
4. Écrire le rapport dans `Obsidian/Watchtower/<projet>/<date>-stack-audit.md`.
5. **Corrections déclaratives et minimales** (préférence le boss, cf. leo-feed) : override explicite dans `package.json` plutôt que `npm audit fix` large. Ne rien appliquer en prod sans validation.

Pour la prod client : ne jamais conclure "safe" sur la seule base d'un typecheck. Vérifier l'exploitabilité réelle.
