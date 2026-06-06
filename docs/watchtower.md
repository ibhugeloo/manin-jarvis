# Watchtower — surveillance quotidienne des projets clients

## But

Watchtower est un module **dédié aux projets clients qui paient** (Agency). Il est **strictement séparé** du brief perso de Jarvis pour ne pas mélanger le pro et le perso :

- **Brief perso** (`jarvis-brief`) → 7h30 → vie personnelle, calendrier, mails, repos perso, todos
- **Watchtower** (`jarvis-watchtower`) → 7h00 → santé prod des clients, alertes critiques, contexte business

> *"Pas une bonne idée d'attendre qu'il y ait un problème avant d'agir, et de mélanger le pro qui paye avec le reste de mes activités."* — le boss, 2026-05-07

## Pipeline

```
07:00 launchd
  └─ jarvis-watchtower.sh
       ├─ lit config/watchtower-projects.yaml
       ├─ pour chaque projet client :
       │    ├─ Sentry      → issues unresolved, top 5 récurrentes, nouvelles 24h
       │    ├─ Vercel      → dernier deploy, runtime errors 24h
       │    ├─ Supabase    → advisors sécu/perf, logs erreurs 24h
       │    └─ agency-app   → statut projet, dernière version, feedbacks pending, heures non facturées
       ├─ écrit summary.md (1 page) + detail.md (par projet) dans Obsidian/Watchtower/<date>/
       └─ pousse Telegram UNIQUEMENT si au moins un projet est 🔴
```

## Sortie quotidienne

```
~/Documents/Obsidian/vault/Watchtower/2026-05-07/
├── summary.md   # rapport simple, 1 écran, lisible en 30s
└── detail.md    # rapport détaillé, par projet, par source
```

### Format `summary.md`

- Phrase d'accroche
- Tableau status global (Projet | Client | 🟢/🟡/🔴 | Alertes)
- Section "Alertes 🔴" — actions à traiter aujourd'hui
- Suggestion du jour

### Format `detail.md`

Par projet :
- **Sentry** : nouvelles issues, total unresolved, top 5
- **Vercel** : statut deploy, erreurs runtime, logs si fail
- **Supabase** : advisors sécu/perf, erreurs Postgres/Auth
- **Contexte agency-app** : statut, dernière version livrée, feedbacks pending, heures non facturées, contact client
- **Action recommandée**

## Code couleur (par projet)

- 🟢 **Vert** : tout est calme. Pas d'action requise.
- 🟡 **Jaune** : signal faible (perf advisor, runtime errors > seuil, total unresolved > seuil). **Pas de Telegram**, juste rapport. À traiter dans la semaine.
- 🔴 **Rouge** : alerte critique. **Push Telegram immédiat.** À traiter aujourd'hui.
  - Nouvelle issue Sentry unresolved < 24h
  - Dernier deploy Vercel = ERROR
  - Advisor sécu Supabase

Les seuils sont configurables par projet dans `watchtower-projects.yaml` (`red_thresholds`, `yellow_thresholds`).

## Source de vérité des projets

Le fichier `config/watchtower-projects.yaml` est la liste autoritaire. Il est édité **à la main pour la phase 1** (1 seul projet : example-app).

> **Phase 2 (à venir)** : auto-discovery depuis agency-app. Le yaml sera regénéré automatiquement à partir de la table `projects` de agency-app filtrée sur `status IN ('delivered','iterating')`.

## Lien avec agency-app

Watchtower est **branché sur agency-app** comme source de contexte business. Pour chaque projet surveillé, il enrichit le rapport avec :
- Statut actuel du projet (`audit/brief/build/demo/iterating/delivered/closed`)
- Dernière version livrée + preview URL
- Feedbacks clients pending (à traiter)
- Heures non facturées (revenu à matérialiser)
- Email contact client

Cela permet au rapport de répondre non seulement à *"l'app plante-t-elle ?"* mais aussi à *"où en est-on commercialement avec ce client ?"*.

## Ajouter un nouveau projet client

1. Éditer `config/watchtower-projects.yaml` :

```yaml
projects:
  - slug: <slug-projet>
    name: <Nom long>
    client: <Nom client>
    paying: true
    repo: ~/Documents/GIT PROD/<slug-projet>
    obsidian_note: Claude/Projects/<slug-projet>.md
    description: >
      <2-3 lignes>
    deployed_at: YYYY-MM-DD
    status: production
    sentry:
      enabled: true
      org: <org-slug>
      project: <project-slug>
    vercel:
      enabled: true
      slug: <vercel-slug>
    supabase:
      enabled: true
      match_name: <nom partiel pour matcher dans list_projects>
    agency:
      enabled: true
      match_name: <nom partiel pour matcher dans la table projects de agency-app>
    red_thresholds:
      sentry_new_unresolved_24h: 1
      vercel_failed_deploy: true
      supabase_security_advisors: 1
    yellow_thresholds:
      sentry_unresolved_total: 5
      vercel_runtime_errors_24h: 10
      supabase_perf_advisors: 1
```

2. Re-lancer le bootstrap (le fichier YAML reste dans le repo, lu directement par Claude — pas besoin de copier dans `~/.local/share/`).

3. Tester immédiatement : `~/.local/bin/jarvis-watchtower.sh`

## Fichiers du module

| Fichier | Rôle |
|---|---|
| `bin/jarvis-watchtower.sh` | Script principal lancé par launchd |
| `share/watchtower-prompt.md` | Prompt LLM Opus avec instructions de collecte |
| `LaunchAgents/com.example.jarvis.watchtower.plist.template` | LaunchAgent, déclenchement 7h00 |
| `config/watchtower-projects.yaml` | Registre des projets clients à surveiller |

## Logs & debug

```bash
# Logs principaux
tail -f ~/.local/var/log/jarvis-watchtower.log

# Logs stdout/stderr du LaunchAgent
tail -f ~/.local/var/log/jarvis-watchtower.stdout.log
tail -f ~/.local/var/log/jarvis-watchtower.stderr.log

# Test manuel
~/.local/bin/jarvis-watchtower.sh

# Vérifier que le LaunchAgent est chargé
launchctl print "gui/$(id -u)/com.example.jarvis.watchtower"

# Recharger le LaunchAgent après modif
launchctl unload ~/Library/LaunchAgents/com.example.jarvis.watchtower.plist
launchctl load -w ~/Library/LaunchAgents/com.example.jarvis.watchtower.plist
```

## Limites connues V1

- Le yaml est édité à la main (phase 2 = auto-discovery depuis agency-app).
- Pas encore d'intégration dans le dashboard `jarvis-ui` (phase 3).
- Pas de rollup hebdomadaire ni mensuel (à voir si besoin émerge).
- Si Sentry/Vercel/Supabase MCP est down, Watchtower reporte gracieusement `_(source indisponible)_`. Pas de mécanisme de retry automatique côté MCP — c'est `claude-p-robust` qui gère les retries au niveau du modèle.

## Décisions structurantes

Voir `Claude/Memory/decisions.md` pour la trace de la décision *"Watchtower séparé du brief perso, push Telegram sur 🔴 uniquement, branché sur agency-app"*.
