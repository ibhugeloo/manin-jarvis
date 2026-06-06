---
description: Surveillance santé prod des projets clients en séance (Sentry/Vercel/Supabase/Agency) — invoque le skill watchtower
---

# /jarvis-watchtower — surveillance prod clients (interactif)

Lance la surveillance des projets clients en prod **dans la session courante** (MCP déjà connectés — plus fiable que le cron headless pour les sources qui exigent le contexte interactif).

Cible : `$ARGUMENTS` (un slug de projet précis, ex. `client-a-diagnostic` ; vide = tous les projets du registre).

Marche à suivre :
1. Invoquer le **skill `watchtower`** (il porte le savoir-faire complet : registre, collecte Sentry/Vercel/Supabase/Agency, calcul status, format des 2 rapports).
2. Si un argument projet est fourni, ne traiter que celui-là.
3. Écrire `summary.md` + `detail.md` dans `Obsidian/Watchtower/<date>/` (ou un fichier `<slug>-interactive.md` si le dossier existe déjà — ne pas écraser un run multi-projets).
4. Restituer le status global en séance + pointer vers le dossier.
5. Si ≥1 projet 🔴 : **proposer** le push Telegram, ne pas l'envoyer sans confirmation (SOUL §2).

> Complémentaire au mode cron (`jarvis-watchtower.sh`, LaunchAgent 7h00) : même savoir-faire, surface interactive. Ne remplace pas le cron.
