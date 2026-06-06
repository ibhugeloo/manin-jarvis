---
name: watchtower
description: Surveillance santé prod des projets clients du boss (Agency). Croise Sentry + Vercel + Supabase + command center Agency par projet, calcule un status 🟢/🟡/🔴 et produit deux rapports (summary + detail) dans Obsidian/Watchtower/. Use when l'utilisateur demande "watchtower", "santé prod", "état des projets clients", "check prod", ou veut un audit de surveillance des projets en production.
---

# Skill — Watchtower (surveillance prod clients)

Savoir-faire de surveillance quotidienne des projets clients en prod. Version **interactive** (en séance, MCP déjà connectés). Le mode cron headless reste géré par `bin/jarvis-watchtower.sh` + `share/watchtower-prompt.md`.

Persona : vouvoiement, "boss", factuel, **zéro invention**. Source MCP en échec → `_(source indisponible)_`. Tout va bien → `_RAS_`, ne pas meubler.

## Étape 1 — Registre

Lire `~/Documents/GIT PROD/manin-jarvis/config/watchtower-projects.yaml`. Pour chaque projet sous `projects:` : `slug`, `name`, `client`, sous-sections `sentry`/`vercel`/`supabase`/`agency` (+ `enabled`), `red_thresholds`, `yellow_thresholds`, `ignore_supabase_advisors`. Si un argument projet est passé (`$ARGUMENTS`), ne traiter que celui-là.

## Étape 2 — Collecte par projet (sources en parallèle quand possible)

**Sentry** (`sentry.enabled`) : `find_projects` (org) → existence ; `search_issues` : `is:unresolved firstSeen:-24h` (nouvelles 24h), `is:unresolved` sort=freq limit=5 (top récurrentes), `is:unresolved level:error` (total). Retenir : nouvelles 24h, total unresolved, top 5.

**Vercel** (`vercel.enabled`) : `list_teams` → `list_projects` (matcher slug/nom) → `list_deployments` (statut + date du dernier deploy) ; si ERROR → `get_deployment_build_logs` (1-2 lignes) ; `get_runtime_logs` (erreurs 24h). Retenir : statut dernier deploy, date, erreurs runtime 24h.

**Supabase** (`supabase.enabled`) : `list_projects` (matcher `supabase.match_name`, ≠ base du command center Agency) → `get_advisors` security + performance → `get_logs` postgres/auth (erreurs 24h). **Filtrer** les advisors listés dans `ignore_supabase_advisors` AVANT de calculer les seuils ; les lister en bas du detail sous "Advisors ignorés".

**Command center Agency** (`agency.enabled`, ex-agency-app) : `list_projects` Supabase → base du command center Agency (cf. `reference_platform.md`) → `execute_sql` **lecture seule** sur `match_name` : statut projet + dernière version + feedbacks pending + heures non facturées. Jamais d'INSERT/UPDATE. Échec → `_(données Agency indisponibles)_`.
> ⚠️ Limite connue : la base du command center Agency (compte `you@example.com`) n'est **pas** reliée au MCP Supabase claude.ai → reconnaître la limite, ne pas bluffer. L'ancien domaine `agency-app` est **mort** (rebrand Agency, cf. `decisions.md` 2026-06-04).

## Étape 3 — Status par projet

- 🔴 si ≥1 `red_thresholds` dépassé (ex. `sentry_new_unresolved_24h` ≥ seuil ; `vercel_failed_deploy` ET dernier deploy ERROR ; `supabase_security_advisors` ≥ seuil)
- 🟡 si ≥1 `yellow_thresholds` dépassé (et pas 🔴)
- 🟢 sinon

## Étape 4 — Deux rapports via Write

Chemins : `~/Documents/Obsidian/vault/Watchtower/<YYYY-MM-DD>/summary.md` + `detail.md`.

`summary.md` (≤ 50 lignes, tient sur un écran) : accroche 1 phrase ; table `| Projet | Client | Status | Alertes critiques |` ; section `## Alertes 🔴 (à traiter aujourd'hui)` (ou `_RAS_`) ; `## Suggestion du jour` (2-3 lignes tranchantes, ou "Pas d'action client requise aujourd'hui, boss.").

`detail.md` : par projet `## <slug> — <client> — <status>` avec sous-sections `### Sentry` / `### Vercel` / `### Supabase` / `### Contexte Agency` / `### Action recommandée`. Pas de transcription brute. Aucun emoji hors template (🟢🟡🔴).

> ⚠️ Si `Watchtower/<date>/` existe déjà (run cron ou autre session), **ne pas écraser** `summary.md`/`detail.md` d'un run multi-projets avec un run ciblé : écrire un fichier suffixé (`<slug>-interactive.md`).

## Étape 5 — Restitution

En séance : annoncer le status global + pointer vers `Watchtower/<date>/`. Si ≥1 projet 🔴 : proposer le push Telegram (`jarvis-notify`) — **ne pas l'envoyer sans confirmation** (action externe, SOUL §2). En mode cron, c'est `jarvis-watchtower.sh` qui gère le push automatique sur 🔴.
