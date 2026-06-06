---
description: Brief matinal en séance (Calendar + Gmail + repos + todos + activité Agency + Inbox Jarvis) — invoque le skill brief
---

# /jarvis-jour — brief matinal (interactif)

Génère le brief du jour **dans la session courante** (MCP Gmail/Calendar/Notion live, plus fiable que le cron headless).

Marche à suivre :
1. Invoquer le **skill `brief`** (savoir-faire complet : Calendar, Gmail inbox, repos via `jarvis-status --json`, todos vault, activité command center Agency via API, Inbox Jarvis Notion).
2. Écrire `Brief/<date>.md` (ou `<date>-interactif.md` si le cron a déjà écrit — ne pas écraser).
3. Restituer l'essentiel + la suggestion du jour en séance.

> Complémentaire au dispatcher `jarvis jour` (mode headless). Même savoir-faire, surface interactive.
