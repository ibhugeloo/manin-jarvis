# AGENTS — workflows opérationnels

> **Template.** Copiez en `agents.md`. Décrit **comment** l'assistant travaille au quotidien
> (le *qui* est dans `jarvis_soul.md`, les *choix datés* dans `decisions.md`).
> Chaque règle suit le format **Règle / Why / How to apply** — c'est ce qui la rend applicable.

---

## 1. Périmètre

Quels dossiers l'assistant analyse-t-il par défaut, lesquels il ignore (sandbox, archives) ?
- **Règle** : <ex. n'analyser que `prod/`, ignorer `dev/` et `archives/`>.
- **Why** : <pourquoi ce filtre>.
- **How** : <où c'est câblé ; comment on override ponctuellement>.

## 2. Accès aux projets / clients

Où vit la doc ? Dans le repo avec le code, ou copiée ailleurs ?
- **Règle** : <ex. la doc reste dans le repo ; une note-index pointe dessus, jamais de copie>.
- **Why** : <portabilité, source unique>.
- **How** : <convention de note-index>.
- **Code > doc en cas de conflit** : si une note contredit le code, le **code fait foi**.

## 3. Organisation des notes

Taxonomie + convention de nommage. **Un fait = un seul endroit**, le reste = liens.
- Définissez l'arborescence cible, la langue, la casse des fichiers.
- **Anti-duplication** : avant d'écrire un fait, chercher s'il existe déjà ; sinon canonique + lien.

## 4. Sessions parallèles

Si vous lancez plusieurs sessions, comment l'assistant évite-t-il d'écraser du travail en cours ?
- **Règle** : avant de toucher un fichier non commité, vérifier qu'une autre session n'y travaille pas.

## 5. Scope d'une instruction

*"Écris le message pour X"* → **livrer le texte**, ne pas l'envoyer sans nouvelle instruction.
- **Why** : vous voulez souvent réviser avant l'action externe.

## 6. Sauvegarde / second cerveau *(optionnel)*

Sur quel trigger l'assistant archive-t-il une session (Notion, note locale…) et dans quel format.

## 7. Git — email de commit

- **Règle** : <quel email sur les commits, selon le contexte (perso vs client)>.
- **Why** : un mauvais email de commit peut casser les déploiements (CI qui matche l'email).
- **How** : vérifier `git config user.email` avant de committer.

## 8. Discipline de modification du code

- **Surgical changes** : modifier strictement le périmètre demandé, pas de refacto opportuniste.
- **LLM pour le jugement seulement** : classification/résumé/extraction — pas pour du routing
  déterministe que `grep`/`jq`/un `if` font mieux (latence + coût + non-déterminisme gratuits).
- **Surface conflicts, don't average** : deux patterns contradictoires → choisir le plus récent/testé
  et signaler l'autre, jamais mélanger.

## 9. Apprentissage — promotion d'un fait observé

Comment un pattern récurrent devient une règle durable :
- **Niveau 1** (auto, bas risque) : écriture dans un dossier `auto/` audité et purgé régulièrement.
- **Niveau 2** (doctrine : ce fichier, `profil`, `decisions`, `soul`) : **validation explicite requise**.
  Le silence ne vaut pas consentement.

## 10. Tier mémoire — HOT / WARM / COLD

- **HOT** : auto-chargé chaque session (pertinent ≥ 50% du temps). Garder mince.
- **WARM** : chargé à la demande quand le contexte matche (cwd, mots-clés). Un fichier par projet/domaine.
- **COLD** : lu seulement sur demande explicite (archives, historique).

> Discipline d'admission HOT : n'y promouvoir qu'une règle pertinente dans ≥ 50% des sessions
> **ou** à fort blast radius (garde-fou prod, irréversible). Le reste reste WARM. *« Le garage
> ne doit pas devenir la maison. »*

---

> **Comment customiser :** ne créez pas toutes les règles d'un coup. Ajoutez-en une **quand un
> comportement vous a agacé 3 fois** — c'est le signal qu'elle mérite d'être écrite.
