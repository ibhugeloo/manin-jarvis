# Playbook — Machine à états & invariants sur code prod client

> Procédure technique appliquée par Jarvis sur **tout projet client en production** dès qu'un changement touche une machine à états métier (statut, lock/unlock, workflow).
>
> Référencée depuis `Obsidian/vault/Claude/Memory/agents.md §12`. Lue à la demande, pas auto-loadée.
>
> Mise en place : 2026-05-19 après un incident de cohérence d état sur un dossier client (example-app).

---

## 1. Pourquoi ce playbook existe

Le 2026-05-19, un dossier client a été figé en statut `genere` (transmis à l organisme financeur) alors qu'aucun diagnostic terrain n'avait été saisi. L'enquêtrice était bloquée.

Le bug vivait dans l'orchestration entre les Server Actions (`validerPrediagnostic`) et la route API `/api/generate-pdf`. **40 audits techniques + 203 tests passants** n'ont pas détecté le bug parce que :
- Les tests couvraient les Server Actions individuellement
- Aucun test ne simulait le parcours utilisateur complet `suspicion=oui → valider → générer fiche pré-diag intermédiaire avant visite`
- Aucun audit d'invariants n'avait été mis en place pour détecter les états incohérents en base

Citation le boss : *"c'est pas possible ce genre de bug alors qu'on a fait 40 audit et des tests"*.

Ce playbook empêche cette catégorie de bug de revenir.

## 2. Les 4 garde-fous à exiger par projet

### Garde-fou 1 — Documentation FSM officielle (`docs/state-machine.md`)

Le projet doit contenir un document unique source de vérité qui liste :

1. **Tous les états possibles** d'un objet métier (table)
2. **Toutes les transitions autorisées** (tableau ou diagramme)
3. **Toutes les transitions interdites** flaggées explicitement
4. **Les invariants à respecter** (ex : "statut=X ⇒ champ Y non-NULL")
5. **La procédure de modification** : "si vous touchez à la FSM, vous DEVEZ mettre à jour ce doc + les tests"

Modèle de référence : `~/Documents/GIT PROD/example-app/docs/state-machine.md`.

### Garde-fou 2 — Tests E2E métier (`tests/lib/*/state-*.test.ts` ou équivalent)

**Pas des tests d'unité isolés sur les Server Actions** — des tests qui couvrent les **parcours utilisateur complets** :

- *"Utilisateur crée → fait A → fait B → l'objet doit être dans état X"*
- Exhaustivité : toutes les combinaisons (état initial × action × paramètres) doivent être couvertes
- Si possible, isoler la logique de transition en **fonction pure exportée** + tester cette fonction unitairement (cf. `lib/pdf/status-transition.ts` côté example-app)

### Garde-fou 3 — Script d'audit d'invariants exécutable (`scripts/audit-state-consistency.mjs`)

Un script CLI runnable contre la prod, qui pour chaque invariant documenté :
- Exécute la query qui détecte les violations
- Sort code 0 si OK, code 1 si au moins une violation
- Affiche les samples des dossiers en état incohérent

À lancer :
- Après tout déploiement qui touche à la FSM
- En cron mensuel (pour détecter les régressions silencieuses)
- Sur demande pendant un incident

Modèle : `~/Documents/GIT PROD/example-app/scripts/audit-state-consistency.mjs`.

### Garde-fou 4 — Checkpoint forcé dans `CLAUDE.md` du projet

Section dédiée dans `CLAUDE.md` qui force le développeur (ou Jarvis) à passer par 3-4 étapes avant tout commit qui touche aux transitions :

```markdown
> ### 🚨 Checkpoint OBLIGATOIRE pour toute modif touchant à `<table>.<statut>`, `<table>.<lock>`, ou aux transitions
>
> 1. Lire `docs/state-machine.md` — vérifier que la modif est documentée
> 2. Ajouter / modifier les tests dans `tests/.../state-*.test.ts`
> 3. Lancer le SQL d'audit ou le script `scripts/audit-state-consistency.mjs`
> 4. Auto-critique terrain : énumérer mentalement 4-5 parcours utilisateurs typiques
>
> **Ne jamais signer "prêt prod" sans avoir coché ces 4 points.**
```

## 3. Quand Jarvis applique ce playbook

### Déclencheurs (Jarvis voit dans un diff ou un audit) :

- Champs nommés `statut`, `state`, `phase`, `step`, `stage` dans une table
- Champs `locked_at`, `verrouille_at`, `frozen_at` ou équivalents
- Server Actions de transition métier (`valider*`, `cloturer*`, `finaliser*`, `archiver*`)
- Routes API qui modifient l'état d'un objet métier
- Migrations SQL qui modifient `<statut>` ou `<lock>` ou ajoutent un nouvel état

### Action de Jarvis :

1. Lister les 4 garde-fous présents/absents pour ce projet
2. Si un garde-fou manque, **refuser de signer "prêt prod"** tant qu'il n'est pas en place
3. Proposer la création du garde-fou manquant (avec template depuis example-app comme référence)
4. Auto-critique mentale obligatoire : énumérer 5 parcours utilisateurs, vérifier que chaque parcours produit un état cohérent

## 4. Quand ce playbook NE s'applique PAS

- Sites vitrine sans workflow métier (`portfolio-site`, `landing-site`, `agency-site`)
- CRUD purs sans transitions interdites
- Code Jarvis interne (`manin-jarvis`) — pas de client externe
- Sandbox `~/Documents/GIT DEV/` — expérimentations
- Code en exploration / preuve de concept non destiné à la prod client

## 5. Projets concernés au 2026-05-19

| Projet | FSM ? | Playbook appliqué ? |
|---|---|---|
| `example-app` | Oui (statut dossier 6 états) | ✅ Garde-fous 1-4 en place 2026-05-19 |
| `agency-app` | Oui (statut projet 8 états : audit/brief/build/demo/iterating/delivered/closed) | ⏳ À instrumenter |
| `example-intake` | À vérifier | ⏳ À évaluer |
| `shop-app` | Probable (statut carte + commande) | ⏳ À évaluer |
| `land-registry` | À vérifier | ⏳ À évaluer |

**Action de suivi** : auditer chaque projet de la liste ci-dessus et créer un ticket par projet pour instrumenter les garde-fous manquants. À planifier dans la prochaine routine `evaluation`.

## 6. Modèles à dupliquer

### Référence `example-app` (premier projet instrumenté) :
- `docs/state-machine.md` — FSM documentée, 6 invariants
- `lib/pdf/status-transition.ts` — logique pure testable
- `tests/lib/pdf/status-transition.test.ts` — 12 tests cas métier (dont la régression de cet incident)
- `scripts/audit-state-consistency.mjs` — audit CLI runnable
- `CLAUDE.md §13` — checkpoint forcé en tête de section
