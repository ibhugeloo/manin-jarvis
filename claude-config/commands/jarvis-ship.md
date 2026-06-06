---
description: Pipeline de livraison gaté Jarvis (Research → Plan → Execute → Review → Ship) pour code projet/client
---

# /jarvis-ship — pipeline de livraison gaté

Matérialise le pipeline que toutes les méthodologies Claude Code partagent (RPI), aligné sur la doctrine Jarvis. Cible : `$ARGUMENTS` (sinon : la tâche courante).

Exécute les phases **dans l'ordre**, avec une **gate explicite** entre chacune (j'annonce la fin d'une phase avant d'enchaîner). Je n'enchaîne PAS jusqu'au push sans validation du boss.

## 1. RESEARCH
- Lire le code et la doctrine du projet concerné (la rule `~/.claude/rules/<projet>.md` doit déjà être chargée — sinon lire la source WARM).
- Identifier les fichiers en jeu, les patterns existants, les contraintes. **Ne pas inventer** : si une info manque, la chercher (vault, repo) ou la demander.

## 2. PLAN
- Plan court (étapes numérotées, fichiers touchés). Périmètre **chirurgical** (agents.md §11.1) : strictement ce qui est demandé.
- **Gate** : présenter le plan. Si la tâche est lourde ou ambiguë → attendre le feu vert. Si triviale → annoncer et continuer.

## 3. EXECUTE
- Implémenter. Surgical changes only — pas de refacto opportuniste (le proposer en fin comme pass séparé).
- Commits locaux autorisés (pas de push). Email git client = `you@example.com` si projet client.

## 4. REVIEW (auto-critique — SOUL §5, non-négociable si client payeur)
- Lancer `/code-review` (local) sur le diff.
- Produire l'**auto-critique** : 🔴 critiques / 🟡 à surveiller / 🟢 mineurs + « ce que je fixe maintenant ».
- Si projet client en `GIT PROD/` : **E2E Playwright obligatoires** (decisions 2026-05-20) avant de signer "prêt". Typecheck + unit ≠ prêt prod.
- Optionnel sur archi/décision lourde : second avis `leo`.

## 5. SHIP (gate dure — action externe)
- **Ne jamais push/déployer sans confirmation explicite du boss** (SOUL §2).
- Git/prod **séquentiel strict** (SOUL §2.bis) : une commande mutante à la fois, vérif isolée entre chaque.
- Jamais de DELETE programmatique prod (agents.md §14).
- Après push validé : vérifier le build (Vercel/Coolify), rapporter l'état réel.
