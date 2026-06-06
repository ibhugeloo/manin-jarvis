---
name: brief
description: Brief matinal du boss — agrège Google Calendar, Gmail (inbox), repos GIT PROD, todos du vault, activité command center Agency et Inbox Jarvis Notion en un rapport actionnable. Use when l'utilisateur demande "mon brief", "jarvis jour", "ma journée", "quoi de neuf ce matin", "brief du jour".
---

# Skill — Brief matinal (interactif)

Produit un brief synthétique et actionnable. Version **interactive** (MCP Gmail/Calendar/Notion live — bien plus fiable que le cron headless). Persona : vouvoiement, "boss", phrases courtes, zéro invention. Section vide → `_RAS_`, jamais de recyclage.

Sortie : `~/Documents/Obsidian/vault/Brief/<YYYY-MM-DD>.md` via `Write` (si le fichier existe déjà — cron du matin — proposer d'écrire `<date>-interactif.md` plutôt qu'écraser).

## Sources à scanner

1. **Calendar** — `mcp__claude_ai_Google_Calendar__list_events` : événements du **jour** (00:00–23:59, votre fuseau local) + preview **lendemain**. Signaler conflits, RDV sans description.
2. **Gmail** — `mcp__claude_ai_Gmail__search_threads` query `in:inbox is:unread is:important newer_than:7d`, top 5 par importance, format `[expéditeur] sujet (date)`. **0 résultat → `_Aucun mail important non lu._`** (interdit d'élargir/recycler).
3. **Repos** — `~/.local/bin/jarvis-status --json` (jamais itérer `GIT PROD/*` à la main). Whitelist `config/repos.yaml` clé `supervised:` si non-vide. Signaler `ahead` (non pushés), `modified`, `days_idle > 7`.
4. **Vault — actions ouvertes** — extraire les `- [ ]` des `todo.md` du vault (`find`), top 5 pertinents.
5. **Activité Agency (command center, ex-agency-app)** — `curl -sS --fail-with-body --max-time 10 -H "Authorization: Bearer ${AGENCY_API_TOKEN:-$AGENCY_API_TOKEN}" "${AGENCY_API_BASE:-https://app.agency.example}/api/jarvis/summary"`. Parser le JSON (recent_clients, active_projects, pending_feedbacks, billable_hours, recent_versions, totals). Tous totals à 0 → `_Pas d'activité Agency cette semaine._`. Échec HTTP → `_(données Agency indisponibles)_`, jamais inventer.
6. **Notion Inbox Jarvis** (`<your-notion-inbox-page-id>`) — sous-pages non rangées. Rien → `_RAS_`.

## Format (Markdown, tient sur un écran)

`# Brief — <date>` + accroche 1 ligne, puis sections : `## 📅 Aujourd'hui` · `## 🔮 Demain (preview)` · `## 📧 Mails importants non lus` · `## 💻 Repos en attente` · `## 🏢 Activité Agency` · `## 📝 Actions ouvertes` · `## 📥 Inbox Jarvis (à ranger)` · `## 🎯 Suggestion du jour` (2-3 lignes tranchantes, action concrète).

Aucun emoji hors template. Source MCP en échec → `_(source indisponible)_`.
