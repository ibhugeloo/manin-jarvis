---
id: MOS-002
title: Industrialiser l'auto-critique sur tout livrable client agency-app
status: wip
opened_at: 2026-05-09
closed_at:
deadline:
parent_dream: agency-co
deliverable: Avant tout claim "prêt à tester" sur un projet client, l'auto-critique format SOUL §5 (🔴/🟡/🟢 + ce qui est fixé maintenant) est produite spontanément, vérifiable a posteriori dans le récap de session.
tags: [agency, quality, soul]
---

# Industrialiser l'auto-critique sur tout livrable client agency-app

## Pourquoi
Cf. SOUL §5 et lessons.md — incident 2026-05-07 V4 example-app : claim "prêt à tester"
sur la base de typecheck+lint+tests sans aucune couverture intégration réelle. le boss a dû
demander "qu'est-ce qui peut casser ?" pour obtenir l'analyse. Le format est défini dans SOUL
mais pas encore systématiquement appliqué — cette mission rend l'application traçable.

## Projets client en scope (2026-05-13)
- `example-app`
- `example-intake`

_Liste resserrée par le boss le 2026-05-13. Toute ouverture de nouveau client = ajout dans `CLIENT_PROJECTS` du hook + ici._

## Définition de "done"
- [x] Hook `SessionEnd` détecte les sessions qui ont touché un projet client (`GIT PROD/<projet-client>/` via `CWD` ou grep transcript) et vérifie que le récap contient une section auto-critique.
- [x] Si absente : nudge dans le récap Notion + observation `observations.md` confidence:high + push Telegram.
- [ ] 3 sessions consécutives avec auto-critique présente sur projet client → mission close.

## Plan
1. ✅ Identifier la liste des projets clients (resserrée à `example-app` + `example-intake`).
2. ✅ Enrichir `jarvis-session-recap.sh` : détection scope client + grep auto-critique + nudge + observation + Telegram + streak counter + emit MOS event.
3. ⏳ Observer la prochaine session client réelle pour validation runtime.
4. ⏳ Activer en prod (déjà déployé — actif au prochain `/exit` sur projet client).
5. ⏳ Compter 3 occurrences validées (streak file : `~/.local/var/jarvis-mos-002-streak.txt`) → close.

## Détection technique
- **Scope client** : `CWD` matche `GIT PROD/<client>/` OU le transcript contient `GIT PROD/<client>/`.
- **Présence auto-critique** : regex `auto[- ]critique|qu.?est.?ce qui peut casser` (insensitive) sur le récap markdown final.
- **Streak** : compteur fichier persistant. +1 sur hit, reset à 0 sur miss. À 3 → notify macOS + log.
- **Telemetry** : MOS event `MOS002_ok` ou `MOS002_miss` avec le projet client en payload.

## Journal
- 2026-05-09 01:05 — Mission ouverte en parallèle de MOS-001 pour démontrer le concept "missions méta".
- 2026-05-13 00:43 — Liste client resserrée à 2 projets. Étape 2 codée et déployée dans `bin/jarvis-session-recap.sh` (+74 lignes). Tests : `zsh -n` OK + dry-run manuel.

## Notes
Dépend de MOS-001 pour le suivi formel (la mission peut être ouverte/trackée même sans MOS,
mais le widget Control Room la rendra visible). Pas bloquante, peut démarrer après MOS-001 close.
