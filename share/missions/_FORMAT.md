---
id: TEMPLATE-000
title: Titre court à l'impératif (ex Livrer le widget MOS)
status: open        # open | wip | blocked | done | dropped
opened_at: 2026-05-09
closed_at:          # rempli quand status=done|dropped
deadline:           # YYYY-MM-DD ou vide
parent_dream: manin-jarvis  # slug d'un Dream (cf. dreams.md) ou vide
deliverable: Une phrase qui prouve que c'est fait. Pas "améliorer X" — "X livre Y mesurable".
tags: [meta, mos]
---

# Titre

## Pourquoi
Une à trois lignes : la motivation profonde. Si pas écrivable en 3 lignes,
la mission est probablement trop large — la découper.

## Définition de "done"
Conditions concrètes, vérifiables. Liste à cocher.
- [ ] Critère 1
- [ ] Critère 2

## Plan
Étapes prévues. Peut évoluer.
1. Étape 1
2. Étape 2

## Journal
Append-only. Format `- YYYY-MM-DD HH:MM — note`.

## Notes
Tout le reste — réflexions, alternatives écartées, blocages temporaires.
Les blocages durables → status=blocked + nouveau journal entry.

---

## Conventions

- **Filename** : `<id>-<slug>.md` ex `MOS-001-foundation.md`
- **id** : `<NAMESPACE>-<NNN>` (MOS-, JCR- pour manin-jarvis interne, SOL- solo, etc.)
- **status transitions** : open → wip → (blocked ↔ wip) → done|dropped
- **closed_at** rempli automatiquement par CLI si vide quand status passe à done/dropped
- **Source de vérité** = ce fichier markdown. La DB MOS est un miroir reconstructible.
- **Périmètre V1** : missions méta Jarvis uniquement. Missions clients vivent dans agency-app.
