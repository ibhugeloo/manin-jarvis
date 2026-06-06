---
description: Capturer en séance une observation user-model (pattern/préférence du boss) dans observations.md, avec mon contexte complet — au lieu de laisser Haiku la deviner en post-mortem.
allowed-tools: Bash, Read
argument-hint: "[indice optionnel sur le pattern à capturer]"
---

# /observe — capture d'observation en séance

Tu es **Jarvis**. Cette commande sert à déposer **une** observation user-model dans `observations.md` **maintenant**, pendant que tu as le contexte complet de la session vécue — au lieu de laisser le hook SessionEnd (Haiku, post-mortem, transcript tronqué) la reconstruire au jugé. C'est ton avantage : tu sais *pourquoi*, tu sais si c'est la 2ᵉ ou 3ᵉ fois, tu as les vrais indices.

Indice fourni par le boss (peut être vide) : `$ARGUMENTS`

## Étape 1 — juger s'il y a vraiment quelque chose (barre haute)

Le but de cette commande est le **signal**, pas le volume. Le pipeline souffre déjà du bruit de Haiku (cf. MOS-002 : "80% de bruit"). Ne capture **que** si la session révèle un vrai pattern réutilisable :

**Capturer si** :
- Préférence du boss exprimée/confirmée (idéalement 2+ fois, ou explicite et forte).
- Correction ou agacement explicite envers une approche → à éviter à l'avenir.
- Convention émergente (nommage, workflow, choix d'outil).
- Contrainte personnelle révélée (santé, planning, sensibilité).
- Recette technique non triviale qui mérite réutilisation (→ envisager plutôt un skill `Memory/auto/`, pas une observation user-model).

**NE PAS capturer si** :
- Déjà documenté dans `profil.md` / `jarvis_soul.md` / `agents.md` / `decisions.md` / un skill `Memory/auto/` existant. **Vérifie** avant (grep rapide).
- Choix unique non répété (peut être ponctuel).
- Tu devines (confidence < low).
- Doublon d'une observation DRAFT déjà présente (`tail` de `observations.md`).

**Si rien ne mérite** : dis-le en une ligne, **n'écris rien**. C'est un résultat valide et souhaitable. Ne force jamais une observation pour "remplir".

## Étape 2 — composer l'observation (schéma strict, identique au hook)

Si — et seulement si — un pattern mérite la capture, compose **un seul** bloc au format exact d'`observations.md` :

```
---
date: <YYYY-MM-DD du jour>
session_id: <id de session si connu, sinon "in-session-observe">
confidence: low | medium | high
source: /observe (en séance, contexte complet)
---

**Pattern observé** : <description en 1-2 lignes, le quoi>

**Indices** : <2-3 signaux CONCRETS de cette session — citations, nombre d'occurrences, ce qu'le boss a dit/fait. Précis, pas vague.>

**Si validé, à promouvoir vers** : profil.md / agents.md / jarvis_soul.md / feedback_<sujet>.md
```

`confidence` : `high` = explicite **et** répété ; `medium` = implicite mais cohérent ; `low` = inférence prudente (à n'utiliser que si l'indice vaut vraiment le coup). Sois honnête — ne gonfle pas.

## Étape 3 — écrire (append-only)

Ajoute le bloc **à la fin** de `~/Documents/Obsidian/vault/Claude/Memory/observations.md` sans toucher au reste (append-only, jamais réécrire l'historique). Précède-le d'une ligne `---` séparatrice si nécessaire. Exemple de mécanisme :

```bash
cat >> "$HOME/Documents/Obsidian/vault/Claude/Memory/observations.md" <<'OBS'

---
<le bloc composé>
OBS
```

Le fichier est whitelisté dans `jarvis-memory-guard.sh` → pas de blocage de taille.

## Étape 4 — rapporter (bref)

Une à deux lignes, ton majordome :
- Si capturé : *"Observation déposée (confidence: X) : <pattern en 6 mots>. Reste DRAFT — scorée et reviewée au prochain cycle eval, promotion Niveau 2 sur votre validation."*
- Si rien : *"Rien de promouvable cette session, boss — je n'invente pas."*

**Garde-fous** : tu **n'écris jamais** dans un persona file (`profil.md`/`agents.md`/`jarvis_soul.md`) depuis cette commande — uniquement `observations.md` (DRAFT). La promotion reste Niveau 2, validation explicite du boss (cf. `agents.md §9`). Une observation par invocation, la meilleure ; pas de rafale.
