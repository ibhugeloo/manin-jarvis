---
name: hook-post-sessiend-auto-critique-mos-002
auto: true
trigger: Chaque /exit Claude Code depuis example-app ou example-intake déclenche le check auto-critique
---

# Hook Post-SessionEnd — Auto-critique sur sessions client (MOS-002)

## Pourquoi
SOUL §5 exige l'auto-critique spontanée avant tout claim "prêt à tester". Incident 2026-05-07 (example-app V4) a montré qu'il fallait **industrialiser** ce check via un hook plutôt que de s'y fier à la mémoire.

## Procédure (résumée)
1. **Détection scope client** : CWD matche `GIT PROD/example-app/` ou `GIT PROD/example-intake/`.
2. **Check regex auto-critique** : `auto[- ]critique|qu.?est.?ce qui peut casser` sur le récap final.
3. **Cas OK** : streak `+1` en `~/.local/var/jarvis-mos-002-streak.txt`.
4. **Cas MISS** : 
   - Append section `## ⚠️ MOS-002 — Auto-critique manquante` au récap
   - Append observation `confidence: high` → `observations.md`
   - Push Telegram `🟡 MOS-002 — session <client> sans auto-critique (streak reset)`
   - Streak reseté à `0`
5. **Telemetry** : MOS event `MOS002_ok` / `MOS002_miss` → widget "Missions & events".

## Hook location
`bin/jarvis-session-recap.sh` lignes ~325–380 (bloc `## 6. MOS-002 auto-critique check`).

## Anti-patterns à éviter
- Ne pas matcher la regex sur les commentaires `<!-- auto-critique` (ça fausse le count).
- Ne pas baser le check sur le simple presence d'une section titrage — il faut le contenu (l'analyse 🔴/🟡/🟢).
- Ne pas oublier de reset le streak à `0` si MISS (sinon on compte des sessions consécutives incorrectes).
