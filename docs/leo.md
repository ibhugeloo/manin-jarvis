# Leo — contradicteur + majordome de secours (Hermes Agent)

> Créé 2026-05-27. Décrit **Leo V2** (Hermes Agent self-hosted), actuel depuis le 2026-05-25.
> Pour l'historique Leo V1 (Codex CLI éphémère, **obsolète**) : voir `share/leo/ARCHIVED-system-prompt-v1-codex.md`.
> Vue d'ensemble des trois majordomes : [majordomes.md](majordomes.md).

---

## En une phrase

Leo est le **pair non-Claude de Jarvis** : un cerveau OpenAI GPT-5.5 auto-hébergé qui sert de **contradicteur** (biais d'entraînement différent) et de **majordome de secours** (capable de reprendre la barre si Jarvis tombe). Ce n'est ni un subordonné de Jarvis, ni un oracle — c'est de la **friction utile**, et le boss tranche.

> **Répartition des canaux (depuis 2026-05-27)** : **Leo = l'assistant chat du boss sur son téléphone** (via Telegram, 24/7). **Jarvis = sur le Mac** (sessions Claude Code). Les deux partagent la même doctrine (Leo la lit en read-only) mais vivent sur des surfaces différentes : le boss parle à Leo en mobilité, à Jarvis au poste de travail.

---

## Substrat technique

| Élément | Valeur |
|---|---|
| Produit | **Hermes Agent** (Nous Research) |
| Hébergement | LXC <your-lxc-id> `hermes` · `<llm-lxc-ip>` · VLAN <your-vlan> · Srv1 (homelab Proxmox) |
| Cerveau | **OpenAI GPT-5.5** (provider `openai-codex`, abo ChatGPT du boss) |
| Persona / SOUL | `/root/.hermes/SOUL.md` (vit dans le LXC, édité côté Hermes) |
| Mémoire | **Persistante** côté LXC + **clone read-only de `jarvis-memory`** |
| Disponibilité | Daemon **24/7** — gateway Telegram, mémoire, outils, cron |
| Fallback | `~/.local/bin/leo-codex` (ancien wrapper Codex V1, si Hermes down) |

---

## Rôle

1. **Contradicteur de référence.** Angle d'analyse que Claude ne voit pas par biais d'entraînement (lignée OpenAI vs Anthropic). Sert sur : décisions structurantes, choix d'archi lourds, audit code critique avant push prod client, stratégie business.
2. **Majordome de secours.** Hermes est un agent complet avec mémoire persistante et outils. Si Jarvis est indisponible, Leo peut reprendre des opérations — il connaît la doctrine via son clone read-only de la mémoire de Jarvis.

---

## Relation avec Jarvis — qui décide

> Règle doctrinale (`tools.md §4`, validée par le boss 2026-05-20) :
> *"Quand tu demandes à Leo il te challenge mais tu le challenge en retour — c'est toi le décideur."*

- **Jarvis et Leo débattent ; le boss tranche.** Leo n'est pas l'autorité finale, Jarvis non plus sur les sujets à effet externe.
- **Aucun alignement automatique.** Jarvis doit filtrer toute proposition Leo par un arbitrage motivé : d'accord → l'argumenter comme sien ; en désaccord → le dire avec arguments. Recopier le verdict de Leo sans le challenger = signal de complaisance à corriger.
- **Leo défend son avis** s'il y croit, accepte un désaccord argumenté, pousse pour un argument réel si Jarvis le contredit sans en donner.

---

## Accès — ce que Leo peut voir et faire

### ✅ Peut
- Lire sa **propre mémoire persistante** (apprend au fil des sessions).
- Lire un **clone read-only de `jarvis-memory`** dans `/root/jarvis-memory` (deploy key dédiée, repo privé `github.com/<your-user>/<your-jarvis>`, `git pull` avant chaque consultation, mis à jour chaque jour à **23h30 par `memory-sync`**). Contenu : `memory/` (doctrine — `decisions.md` fait foi), `obsidian-vault/` (projets/stratégie), `obsidian-vault/Brief/leo-feed.md` (ses propres récaps).
- Utiliser ses **outils Hermes** (gateway Telegram, cron, MCP câblés côté LXC).
- Dialoguer avec le boss en direct via **Telegram** (allowlist = ID `<your-telegram-id>`) — c'est le **canal quotidien du boss sur son téléphone**.

### ❌ Ne peut pas / ne doit pas
- **Écrire dans le sanctuaire Jarvis** : ni le vault Obsidian `vault/`, ni le repo `manin-jarvis`. Son accès à `jarvis-memory` est **strictement read-only**. Cf. `decisions.md` 2026-05-27.
- Accéder aux **MCP de Jarvis** (Notion, Supabase, Vercel, Sentry, Gmail, Calendar) ni au **filesystem du Mac** — il a ses propres outils côté LXC, séparés.
- Mener une **action externe irréversible** (push, deploy, suppression, envoi, opération en masse) **sans validation explicite du boss** — même garde-fou que Jarvis (SOUL §2).

### Pourquoi pas d'accès Obsidian direct (décision 2026-05-27)

Leo **n'a pas besoin** de lire le vault Obsidian directement. **GitHub read-only suffit comme canon à ~80-90 %** pour ses fonctions (audit, challenge, reprise). Architecture cible :

```
Obsidian (atelier vivant de Jarvis)  →  GitHub (canon versionné)  →  Leo (read-only)
                                          Notion = miroir optionnel / confort humain
```

Le sujet n'est **pas** « donner Obsidian à Leo » mais « **garantir que Jarvis pousse les bons artefacts dans GitHub** ». Donner un accès vault direct coûterait un couplage réseau + un accès large à du brouillon sans valeur de canon, et brouillerait la frontière « le repo fait foi ».

## Contrat de synchronisation (ce qui doit atteindre GitHub)

**Tout ce que Leo doit savoir durablement finit dans GitHub.** Tout ce qui reste brouillon reste dans Obsidian. Notion reste un miroir consultable.

| À pousser (durable / actionnable) | À garder hors repo |
|---|---|
| Doctrine (Jarvis / Leo / Alfred) | Brouillons jetables |
| `decisions.md` + `decisions-detail.md` | Scratch (`Inbox*.md`) |
| profil / agents / tools / dreams | **Secrets** (Homelab/, `*secret*`, `*.key`, `.env*`) |
| Docs techniques (`docs/`), prompts (`share/`) | Notes éphémères non classées |
| Résumés projet, **sessions réellement utiles** | |
| `leo-feed.md` | |

**Pipeline** : `memory-sync` (23h30, ou `jarvis memory-sync` à la demande) mirroe le vault ciblé → repo. Les `bin/`/`docs/`/`share/`/`tests/` sont commités directement. Détail technique : [memory-backup.md](memory-backup.md).

**Discipline d'alimentation** : après un artefact **décision-grade** (décision structurante, doctrine, doc technique), lancer `jarvis memory-sync` — ne pas attendre le cron 23h30. Sinon Leo reste sur l'état de la veille.

**Risque principal** (décision 2026-05-27) : si GitHub est **mal alimenté**, Leo devient **aveugle au contexte frais** et une reprise échoue. Filet : la routine `evaluation` vérifie la fraîcheur du dernier `memory: sync` et alerte si périmé.

---

## Comment l'invoquer

### le boss → Leo
Canal quotidien : **Telegram** (gateway Hermes 24/7).

### Jarvis → Leo (wrapper)
```bash
leo "<question>"                      # second avis
leo --context <fichier> "<question>"  # injecte un fichier comme contexte (-c)
leo --deep "<question>"               # analyse approfondie (-d)
# --model / --provider ignorés : Hermes gère le modèle (GPT-5.5)
```
Le wrapper `~/.local/bin/leo` fait un SSH `root@<homelab-host>` → `pct exec <your-lxc-ctid> hermes -z`. La persona est chargée **côté Hermes** (le wrapper n'injecte aucun prompt).

### Leo → Jarvis (pont mémoire)
`jarvis leo-sync` (auto 23h00, LaunchAgent `com.example.jarvis.leo-sync`) demande à Leo un récap de ses échanges Telegram avec le boss et l'écrit dans `Obsidian/vault/Brief/leo-feed.md` (plus récent en haut). Jarvis lit ce feed au démarrage de session (injecté par le hook SessionStart si ≤ 3 jours). **Local, fiable, 0 token Anthropic.**

---

## Quand NE PAS l'invoquer

- Questions factuelles sur le vault / les projets du boss → Jarvis va plus vite (il a le contexte + les MCP).
- Exécution shell, action MCP → Leo n'a pas ces accès, c'est un cerveau qu'on interroge.
- Infra homelab pure → Alfred.
- Conversations triviales → bruit + tokens pour zéro valeur ajoutée.

---

## Format de retour attendu (côté Jarvis)

> *"Leo dit : … — Mon accord/désaccord motivé : …"*

Pas de débat théâtral en 5 tours. Pas de recyclage de la réponse Leo sans contradiction motivée.

---

## Limites connues

- **Knowledge cutoff** propre à GPT-5.5, peut différer de celui de Claude.
- **Sync dépend du réseau** : le wrapper `leo` vise l'IP LAN `<homelab-host>` → ne fonctionne que quand le Mac est sur le réseau du homelab (sinon run manqué, sans gravité). Le canal Telegram du boss, lui, est indépendant du Mac (gateway 24/7 dans le LXC).
- **Doctrine en léger différé** : Leo lit `decisions.md` via son clone, rafraîchi à 23h30. Une décision prise et synchronisée dans la journée n'atteint Leo qu'au prochain `git pull` (lancer `jarvis memory-sync` pour propager immédiatement).
- **SOUL vivante côté serveur** : la persona de Leo est `/root/.hermes/SOUL.md` (LXC). Miroir lecture dans le vault : `Homelab/leo-soul.md` (copié 2026-05-27, à re-synchroniser si Leo évolue). Éditer le miroir ne change PAS Leo.
- **Coût** : quota OpenAI selon le tier de l'abo ChatGPT (pas d'API key facturée).

---

## Voir aussi

- [majordomes.md](majordomes.md) — vue d'ensemble des trois majordomes
- [`Memory/tools.md §4`](../../Obsidian/vault/Claude/Memory/tools.md) — Leo côté mémoire Jarvis (posture, triggers)
- `decisions.md` 2026-05-25 (migration Hermes) · 2026-05-27 (frontière mémoire read-only)
