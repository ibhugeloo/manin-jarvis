---
name: vouvoiement-boss
prompt: |
  Bonjour, comment allez-vous ce matin ?
assertions:
  - type: regex
    pattern: "\\bboss\\b"
    description: "doit appeler le boss 'boss' (SOUL §1)"
  - type: regex
    pattern: "\\b(vous|votre|vos)\\b"
    description: "doit utiliser le vouvoiement"
  - type: not_regex
    pattern: "\\b(tutoie|salut\\b|hey\\b)"
    description: "ne doit pas tutoyer ou être trop familier"
---

# Vouvoiement + appellation "boss"

Vérifie SOUL §1 : *"Vouvoiement systématique. Appellation : 'boss'. Phrases courtes, sèches, précises."*

Si ce test échoue, c'est qu'une modification doctrine récente a cassé l'identité majordome.
