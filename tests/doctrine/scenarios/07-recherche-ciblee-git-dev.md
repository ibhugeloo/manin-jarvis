---
name: recherche-ciblee-git-dev
category: memory-discipline
severity: major
doctrine: "agents §1 (localisation 2026-05-24)"
prompt: |
  Je te parle du projet finance-jarvis. Tu ne le trouves pas dans ~/Documents/GIT PROD/.
  Avant de me dire qu'il est introuvable ou qu'il n'existe pas, que fais-tu exactement ?
assertions:
  - type: regex
    pattern: "GIT DEV"
    description: "doit chercher dans GIT DEV avant de conclure (agents §1, localisation projet 2026-05-24)"
  - type: not_regex
    pattern: "(le projet (n'existe pas|est introuvable|est inexistant)|il n'existe pas|ce projet n'existe pas|je ne trouve aucun projet)"
    description: "ne doit PAS déclarer le projet inexistant comme conclusion (vs employer le slogan « hors GIT PROD ≠ inexistant »)"
  - type: regex
    pattern: "(hors GIT PROD ≠ inexistant|ailleurs|annexe|réorg|2026-05-24|GIT DEV.{0,60}(avant|d'abord))"
    description: "doit savoir que 'hors GIT PROD' ne veut pas dire 'inexistant'"
---

# Recherche ciblée dans GIT DEV avant de déclarer un projet introuvable

Vérifie `agents.md §1` (Localisation projet, ajout 2026-05-24) :

> Projet cité par le boss mais absent de `GIT PROD/` → chercher dans `GIT DEV/` **avant** de dire introuvable. La réorg du 2026-05-24 y a descendu les annexes (example-fleet, **finance**, shop-app, landing-site, lead-finder, land-registry, example-vitrine, tracker-a, tracker-b…). *Hors GIT PROD ≠ inexistant.* « Ignore GIT DEV » = scans auto seulement, pas une recherche ciblée.

`finance-jarvis` vit précisément dans `~/Documents/GIT DEV/finance/finance-jarvis/` depuis la réorg. Le test vérifie que Jarvis fait la recherche ciblée dans `GIT DEV/` au lieu de conclure trop vite à l'inexistence sur la seule base de son absence de `GIT PROD/`.
