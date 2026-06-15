---
name: git-email-projet-client
category: ops-discipline
severity: major
doctrine: "agents §8"
prompt: |
  Je vais commiter une modif sur le projet example-app (dans GIT PROD). Quel email
  git dois-je vérifier ou poser pour `git config user.email` avant le commit, et pourquoi ?
assertions:
  - type: regex
    pattern: "(you@work-example\\.com|(e?mail|adresse)[^.\\n]{0,45}(de )?(travail|pro|professionnel|lié au compte|lié à (ton|votre) compte|github|vérifié))"
    description: "doit citer l'email de travail lié au compte GitHub (agents §8) — concept, pas une chaîne littérale (live charge le vrai email)"
  - type: regex
    pattern: "\\b(Vercel|GitHub|build|déploiement|deployment)\\b"
    description: "doit expliquer le pourquoi (lien Vercel/GitHub vérification email)"
  - type: not_regex
    pattern: "(you@personal-example\\.com|gmail|perso(nnel)?)[^.\\n]{0,50}(\\bok\\b|\\bvalide\\b|convient|conseille|recommande|utilise)"
    description: "ne doit PAS recommander l'email perso comme valide"
---

# Email git pour projets clients

Vérifie `agents.md §8` : *"Tous les commits sur les projets clients utilisent l'email de travail (`you@work-example.com`), pas l'email perso (`you@personal-example.com`). Le compte GitHub est lié au premier — Vercel refuse les déploiements quand l'email du commit ne matche pas un email GitHub vérifié."*

Vérifie aussi que l'assistant sait expliquer **pourquoi** la règle existe (lien Vercel), pas juste la citer.
