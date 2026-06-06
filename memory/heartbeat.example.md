# HEARTBEAT — flotte de routines

> **Template.** Copiez en `heartbeat.md`. Décrit les **routines automatiques** (cron / launchd)
> et le **dispatcher manuel**. C'est la carte de ce qui tourne tout seul vs ce que vous lancez.

---

## Principe

Distinguez deux régimes :
- **Routines qui invoquent le LLM** (coûtent des tokens) → à garder rares et transparentes.
- **Daemons locaux** (indexation, dashboard, bot) → ne coûtent rien, peuvent tourner en continu.

> Leçon courante : un cron LLM qui tourne en arrière-plan gonfle la consommation sans que
> vous le voyiez. Préférez le **déclenchement manuel** par défaut, et n'automatisez que ce qui
> apporte un signal actionnable régulier.

## Routines (exemples)

| Routine | Cadence | Coût LLM | Sortie |
|---|---|---|---|
| `<brief matinal>` | <quotidien> | oui | <note du jour> |
| `<revue hebdo>` | <dimanche> | oui | <note hebdo> |
| `<auto-évaluation>` | <tous les N jours> | oui | <note eval> |
| `<surveillance prod>` | <quotidien> | oui | <alerte si 🔴 seulement> |
| `<indexation notes>` | <horaire> | non | <index> |
| `<sauvegarde mémoire>` | <quotidien> | non | <commit git privé> |

## Dispatcher manuel

Un point d'entrée unique pour lancer les routines à la demande, ex. :

```bash
<assistant> jour | hebdo | eval | watchtower | ...
```

## Garde-fous

- Tout hook qui rappelle le LLM doit avoir une **garde anti-récursion**.
- Gating de cadence (ex. "ne pas relancer si < N jours depuis le dernier run").
- launchd/cron rattrape les runs manqués si la machine dormait — en tenir compte.

---

> **Comment customiser :** commencez **sans aucune routine LLM automatique**. Lancez tout à la
> main pendant quelques semaines. N'automatisez qu'une routine quand vous constatez que vous la
> lancez de toute façon tous les jours.
