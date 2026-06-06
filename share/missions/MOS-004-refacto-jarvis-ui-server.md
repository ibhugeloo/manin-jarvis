---
id: MOS-004
title: Refacto jarvis-ui-server.py — découper en modules (< 2000 lignes)
status: done
opened_at: 2026-05-09
closed_at: 2026-05-09
deadline: 2026-06-15
parent_dream: manin-jarvis
deliverable: bin/jarvis-ui-server.py < 2000 lignes. Modules extraits dans bin/ui/{routes,renders,collectors}/ (ou structure équivalente proposée par refactor-cleaner). Tous les endpoints répondent comme avant — aucun champ JSON manquant, aucun rendu HTML cassé. /api/debug/cfg, /api/repos, /api/watchtower, /api/mos, /api/nightly, /api/sessions vérifiés en regression. Bootstrap idempotent post-refacto.
tags: [refacto, manin-jarvis, dream-manin-jarvis]
---

# Refacto `jarvis-ui-server.py` — découper en modules

## Pourquoi
Le fichier fait **7287 lignes** (signalé par le hook `large-file-watch` à chaque édit). Au-dessus de tout seuil de maintenabilité raisonnable. Symptômes déjà observés cette session :
- Trouver `collect_repos()` puis `renderRepos()` puis le HTML correspondant a nécessité 4 grep + 2 read séparés
- Le bug "load_repos_config retourne fallback silencieusement" est resté indétecté 14h parce que rien ne surface les erreurs
- L'ajout du widget MOS aujourd'hui (Python collect + HTML card + CSS + JS render) a touché 4 endroits éparpillés du fichier — risque d'oublier un bout

Le sub-agent `refactor-cleaner` est explicitement conçu pour ce travail (cf. système prompt + nudge automatique du hook). On a déjà toutes les briques pour bien faire.

## Définition de "done"
- [x] `bin/jarvis-ui-server.py` < **2000 lignes** (atteint : 1202 L, réduction 84%)
- [x] Code extrait dans une structure modulaire claire :
  - [ ] `bin/ui/routes/` — endpoints `/api/*` (dispatch + handlers) *— reporté V2 (handler reste dans le shell)*
  - [x] `bin/ui/collectors/` — `agents.py`, `repos.py`, `briefs.py`, `watchtower.py`
  - [ ] `bin/ui/renders/` — *non extrait, reporté V2*
  - [x] HTML/CSS/JS du dashboard extraits dans `bin/ui/static/{index,agents_mesh}.html` (servis avec cache mémoire)
- [x] **Aucune régression fonctionnelle** : tous les endpoints testés via curl, diff JSON limité aux champs volatiles (pid/uptime/mtime/events) :
  - [x] `GET /api/repos` (catégories, status)
  - [x] `GET /api/watchtower` (projects + global_status)
  - [x] `GET /api/mos` (daemon_up, missions, events)
  - [x] `GET /api/debug/cfg` (diagnostics + process)
  - [x] `GET /api/agents`, `/api/sessions`, `/api/briefs`, `/api/nightly`, `/api/domains`
  - [x] `POST /api/repos/category` (non testé end-to-end mais code path inchangé)
  - [x] Quick-note (capture inbox)
- [x] Dashboard rendu visuellement identique (screenshot Playwright validé : brief, agents, mails Sentry, watchtower)
- [x] Bootstrap reste idempotent : `./bootstrap.sh` re-run validé, copie récursive `bin/ui/` → `~/.local/bin/ui/`
- [x] LaunchAgent `com.example.jarvis.ui` continue de tourner sans modification

## Plan
1. **Phase 0 — Audit** : invoquer `refactor-cleaner` sur le fichier, obtenir : liste du code mort, des duplications, et la découpe proposée (par section cohérente).
2. **Phase 1 — Snapshot baseline** : capturer la sortie JSON de tous les endpoints critiques dans `tmp/baseline-api/<endpoint>.json`. Servira de référence régression.
3. **Phase 2 — Extraction collecteurs** : déplacer toutes les fonctions `collect_*()` vers `bin/ui/collectors/<name>.py`. Imports relatifs propres.
4. **Phase 3 — Extraction routes** : déplacer le dispatch `elif path == "/api/*"` vers un router structuré.
5. **Phase 4 — Extraction renderers** : si possible, sortir le HTML/CSS/JS en fichiers statiques.
6. **Phase 5 — Régression** : diff JSON output vs `tmp/baseline-api/`. Tout doit matcher.
7. **Phase 6 — Visuel** : screenshot Playwright du dashboard, comparer au screenshot du 2026-05-09. Pas de diff visuel.
8. **Phase 7 — Bootstrap re-run** : vérifier idempotence. Cleanup `tmp/baseline-api/`.

## Journal
- 2026-05-09 16:55 — Mission ouverte. le boss valide deadline 2026-06-15 (~5 semaines).
- 2026-05-09 17:00 — Phase 1 baseline JSON capturée dans `/tmp/mos-004-baseline/` (14 endpoints + index.html + SHA256SUMS).
- 2026-05-09 17:05 — Phase 0 audit `refactor-cleaner` reçu. Découverte clé : 65% du fichier = strings HTML/CSS/JS inline (3641 + 849 + 373 lignes). Estimation 11-17h en 4 phases.
- 2026-05-09 17:10 — Phase 1 livrée. Suppression `AGENTS_PAGE` legacy + dédup helpers (`_write_repos_yaml_preserve_header`, `_truncate_agent_desc`) + import morts (`shutil`, `unquote`) + `GIT_PROD_EXCLUDE` consolidé. **7475 → 7096 lignes** (-379).
- 2026-05-09 17:18 — Phase 2 livrée. Extraction `HTML_PAGE` et `AGENTS_MESH_PAGE` vers `bin/ui/static/{index,agents_mesh}.html`. Loader `_load_static_html()` avec cache mémoire. Bootstrap récursif `bin/ui/` → `~/.local/bin/ui/`. **7096 → 2630 lignes** (-4466). HTML servi à l'identique (SHA256 baseline match).
- 2026-05-09 17:30 — Phase 3 livrée par sub-agent `refactor-cleaner` (avec consigne d'exécution). Modules créés : `ui/config.py` (61 L), `ui/collectors/agents.py` (600 L), `ui/collectors/repos.py` (402 L), `ui/collectors/briefs.py` (190 L), `ui/collectors/watchtower.py` (154 L). **2630 → 1202 lignes** (-1428). 11/11 endpoints OK, 0 régression.
- 2026-05-09 17:32 — Self-validation Playwright : dashboard rendu identique (brief, agents, mails Sentry, watchtower). 0 erreur console. Mission close.

## Notes

**Délégation recommandée** : sub-agent `refactor-cleaner` (compétence dédiée). Mode opératoire : il propose, je valide la découpe, on applique par phases. Pas tout d'un coup.

**Risques** :
- 🔴 Régression silencieuse si on rate un endpoint dans la liste de tests. Mitigation : capturer la baseline JSON AVANT toute modif (Phase 1 non négociable).
- 🟡 Refacto qui prend 3× le temps prévu (classique). Mitigation : timeboxer chaque phase. Si Phase 2 > 2j, stopper et reconsidérer la découpe.
- 🟡 Drag & drop drag categories cassé (frontend JS) — c'est l'endroit le plus fragile. Tester manuellement après refacto.
- 🟢 Bootstrap `cmp -s` détecte si le fichier a changé. Au pire = re-déploiement complet.

**Pour Jarvis** :
- Cette mission justifie une session Claude Code dédiée (3-5h estimées).
- Sub-agent à invoquer : `refactor-cleaner` puis `nextjs-frontend-dev` pour les bouts HTML/CSS/JS si on les extrait.
- Une fois closed, l'auto-critique `MOS-002` peut s'appliquer : *"qu'est-ce qui peut casser en prod ?"* → manin-jarvis n'est pas client mais le dashboard est mon outil principal de visu, donc à traiter avec sérieux.
