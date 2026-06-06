# Alfred — intégration Control Room

Alfred est le **majordome homelab** du boss. Modèle Claude Opus 4.7, périmètre strict : Proxmox, VLANs, Coolify homelab, backup 3-2-1. Invocable depuis le shell via `alfred "<question>"`.

> Vue d'ensemble des trois majordomes : [majordomes.md](majordomes.md).

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  bin/alfred  (wrapper bash, source canonique)   │
│                                                 │
│  → lit  Obsidian/vault/Homelab/                 │
│         alfred_project_instructions.md          │
│                                                 │
│  → lance claude -p                              │
│         --model claude-opus-4-7                 │
│         --system-prompt "<contenu prompt>"      │
│         "<question utilisateur>"                │
└─────────────────────────────────────────────────┘
                ↓ symlink
        ~/.local/bin/alfred  (dans le PATH)
```

**Pourquoi `--system-prompt` plutôt que `--append-system-prompt`** :
- `--system-prompt` **remplace** le prompt par défaut de Claude Code → la doctrine Jarvis (auto-imports CLAUDE.md global) n'est **pas chargée**.
- Alfred reste cantonné à son périmètre sysadmin, sans confusion identitaire avec Jarvis.
- `--append-system-prompt` aurait empilé Alfred par-dessus la doctrine Jarvis → Alfred aurait hérité du tutoiement vouvoiement et des règles de Jarvis. Pas voulu.

**Pourquoi `--print` (one-shot)** :
- Pas de session persistante. Chaque appel Alfred est isolé.
- Pas de pollution de l'historique des sessions Claude Code.
- Pratique pour scripting : Alfred peut être appelé par Watchtower, par une routine, par le boss directement.

**Auth** : OAuth via votre abo Claude Max. **Pas de clé API consommée**, donc pas de coût marginal.

---

## Usage

### Basique

```bash
alfred "Quel VMID prendre pour une nouvelle LXC sur VLAN 40 ?"
alfred "Comment configurer un tunnel Cloudflare pour mon app perso ?"
alfred "Pourquoi mon PostgreSQL Prod (<db-host>) refuse les connexions externes ?"
```

### Avec contexte additionnel

```bash
alfred --context plan-migration.md "Que faut-il vérifier avant de bouger PG Prod ?"
alfred -c docker-compose.yml "Audit cette stack Docker pour exposition publique"
```

Le fichier passé en `--context` est concaténé à la question sous le bloc `--- CONTEXTE ---`.

### Override du modèle (avancé)

```bash
alfred --model claude-sonnet-4-6 "<question rapide non-critique>"   # plus économe
```

### Override du system prompt

```bash
ALFRED_PROMPT_FILE=/tmp/alfred-experimental.md alfred "<question>"
# ou
alfred --prompt /tmp/alfred-experimental.md "<question>"
```

Utile pour tester une évolution du prompt sans toucher au vault.

---

## Quand Jarvis invoque Alfred

**Aujourd'hui** : invocation 100% manuelle par le boss. Pas de routine qui appelle Alfred automatiquement.

**Pattern proposé** (à activer si l'usage manuel se stabilise) :
- Avant un changement homelab risqué dans une session Jarvis, je peux invoquer `alfred --context plan.md "<question vérification>"` et inclure sa réponse dans mon récap. C'est une **délégation** interne, transparente pour le boss.
- Watchtower pourrait pré-diagnostiquer un incident homelab via Alfred avant le push Telegram, pour fournir un contexte technique riche.

Aucune de ces deux intégrations n'est codée. Trigger d'activation : le boss demande explicitement, ou j'observe 3+ usages manuels où la délégation aurait été utile.

---

## Limites

1. **Pas d'exécution.** Alfred répond, il n'exécute pas. Le mode `claude -p` autorise les tool calls, mais le system prompt Alfred parle de "présenter l'action" puis "exécuter avec confirmation". En pratique, `claude -p` peut tenter des tool calls (Bash, Read, Write). Si vous voulez bloquer ça strictement, ajoutez `--disallowed-tools "Bash,Write,Edit"` dans le wrapper. **Pas fait V1** — Alfred peut donc lire des fichiers (`Read`) ce qui est utile pour des audits, mais à surveiller.
2. **Pas d'accès au homelab depuis l'agent cloud.** Si vous invoquez `alfred` depuis votre Mac et qu'Alfred tente un `ssh root@<host>`, il utilisera votre session shell locale (qui a accès LAN/Twingate). Donc depuis votre Mac : ça marche. Depuis un agent cloud Anthropic : ça échouera. C'est le comportement attendu.
3. **Pas de mémoire entre appels.** Chaque invocation est isolée. Pas de suivi long-terme, pas d'apprentissage. Si vous voulez qu'Alfred "se souvienne" d'une décision, il faut l'écrire dans son fichier d'instructions.
4. **Coût quota Claude.** Bien que l'abo Claude Max couvre, chaque appel consomme du quota. Opus 4.7 + system prompt de ~5 KB + question = ~10-20k tokens par invocation. À usage normal (~10-30 appels/mois), pas un souci.

---

## Modifier le comportement d'Alfred

**Source de vérité** : `Obsidian/vault/Homelab/alfred_project_instructions.md`.

Le wrapper lit ce fichier à chaque invocation. Donc :
1. Vous éditez le fichier vault.
2. Vous sauvegardez.
3. Prochaine invocation `alfred` → nouvelle version du prompt.

**Pas de cache, pas de redémarrage.** Modèle simple, pratique pour itérer.

Si vous voulez geler une version pour un usage spécifique : copier le fichier ailleurs et le passer via `--prompt`.

---

## Doctor / debug

Pas de commande `alfred doctor` V1. Pour debug :

```bash
# 1. Vérifier que le wrapper trouve le prompt
ls -l "$HOME/Documents/Obsidian/vault/Homelab/alfred_project_instructions.md"

# 2. Tester avec un prompt trivial
alfred "Réponds en un mot : OK"

# 3. Vérifier le modèle utilisé (verbose claude)
claude -p --model claude-opus-4-7 --system-prompt "Tu es Alfred." "Quel modèle es-tu ?"

# 4. Si le wrapper plante : lire le shebang et les chemins
head -10 ~/.local/bin/alfred
which alfred
readlink ~/.local/bin/alfred
```

---

## TODO

- [ ] Décider si on bloque `--disallowed-tools "Bash,Write,Edit"` pour qu'Alfred soit lecture-only par défaut.
- [ ] Décider si on déplace `~/.local/bin/leo` vers `bin/leo` pour symétrie avec Jarvis et Alfred (le system prompt vit déjà côté repo dans `share/leo/`, le wrapper devrait suivre).
- [ ] Si pattern stable : créer `share/alfred/` avec templates de réponses pour les actions homelab récurrentes (provisioning, migration, debug).
