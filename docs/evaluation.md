---
name: Auto-évaluation Jarvis (cycle 4 jours)
description: Routine cron qui auto-analyse la qualité de Jarvis tous les 4 jours, détecte des patterns à mémoriser, et propose des améliorations.
type: reference
---

Système ajouté le 2026-05-05. **Cadence passée de mensuel → 4 jours le 2026-05-07** (cf. `decisions.md`).

## Schedule

- **Tous les 4 jours à 23h00** (votre fuseau local)
- LaunchAgent : `com.example.jarvis.routine-evaluation` — fire **quotidien à 23h00**, le script gate sur "≥ 4 jours depuis le dernier run" via `~/.local/var/jarvis-routine-evaluation-last-run`
- Sortie : `~/Documents/Obsidian/vault/Brief/YYYY-MM-DD-evaluation.md` (un fichier par cycle, pas d'overwrite)
- Modèle : `claude --model opus`

## Pourquoi cette cadence (et pas StartInterval)

Le LaunchAgent fire chaque jour à 23h00, le script `jarvis-routine.sh` décide. Avantages :
- Heure prévisible (23h00 fixe, pas de drift)
- Survit aux reboots / Mac en veille (launchd reschedule au prochain wake)
- Bypass manuel facile : `JARVIS_ROUTINE_FORCE=1 jarvis-routine.sh evaluation`
- Modifier la cadence = un seul chiffre dans `jarvis-routine.sh` (`gate_min_seconds`)

## Ce qui est analysé (fenêtre 5 derniers jours)

1. **Statistiques d'usage** du cycle (sessions Claude, briefs/soirs générés, projet le plus travaillé)
2. **Erreurs récurrentes détectées** : violations des règles de `lessons.md` dans les transcripts
3. **Règles correctement appliquées**
4. **Audit structurel `Memory/`** (anti-drift, doublons, orphelins)
5. **Patterns à enregistrer en mémoire** : seuil **3+ occurrences strict** sur la fenêtre
6. **Suggestions d'amélioration** (1-2, plus court qu'en mensuel)
7. **Hygiène venv Python** (critiques uniquement)
8. **Score qualité** décomposé : structurel / comportemental / opérationnel
9. **Question ouverte** à le boss pour orienter le prochain cycle

## Auto-écriture des skills (pas de validation préalable)

Décision 2026-05-06 — pour tout pattern récurrent (3+ occurrences sur la fenêtre 5j), Jarvis écrit directement dans `Memory/auto/<DATE>_<slug>.md` avec frontmatter `auto: true`. Review au cycle suivant pour promotion vers `Memory/feedback_*.md` ou purge.

**Exception** : conflit avec une décision existante de `decisions.md` → arbitrage le boss requis (lister dans "Question à le boss").

## Déclencher manuellement (bypass du gating 4j)

```bash
JARVIS_ROUTINE_FORCE=1 ~/.local/bin/jarvis-routine.sh evaluation
```

Sans `JARVIS_ROUTINE_FORCE=1` : si dernier run < 4j, le script log "skip" et exit 0 sans rien faire.

## Logs

```bash
tail -f ~/.local/var/log/jarvis-routine.log
```

## Désactiver

```bash
launchctl unload ~/Library/LaunchAgents/com.example.jarvis.routine-evaluation.plist
```

## Pourquoi c'est important

Sans ce mécanisme, Jarvis :
- Répète les mêmes erreurs sans s'en rendre compte
- N'enrichit sa mémoire que lorsqu'le boss y pense explicitement
- N'a pas de feedback objectif sur sa qualité

Avec, et **avec une cadence 4j au lieu de mensuelle** :
- Boucle d'apprentissage ~7,5× plus rapide qu'en mensuel
- Patterns détectés sous 5j max au lieu de 30j max
- Bruit absorbé par `Memory/auto/` (séparé de la mémoire validée) + audit cycle suivant
- Coût marginal négligeable (1 run Opus tous les 4j ≈ 7-8 runs/mois)

C'est le compromis "Hermes-like sans la surcharge" décidé après analyse des outils tiers (cf. décision 2026-05-07).
