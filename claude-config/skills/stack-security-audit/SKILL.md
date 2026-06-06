---
name: stack-security-audit
description: Audit complet de sécurité + obsolescence des dépendances d'un projet déjà en production. Croise versions installées avec dernières releases stables, CVE GitHub Advisories / npm audit / pip-audit / Supabase advisors, erreurs Sentry actives, et runtime Vercel pour produire un rapport priorisé (🔴 critique / 🟡 à surveiller / 🟢 mineur) avec fixes concrets. À déclencher PROACTIVELY quand l'utilisateur dit : "audit la stack de X", "vérifie si <projet> est à jour", "health-check sécurité <projet>", "stack-audit", "CVE sur <projet>", "dépendances obsolètes", "le projet est-il toujours safe en prod", "patch security <projet>", "<projet> est en retard sur quoi". Sortie standardisée dans Obsidian/Watchtower/<projet>/<date>-stack-audit.md.
---

# Stack Security Audit — projets en production

Objectif : pour un projet d'`~/Documents/GIT PROD/`, produire un rapport actionnable qui répond à 3 questions :

1. **Sécurité** — y a-t-il des CVE actives sur les dépendances installées ?
2. **Obsolescence** — quelles deps sont en retard de majeure / mineure, avec quel risque de drift ?
3. **Santé prod** — Sentry/Vercel/Supabase signalent-ils déjà des symptômes liés à ces deps ?

**Lecture par défaut. Aucune commande qui modifie le projet (`npm install`, `npm update`, `pip install -U`) sans validation explicite du boss.**

---

## 1. Prérequis avant de lancer

Demander/confirmer si pas évident :

- **Projet cible** : nom du dossier dans `~/Documents/GIT PROD/`. Si ambigu, lister via `jarvis-status --json` et demander.
- **Branche** : `main` par défaut. Si le projet a une branche de release distincte, le mentionner.
- **Périmètre** : tout le repo, ou un sous-module précis (ex. juste le frontend d'un monorepo).

Si le projet ne tourne pas en prod (statut `audit`/`brief`/`build` dans agency-app), **dire-le** au boss avant de lancer — l'audit a moins de valeur sur un projet pas encore exposé.

---

## 2. Phase 1 — Inventaire stack

Détecter le langage et les manifests :

| Stack | Manifests à lire | Commande locale |
|---|---|---|
| Node/JS/TS | `package.json` + `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` | `npm outdated --json`, `npm audit --json` |
| Python | `requirements.txt` / `pyproject.toml` / `poetry.lock` / `Pipfile.lock` | `pip list --outdated --format=json`, `pip-audit --format=json` (si installé) |
| Rust | `Cargo.toml` + `Cargo.lock` | `cargo outdated --format json`, `cargo audit --json` |
| Go | `go.mod` + `go.sum` | `go list -u -m -json all`, `govulncheck ./...` |
| Ruby | `Gemfile` + `Gemfile.lock` | `bundle outdated --parseable`, `bundle audit check` |
| PHP | `composer.json` + `composer.lock` | `composer outdated --format=json`, `composer audit --format=json` |
| Docker | `Dockerfile`, `docker-compose.yml` | Lire base images et versions épinglées |

**Lister aussi** :
- Version runtime (`.nvmrc`, `.python-version`, `engines` dans `package.json`)
- Framework principal et version (Next.js, React, Django, Rails, etc.)
- DB et version (PostgreSQL via Supabase, MySQL, etc.)

Si une commande locale n'est pas installée, **ne pas tenter de l'installer** — noter "outil X non disponible, fallback via lecture du lockfile + GitHub Advisories".

---

## 3. Phase 2 — Cross-référencer les sources externes

### 3.a — CVE & advisories

Pour chaque dépendance jugée critique (framework, lib auth, lib crypto, parser, lib HTTP, ORM, DB driver) ou pour toute entrée flaggée par `npm audit` / `pip-audit` :

1. **GitHub Advisory Database** via WebFetch : `https://github.com/advisories?query=<package>` — vérifier que la version installée n'est pas dans une plage `Affected`.
2. Pour les CVE confirmées, récupérer : sévérité (Critical / High / Moderate / Low), version corrigée, vecteur d'exploit (RCE, XSS, prototype pollution, DoS…), si exploit public connu.
3. **Ignorer** les advisories qui s'appliquent à un mode d'usage non utilisé dans le projet (ex. CVE sur `lodash.template` mais le projet n'utilise que `lodash.merge`).

### 3.b — Versions stables actuelles

Pour les deps majeures, vérifier la dernière release stable et la roadmap :
- `https://www.npmjs.com/package/<pkg>` ou registry équivalent
- Notes de release des 2-3 dernières majeures (breaking changes à anticiper)
- Pour Next.js / React / Tailwind / shadcn : lire le changelog des `.x` récentes — patterns de regression connus.

### 3.c — Santé prod via MCP

- **Sentry** (`mcp__claude_ai_Sentry__search_issues`) : issues `unresolved` des 7 derniers jours sur le projet. Croiser le stack trace avec les deps audités — si une lib X est dans la stack trace d'une erreur active, **monter sa priorité d'un cran**.
- **Vercel** (`mcp__claude_ai_Vercel__get_runtime_logs`, `list_deployments`) : derniers builds échoués + erreurs runtime des dernières 24h sur le deployment de prod.
- **Supabase** (`mcp__claude_ai_Supabase__get_advisors` avec `type='security'` et `type='performance'`) : si le projet utilise Supabase, lister les advisors actifs. RLS désactivée, indexes manquants, search_path mutable, etc.

---

## 4. Phase 3 — Classification & priorisation

Chaque finding va dans une catégorie unique. Tie-breaker : si doute, monter d'un cran (mieux vaut sur-alerter qu'oublier un risque sécu).

### 🔴 Critique — fix dans les 48h

Critères (un seul suffit) :
- CVE Critical/High **et** la dep est utilisée dans un code path exposé (auth, parsing input utilisateur, network)
- Sentry montre une erreur active probablement liée à une dep obsolète
- Supabase Security advisor actif (RLS manquante sur table sensible, function search_path injection-able)
- Runtime Node/Python EOL atteint ou < 30j de la fin de support
- Lib auth (NextAuth, Passport, Devise) avec patch dispo

**Format** :
```
🔴 <pkg>@<version installée> → <version cible>
   CVE-XXXX-YYYY (Critical) — <résumé exploit en 1 ligne>
   Impact sur ce projet : <code path concret OU "exposé via /api/X"> 
   Fix : <commande exacte> + <breaking changes à valider OU "aucun, patch mineure">
   Effort : <S/M/L>
```

### 🟡 À surveiller — fix dans le mois

Critères :
- CVE Moderate ou High mais sur un code path non exposé
- Majeure de retard sur framework (Next 14 → 15, React 18 → 19) avec features deprecated activement utilisées
- Mineure de retard avec breaking change documenté qui touche le projet
- Performance advisor Supabase
- Dep avec < 6 mois sans release et alternative recommandée

### 🟢 Mineur — backlog, traçabilité

Critères :
- Patches purs (X.Y.Z avec Z bumped) sans CVE
- Minor releases sans breaking change utilisé
- Devdeps obsolètes sans impact runtime

---

## 5. Phase 4 — Plan d'action concret

Pour chaque 🔴 et 🟡, fournir le **fix exact** :

- Commande à lancer (`npm install pkg@1.2.3`, `pip install "pkg>=1.2.3"`)
- Si breaking : lien vers le guide de migration officiel + diff prévisible sur le projet (grep des usages dans le repo)
- Si pas d'auto-fix possible (lib abandonnée) : alternative recommandée + scope du switch

Regrouper les patches sûrs en **un seul bloc copiable** "fixes triviaux à appliquer maintenant" — le boss peut le coller, lancer les tests, commit.

Séparer les majors en **propositions individuelles** avec section "Avant / Après" et "Tests à refaire".

**Ne JAMAIS** lancer `npm install`, `pip install -U`, `cargo update`, etc. Le skill s'arrête au plan.

---

## 6. Format de sortie

Écrire dans `~/Documents/Obsidian/Watchtower/<projet>/<YYYY-MM-DD>-stack-audit.md`. Créer le dossier si inexistant.

```markdown
# Stack Audit — <projet> — YYYY-MM-DD

## TL;DR
- 🔴 N findings critiques
- 🟡 N findings à surveiller
- 🟢 N findings mineurs
- Verdict : <safe / action requise / urgent>

## Contexte
- Repo : ~/Documents/GIT PROD/<projet>
- Branche auditée : <main / release-X>
- Stack détectée : <Next.js 15.x + Supabase + Resend ...>
- Dernier deploy prod : <date Vercel>
- Sentry : <N issues unresolved>

## 🔴 Critique
<format §4>

## 🟡 À surveiller
<format §4>

## 🟢 Mineurs
<liste compacte, une ligne par finding>

## Plan d'action immédiat
### Patches triviaux à appliquer maintenant
```bash
<bloc copiable>
```

### Majors à planifier (un par section)
**<framework> N → N+1**
- Effort : <S/M/L>
- Breaking changes pertinents : <liste>
- Tests à refaire : <liste>
- Guide officiel : <URL>

## Sources consultées
- npm audit : <date snapshot>
- GitHub Advisories : <packages vérifiés>
- Sentry : <issues IDs>
- Supabase advisors : <count>
- Vercel runtime : <fenêtre>

## Prochaine review suggérée
<date+30j si verdict safe, +7j si action requise>
```

---

## 7. Garde-fous

- **Lecture seule** : aucune modification du repo. Pas de `npm install`, pas de commit, pas de PR auto.
- **Pas d'install d'outils** : si `pip-audit`/`cargo-audit`/`govulncheck` manque, fallback documentation + GitHub Advisories, et noter la limite dans le rapport.
- **Reconnaître la limite** quand un MCP est indispo : si Sentry/Vercel MCP ne renvoient rien sur ce projet, écrire explicitement "Sentry non connecté pour ce projet" plutôt que conclure "RAS prod".
- **Honnêteté sur la couverture** : si l'audit n'a pas pu vérifier une dep faute d'info, la mettre dans une section "Non auditées" plutôt que la classer 🟢 par défaut.
- **agency-app exception** : la base Supabase de agency-app n'est pas reliée au MCP claude.ai (cf. `reference_platform.md`). Si projet = agency-app, sauter le bloc Supabase advisors et l'écrire dans le rapport.

---

## 8. Quand suggérer une cadence récurrente

Si le boss audite un projet pour la 3ème fois ou plus, proposer (sans imposer) :

> *"Boss, ce projet a été audité 3 fois ce trimestre. Voulez-vous l'ajouter à `config/watchtower-projects.yaml` avec une cadence stack-audit mensuelle automatique ?"*

Ne pas créer la cadence automatiquement — c'est une modification du heartbeat (cf. `heartbeat.md`).

---

## 9. Mode rapide vs mode profond

le boss peut préciser :

- **Quick** (*"quick audit"*, *"audit rapide"*) : seulement `npm audit` + `npm outdated` + 3 deps les plus critiques croisées avec GitHub Advisories + Sentry 24h. Pas de Vercel/Supabase. ~3 min.
- **Standard** (défaut) : §2 → §5 complet sur les deps importantes (~10 deps). ~10 min.
- **Deep** (*"audit profond"*, *"deep audit"*) : toutes les deps de prod (devdeps incluses pour les gros risques type webpack/vite/typescript), runtime, CI configs, Docker base images. ~30 min, à réserver aux audits trimestriels.

Annoncer le mode choisi avant de lancer.
