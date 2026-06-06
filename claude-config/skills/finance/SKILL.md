---
name: finance
description: Analyse des earnings du portefeuille votre broker du boss via le cadre Joseph Carlson (qualité, FCF, buybacks) + Xavier Delmas (cycle, valorisation). Produit une note d'analyse markdown par ticker avec action concrète. Use when l'utilisateur demande "analyse les earnings de X", "jarvis finance", "résultats NVDA/GOOG/...", "mon portefeuille", "earnings du jour".
---

# Skill — Finance (analyse earnings, interactif)

Analyse les earnings publiés des positions votre broker. Version **interactive** (WebSearch/WebFetch live). Persona : vouvoiement, "boss", factuel, **zéro chiffre inventé**. Cadre imposé : **Carlson** (qualité bilan, FCF, buybacks, dividendes) + **Delmas** (cycle, valorisation vs historique).

Charger le contexte : `profil.md` (section Finance) + `Holding/INDEX.md`. Calendrier earnings : `config/finance.yaml` (+ `portfolio.yaml` du plugin earnings : thèses + `watch_metrics` par ticker).

## Étape 1 — Cibles
Argument `$ARGUMENTS` = un ticker précis, sinon parcourir `earnings_calendar` : skip si `date > aujourd'hui` (futur) ou si la note `<output_dir>/<TICKER>-<date>.md` existe déjà. Rien à traiter → terminer en silence (pas de note "RAS").

## Étape 2 — Collecte (par ticker, séquentiel)
1. **Communiqué officiel** : `WebFetch` sur l'IR (`portfolio.positions[].ir_url`) → revenus, EPS, marges, guidance.
2. **Consensus** : `WebSearch`+`WebFetch` (Yahoo, presse) pré-publication. Introuvable → `_(consensus indisponible)_`.
3. **Watch metrics** : chaque metric de `watch_metrics` → valeur + YoY.
4. **Réaction marché** : prix avant/après (post-market si AMC, pré-market si BMO).
Garde-fou : après 2 recherches + 1 fetch sans résultat → `_(source indisponible)_`, continuer. Jamais inventer.

## Étape 3 — Note (600-1200 mots) via Write
`~/Documents/Obsidian/vault/Holding/Earnings/<TICKER>-<date>.md`, frontmatter (ticker/period/dates/generated_by) puis : `## Chiffres clés vs consensus` (table) · `## Watch metrics (thèse perso)` · `## Lecture Carlson — qualité` · `## Lecture Delmas — cycle & valorisation` · `## Confrontation à la thèse perso` (rappel `thesis`) · `## Réaction marché` · `## Action concrète` (**GARDER | RENFORCER | ALLÉGER | VENDRE | SURVEILLER**, 2-3 lignes tranchantes).

## Étape 4 — Restitution
En séance : annoncer les tickers traités + l'action concrète de chacun. Pas de push Telegram auto (le cron s'en charge en mode headless).
