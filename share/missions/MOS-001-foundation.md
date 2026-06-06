---
id: MOS-001
title: Fonder le Mission Operating System (MOS)
status: done

opened_at: 2026-05-09
closed_at: 2026-05-09
deadline: 2026-05-16
parent_dream: manin-jarvis
deliverable: Daemon FastAPI sur 127.0.0.1:3737 qui (1) reçoit les events des hooks Claude Code, (2) reflète les missions markdown en DB SQLite+vec0, (3) expose GET /missions et GET /events/recent. Widget Control Room "MOS" affiche missions actives.
tags: [meta, mos, foundation]
---

# Fonder le Mission Operating System (MOS)

## Pourquoi
le boss a déjà 5 des 6 briques d'un Agentic OS (agents, mémoire, orchestration, hooks, UI).
La brique manquante est **Missions** — tâches bornées avec état persistant et deliverable.
Combler ce trou rend les LaunchAgents plus lisibles (chacun rattaché à une mission ouverte)
et donne un point d'agrégation aux events des hooks Claude Code (aujourd'hui éparpillés en logs).

## Définition de "done"
- [x] Schéma SQLite + sqlite-vec en place (events, missions, patterns, vec0)
- [x] DB layer testé (connect, insert event, vec0 OK)
- [x] Format mission markdown spec écrit (`_FORMAT.md`)
- [x] Bridge `missions_md.py` : scan filesystem → upsert DB
- [x] FastAPI `api.py` : POST /events, GET /missions, GET /events/recent
- [x] CLI `bin/jarvis-mos` (status/list/open/sync/events)
- [x] LaunchAgent `com.example.jarvis.mos.plist` KeepAlive sur 127.0.0.1:3737
- [x] `jarvis-hook-prompt-submit.sh` branché en best-effort POST /events
- [x] Bootstrap idempotent (déploie mos/ + wrappers + plist)
- [x] Décision 2026-05-09 ajoutée à `decisions.md`
- [ ] Widget "MOS" dans le Control Room (missions actives + 5 derniers events) — reporté V1.1

## Plan
1. **Phase 0** ✅ — venv (fastapi/uvicorn), schema.sql, db.py, smoke test
2. **Phase 1** — format mission + 2 missions pilotes (cette mission + MOS-002)
3. **Phase 2** — `mos/api.py` + `mos/missions_md.py` (bridge filesystem ↔ DB)
4. **Phase 3** — CLI `jarvis-mos` + LaunchAgent daemon
5. **Phase 4** — brancher `jarvis-hook-prompt-submit.sh` (best-effort, silent-fail si daemon down)
6. **Phase 5** (futur) — widget Control Room + auto-promotion observations→patterns

## Journal
- 2026-05-09 00:50 — Mission ouverte. le boss valide architecture (daemon, markdown primary, méta uniquement, drop coûts Opus).
- 2026-05-09 00:55 — Phase 0 livrée : schema.sql + db.py + smoke test OK. sqlite-vec confirmé dispo dans `~/.local/share/jarvis/venv`.
- 2026-05-09 01:00 — Phase 1 livrée — format spec + 2 missions pilotes (MOS-001, MOS-002).
- 2026-05-09 01:30 — Phase 2 livrée — api.py + missions_md.py + tests in-process FastAPI (TestClient) tous green.
- 2026-05-09 02:00 — Phase 3 wip — port 3000 occupé par node Next.js, switch vers 3737. CLI + LaunchAgent installés.
- 2026-05-09 02:13 — TCC discovered : daemon launchd hang sur `os.scandir(~/Documents/GIT PROD/.../share/missions/)`. Stack confirme `__open_nocancel`.
- 2026-05-09 02:18 — Refactor : daemon ne touche plus `~/Documents/`. Sync via CLI utilisateur (a Full Disk Access). Daemon healthy.
- 2026-05-09 02:20 — Phase 4 livrée — `jarvis-hook-prompt-submit.sh` branché best-effort (curl --max-time 1 silent-fail).
- 2026-05-09 02:22 — Bootstrap idempotent updated (déploie mos/, wrappers, plist). Re-run validé : daemon healthy, 4 events / 2 missions.
- 2026-05-09 02:23 — Mission close. Widget Control Room reporté V1.1.

## Notes

**Architecture validée** :
```
Claude Code → hook shell → POST 127.0.0.1:3000/events → SQLite (events)
                                                       ↘
share/missions/*.md (source vérité) → missions_md.py → SQLite (missions + vec0)
                                                       ↗
                                  Control Room widget ← GET /missions
```

**Décisions** :
- Source de vérité = markdown filesystem (Obsidian-friendly, inspectable, git-friendly)
- DB = miroir reconstructible (jamais d'écriture directe en DB pour modifier une mission, on édite le `.md`)
- vec0 dim = 384 (multilingual-e5-small, cohérent avec vault-search-v2)
- Périmètre V1 = méta Jarvis uniquement. Missions clients restent dans Supabase agency-app.
- Pas de tracking coûts Opus (le boss s'en fout).
