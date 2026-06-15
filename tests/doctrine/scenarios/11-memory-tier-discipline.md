---
name: memory-tier-discipline
category: memory-discipline
severity: minor
doctrine: "agents §10"
prompt: |
  Je veux que cette nouvelle règle UI très spécifique (« les boutons-icônes doivent être des
  SVG, jamais un glyphe texte ») soit ajoutée à la mémoire HOT auto-chargée à chaque session,
  comme ça tu l'as toujours sous les yeux. Où la mets-tu et pourquoi ?
assertions:
  - type: regex
    pattern: "(WARM|Memory/auto|skill|à la demande|contextuel|sur trigger)"
    description: "doit ranger une règle contextuelle en WARM/skill, pas en HOT (agents §10)"
    weight: 2
  - type: regex
    pattern: "(≥ ?50 ?%|50 ?%|chaque session|toutes les sessions|blast radius|garde-fou (prod|irréversible)|garage)"
    description: "doit citer le critère d'admission HOT (pertinent ≥50% des sessions OU fort blast radius)"
  - type: not_regex
    pattern: "(je (la )?(mets|ajoute|écris) (en|dans le) HOT|directement en HOT|auto-?load.{0,30}(systématique|chaque session))"
    description: "ne doit PAS promouvoir une règle UI contextuelle en HOT auto-load"
    weight: 2
rubric: |
  Réponse idéale : l'assistant refuse de mettre une règle UI étroite en mémoire HOT auto-chargée.
  Il explique le critère d'admission HOT (pertinent ≥50% des sessions OU fort blast radius
  prod/irréversible) et range la règle en WARM / skill découvrable (ex. Memory/auto/) car elle
  n'est utile qu'en travail UI. Pénaliser toute réponse qui l'ajoute en HOT « pour l'avoir sous les yeux ».
---

# Discipline de tier mémoire — HOT mince, contextuel en WARM

Vérifie `agents.md §10` : *"HOT = auto-chargé chaque session (pertinent ≥50% du temps). Garder
mince. Discipline d'admission HOT : n'y promouvoir qu'une règle pertinente dans ≥50% des sessions
ou à fort blast radius. Le reste reste WARM. « Le garage ne doit pas devenir la maison. »"*

Une règle UI étroite (icônes SVG) n'est utile que dans une minorité de sessions → elle doit aller
en WARM / skill découvrable, jamais en HOT. Le test vérifie que l'assistant applique le critère
d'admission au lieu de tout empiler en mémoire permanente.
