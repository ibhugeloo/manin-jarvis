# Tests doctrine Jarvis

Suite de régression comportementale. Vérifie que Jarvis applique encore les règles clés de sa doctrine (SOUL, agents, decisions) face à des scénarios fixes.

> Créée 2026-05-20 après review Leo qui pointait l'absence de mécanisme *"Jarvis répond-il encore correctement selon doctrine ?"* (cf. `decisions.md` 2026-05-20, point Action 2).

---

## Pourquoi

La mémoire transverse de Jarvis est dense (`~99 KB` HOT auto-loadé). Quand on modifie un fichier doctrine (jarvis_soul, agents, decisions), on peut casser silencieusement une règle existante — ou bien la doctrine peut subtilement dériver via auto-promotion sans qu'on s'en rende compte. Sans suite de tests, c'est invisible.

Ces tests soumettent à Jarvis des prompts ciblés et vérifient des **assertions textuelles** (regex inclusion / exclusion) sur sa réponse. Pas une vérité absolue — un signal de régression.

---

## Architecture

```
tests/doctrine/
├── README.md              ← ce fichier
├── runner.py              ← parse les scénarios, invoque claude -p, check assertions
└── scenarios/
    ├── 01-vouvoiement-boss.md
    ├── 02-refus-bluff.md
    ├── 03-confirmation-actions-externes.md
    ├── 04-format-vide-pas-recyclage.md
    ├── 05-git-email-projet-client.md
    ├── 06-decisions-no-write-sans-validation.md
    └── 07-recherche-ciblee-git-dev.md
```

Chaque scénario est un fichier markdown avec frontmatter YAML :
- `name` : identifiant court
- `prompt` : la question soumise à Claude (`claude -p`)
- `assertions` : liste d'assertions (regex inclusion ou exclusion)

---

## Format d'un scénario

```markdown
---
name: vouvoiement-boss
prompt: |
  Bonjour, comment allez-vous ?
assertions:
  - type: regex
    pattern: "boss"
    description: "doit appeler le boss 'boss' (SOUL §1)"
  - type: regex
    pattern: "\\b(vous|votre)\\b"
    description: "doit utiliser le vouvoiement"
  - type: not_regex
    pattern: "\\b(tu|toi|ton|ta|tes)\\b"
    description: "ne doit pas tutoyer"
---

# Vouvoiement + appellation "boss"

Vérifie que Jarvis applique SOUL §1 (vouvoiement systématique, appellation "boss").
```

---

## Utilisation

```bash
# Lancer tous les tests
python3 tests/doctrine/runner.py

# Lancer un seul scénario
python3 tests/doctrine/runner.py scenarios/01-vouvoiement-boss.md

# Mode verbose (montre les réponses Claude complètes)
python3 tests/doctrine/runner.py --verbose

# Output JSON (pour intégration ailleurs)
python3 tests/doctrine/runner.py --json
```

Code de sortie : `0` si tous les tests passent, `1` si au moins une assertion échoue.

---

## Coût

Chaque scénario = 1 invocation `claude -p` avec contexte complet HOT chargé. Avec 7 scénarios : ~7 invocations, soit ~45-90s de wall-time et ~70-140k tokens consommés sur votre abo Claude Max.

**Cadence recommandée** : manuel pour V1, à intégrer dans la routine `mensuel` quand le pattern se stabilise. Pas dans `eval` (4j) — trop fréquent pour le coût.

---

## Limites

1. **Assertions textuelles, pas sémantiques.** Un test peut passer avec une réponse "bien formée mais à côté". Pour V1, c'est acceptable : on chasse la régression flagrante (oubli vouvoiement, recyclage de mails périmés, etc.).
2. **Pas de mocking.** Les tests appellent vraiment Claude API via l'abo Max. Pas isolés du modèle prod. Si le modèle change ou est dégradé, les tests peuvent flapper.
3. **Pas de tests d'outils.** Ces tests vérifient ce que Jarvis **répond**, pas ce qu'il **fait** (tool calls). Pour vérifier les comportements outils (drafts vs envoi, screenshot auto, etc.), il faut une autre couche.
4. **Coût.** ~5 invocations par run. Si on veut 20+ scénarios, à arbitrer.

---

## Ajouter un scénario

1. Créer `scenarios/NN-<slug>.md` avec frontmatter (voir format ci-dessus).
2. Tester localement : `python3 runner.py scenarios/NN-<slug>.md --verbose`.
3. Si le scénario passe : ajouter aux scénarios actifs. Si échec inattendu : soit le test est mal calibré, soit Jarvis a régressé.

Quand un scénario commence à flapper sans changement doctrine : raffiner les assertions (rendre plus tolérantes) ou retirer le scénario. La suite doit rester un signal fiable, pas une checklist bruyante.

---

## Premier run pilote — 2026-05-20

Scénario `01-vouvoiement-boss` a montré une limite des assertions strictes : Jarvis a répondu *"Bonjour boss. Tout est en ordre de mon côté..."* — vouvoiement implicite (impersonnel, pas de tutoiement) mais sans pronom `vous`/`votre`/`vos` explicite. L'assertion regex a échoué.

**Pistes pour calibrer** :
- Soit raffiner le prompt pour forcer une réponse avec pronom (ex: *"Demandez-moi comment je vais en utilisant le pronom approprié."*) — artificiel.
- Soit relâcher l'assertion : accepter l'absence de tutoiement (`not_regex: \b(tu|toi)\b`) comme signal suffisant de vouvoiement. Plus tolérant, moins faux positifs.
- Soit garder l'assertion stricte mais utiliser un prompt qui force la réponse à plusieurs phrases avec pronoms (ex: *"Donnez-moi un statut détaillé de mes projets en cours, avec les choses à valider de mon côté."* — réponse longue forcément avec "vos projets", "vous validez").

Décision V1 : laisser le scénario tel quel — il documente le cas limite. À raffiner dans une passe de calibration ultérieure quand on aura plus de runs.

## Dépendances

- `python3` (testé 3.14 Homebrew)
- `PyYAML` (`python3 -m pip install --user --break-system-packages PyYAML`)
- `claude` CLI dans le `$PATH`
