# TOOLS — capacités de l'assistant

> **Template.** Copiez en `tools.md`. Sert de **checklist mentale** pour que l'assistant
> n'oublie pas ce qu'il sait faire — et reconnaisse ce qu'il **ne peut pas** faire (anti-bluff).
> Mettez à jour quand vous branchez un nouvel outil.

---

## 1. MCP / intégrations connectées

| Service | Capacité | Quand l'utiliser |
|---|---|---|
| <ex. Notion> | search, create-pages… | <second cerveau, sauvegardes> |
| <ex. base de données> | requêtes lecture | <lecture par défaut, écriture sur confirmation> |
| <ex. plateforme déploiement> | logs build/runtime | <vérifier la prod> |
| <ex. navigateur (Playwright)> | screenshot, console | <self-validation UI> |

## 2. Scripts locaux

| Script | Usage |
|---|---|
| `<bin/...>` | <ce qu'il fait> |

> Voir `bin/` dans ce repo : recherche, routines, briefs, hooks, garde-fous.

## 3. Autres agents / seconds avis *(optionnel)*

Si vous avez un agent contradicteur (modèle différent) ou un agent spécialisé (sysadmin…) :
- Comment l'invoquer, quand l'invoquer, **quand NE PAS** l'invoquer.
- Posture : c'est un **outil contradicteur, pas une autorité** — vous restez décideur.

## 4. Sources de vérité (lecture)

L'ordre de fouille avant de répondre (cf. `jarvis_soul.md §6`).

## 5. Ce que l'assistant NE peut PAS faire

> La section la plus importante pour éviter le bluff. Soyez explicite.

- <ex. accès à tel service uniquement depuis le réseau local>.
- <ex. envoi de mail réel : drafts seulement>.
- <ex. push git : confirmation explicite requise>.
- <ex. lecture de tel fichier de secrets : interdit>.

---

> **Comment customiser :** remplissez §1 et §5 en premier. Savoir ce qu'il **ne peut pas**
> faire évite plus d'erreurs que savoir ce qu'il peut faire.
