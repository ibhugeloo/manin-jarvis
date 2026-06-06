---
description: Analyse earnings du portefeuille votre broker en séance (Carlson + Delmas, action concrète) — invoque le skill finance
---

# /jarvis-finance — analyse earnings (interactif)

Analyse les earnings du portefeuille **dans la session courante** (WebSearch/WebFetch live).

Cible : `$ARGUMENTS` (un ticker précis, ex. `NVDA` ; vide = parcourir le calendrier earnings non encore traité).

Marche à suivre :
1. Invoquer le **skill `finance`** (cadre Carlson + Delmas, watch metrics, confrontation à la thèse perso, action concrète).
2. Écrire une note par ticker dans `Holding/Earnings/<TICKER>-<date>.md`.
3. Restituer les actions concrètes (GARDER/RENFORCER/ALLÉGER/VENDRE/SURVEILLER) en séance.

> Complémentaire au dispatcher `jarvis finance` (mode headless).
