---
name: Routines Jarvis (soir, hebdo, mensuel)
description: 3 nouvelles routines automatiques en complément du brief matinal. Soir 19h00, hebdo dimanche 18h00, mensuel 1er du mois 9h00. Pilote `jarvis-routine.sh <type>`.
type: reference
---

Système ajouté le 2026-05-05.

## Schedule

| Routine | Quand | Fichier produit |
|---|---|---|
| **brief** (matin) | tous les jours 7h30 | `Brief/YYYY-MM-DD.md` |
| **soir** | tous les jours 19h00 | `Brief/YYYY-MM-DD-soir.md` |
| **hebdo** | dimanche 18h00 | `Brief/YYYY-Www-hebdo.md` |
| **mensuel** | 1er du mois 9h00 | `Brief/YYYY-MM-mensuel.md` |

Toutes les heures sont en votre fuseau local (adapt to your timezone). launchd rattrape automatiquement si le Mac dormait au moment prévu.

## Différenciation des contenus

- **Brief matinal** : tactique pur, du jour. Calendar, mails, repos en attente, suggestion immédiate.
- **Récap soir** : bilan de la journée + setup demain (RDVs, prep mentale).
- **Hebdo** : stratégique. Agrégation 7 jours, sujets dominants, recommandations pour la semaine à venir.
- **Mensuel** : très stratégique. Bilan financier (limité tant qu'votre broker pas connecté), avancement projets, objectifs personnels (liberté financière, épargne, santé). Question ouverte de fond.

Chaque prompt charge la **mémoire transverse Jarvis** au démarrage (rôle, profil, précision).

## Composants

| Élément | Chemin |
|---|---|
| Runner générique | `~/.local/bin/jarvis-routine.sh` (symlink → vault) |
| Prompt soir | `~/.local/share/jarvis/routine-soir-prompt.md` |
| Prompt hebdo | `~/.local/share/jarvis/routine-hebdo-prompt.md` |
| Prompt mensuel | `~/.local/share/jarvis/routine-mensuel-prompt.md` |
| LaunchAgent soir | `~/Library/LaunchAgents/com.example.jarvis.routine-soir.plist` |
| LaunchAgent hebdo | `~/Library/LaunchAgents/com.example.jarvis.routine-hebdo.plist` |
| LaunchAgent mensuel | `~/Library/LaunchAgents/com.example.jarvis.routine-mensuel.plist` |
| Logs | `~/.local/var/log/jarvis-routine.log` |

## Commandes

```bash
# Test manuel
~/.local/bin/jarvis-routine.sh soir
~/.local/bin/jarvis-routine.sh hebdo
~/.local/bin/jarvis-routine.sh mensuel

# Désactiver une routine
launchctl unload ~/Library/LaunchAgents/com.example.jarvis.routine-soir.plist

# Logs
tail -f ~/.local/var/log/jarvis-routine.log
```

## Évolution

Pour ajouter une nouvelle routine `<type>` :
1. Créer le prompt `~/Documents/GIT PROD/manin-jarvis/share/routine-<type>-prompt.md`
2. Créer le plist `~/Documents/GIT PROD/manin-jarvis/LaunchAgents/com.example.jarvis.routine-<type>.plist.template`
3. Re-lancer `bootstrap.sh` → tout est déployé automatiquement

Le runner `jarvis-routine.sh` est générique : il lit `routine-$TYPE-prompt.md` selon l'argument reçu.
