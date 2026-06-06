# Memory — index

> **Template.** Copiez ce fichier en `MEMORY.md` et remplissez-le.
> C'est l'**index auto-chargé** à chaque session : une ligne par fichier mémoire,
> jamais de contenu ici (le contenu vit dans les fichiers pointés).

Cet index permet à l'assistant de savoir *qu'un fait existe* avant d'aller le lire.

## Fichiers HOT (auto-chargés à chaque session)

- [jarvis_soul.md](jarvis_soul.md) — persona, ton, autonomie, garde-fous
- [profil.md](profil.md) — qui vous êtes (identité, préférences, contexte)
- [decisions.md](decisions.md) — choix structurants datés (source de vérité anti-contradiction)
- [agents.md](agents.md) — workflows opérationnels (comment l'assistant travaille)
- [tools.md](tools.md) — inventaire des capacités (MCP, scripts, limites)
- [dreams.md](dreams.md) — objectifs long-terme (2-10 ans)

## Fichiers WARM (chargés à la demande, selon le contexte)

> Listez ici les fichiers contextuels (un par projet, un par domaine) avec leur trigger.
> Ex. : `- [reference_projet-x.md] — charger quand cwd = projet-x ou sujet "projet-x"`

## Convention

`type: user | feedback | project | reference` — voir `agents.md §9` pour le système
de promotion d'un fait observé vers un fichier mémoire durable.
