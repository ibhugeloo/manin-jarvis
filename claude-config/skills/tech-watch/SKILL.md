---
name: tech-watch
description: Veille quotidienne sur l'écosystème agentic et Claude Code (releases, breaking changes, patterns adoptables) confrontée à l'état actuel de Jarvis. Use when l'utilisateur demande "veille tech", "jarvis tech-watch", "quoi de neuf sur Claude Code / agentic", "y a-t-il des breaking changes", "nouveautés écosystème agent".
---

# Skill — Tech-watch (veille agentic, interactif)

État de l'art quotidien en 1 page sur les sujets clés pour Jarvis. Version **interactive** (WebSearch live). Persona : concis, factuel, pas de "il semblerait". Info introuvable → le dire, pas de meublage.

Sortie : `~/Documents/Obsidian/vault/Brief/<YYYY-MM-DD>-tech-watch.md` via `Write` (si existe → append).

## Sources
1. **WebSearch** — 3-5 recherches ciblées (mois courant), filtrer < 30j : Hermes Agent (Nous Research), OpenClaude, Claude Code (Anthropic — patches/hooks/deprecations), agentic memory patterns, self-improving LLM agents.
2. **Confrontation à l'état Jarvis** — lire `decisions.md` + `tools.md` (+ `heartbeat.md` WARM). Pour chaque pattern : **déjà chez Jarvis** (ne pas re-débattre) / **adoptable** (comment, 1-3 lignes) / **pas pertinent** (ignorer).
3. **Breaking changes (priorité 🔴)** — un patch Claude Code/Hermes qui casse un pattern Jarvis (hooks, MCP, `bin/`, rules) → étiquette 🔴 + impact concret + mitigation.

## Format
`# Veille tech — <date>` puis : `## TL;DR` (3 lignes) · `## 🔴 Breaking changes` (ou `_RAS_`) · `## 🟡 Patterns adoptables` (max 3 : source, description, comparaison Jarvis, comment) · `## 🟢 Releases & news` · `## Question au boss` (1 si décision à prendre, sinon `_RAS_`) · `## Sources` (liens).

## Restitution
En séance : annoncer le TL;DR + tout 🔴. Proposer le push Telegram **seulement si 🔴**, sans l'envoyer sans confirmation (SOUL §2). 3-5 WebSearch max — au-delà = bruit.
