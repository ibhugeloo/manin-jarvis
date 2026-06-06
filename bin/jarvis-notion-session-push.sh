#!/bin/zsh
# jarvis-notion-session-push — Push un récap de session vers Notion Inbox Jarvis.
#
# Appelé par jarvis-session-recap.sh en arrière-plan (& detach) pour ne pas
# bloquer la fin de session Claude Code. Toutes les sessions sont sauvegardées —
# le tri se fera à l'audit mensuel (cf. décision 2026-05-06 : auto-eval clean).
#
# Usage : jarvis-notion-session-push.sh <recap_file.md>
#
# Anti-récursion : hérite de JARVIS_RECAP_RUNNING=1 du parent. Le claude -p
# que ce script lance déclenchera son propre SessionEnd, mais le hook
# session-recap voit la var et exit 0 → pas de boucle.

set -uo pipefail

RECAP_FILE="${1:-}"
CLAUDE_BIN="$HOME/.local/bin/claude"
ROBUST="$HOME/.local/bin/claude-p-robust.sh"
LOG="$HOME/.local/var/log/jarvis-notion-session-push.log"

# Inbox Jarvis — UUID stable, cf. feedback_workflow_sauvegarde_notion.md
INBOX_JARVIS_ID="<your-notion-inbox-page-id>"

mkdir -p "$(dirname "$LOG")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# Marqueur anti-récursion explicite — le claude -p ci-dessous ne doit pas
# re-déclencher de push Notion à sa fermeture.
export JARVIS_RECAP_RUNNING=1
export JARVIS_NOTION_PUSH_RUNNING=1

{
  echo ""
  echo "===================="
  echo "[$(date)] Notion push start — file=$RECAP_FILE"
} >> "$LOG"

if [[ -z "$RECAP_FILE" || ! -f "$RECAP_FILE" ]]; then
  echo "[$(date)] ERROR: recap file '$RECAP_FILE' absent" >> "$LOG"
  exit 1
fi

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary absent à $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

# Extraire métadata du frontmatter pour le titre Notion
DATE=$(grep -m 1 '^date:' "$RECAP_FILE" | sed 's/^date:[[:space:]]*//' | tr -d ' ')
PROJECT=$(grep -m 1 '^projet:' "$RECAP_FILE" | sed 's/^projet:[[:space:]]*//' | sed 's|.*/||')
TITLE=$(grep -m 1 '^# Session' "$RECAP_FILE" | sed 's/^# Session [0-9-]* — //')

[[ -z "$DATE" ]] && DATE=$(date +%Y-%m-%d)
[[ -z "$TITLE" ]] && TITLE="Session"
[[ -z "$PROJECT" ]] && PROJECT="—"

NOTION_TITLE="$TITLE — $DATE"

# Lire le contenu du récap (sans le frontmatter YAML)
RECAP_CONTENT=$(awk '/^---$/{c++; next} c>=2{print}' "$RECAP_FILE")

PROMPT="Tu dois créer une sous-page dans la page Notion 'Inbox Jarvis' avec l'ID parent : $INBOX_JARVIS_ID.

Utilise l'outil mcp__claude_ai_Notion__notion-create-pages avec :
- parent.type = \"page_id\"
- parent.page_id = \"$INBOX_JARVIS_ID\"
- pages[0].properties.title = \"$NOTION_TITLE\"
- pages[0].content = le contenu Markdown ci-dessous (récap brut, NE PAS reformuler)

Contenu Markdown à mettre dans la page :

---PROJET : $PROJECT---

$RECAP_CONTENT

---

Une fois la page créée, renvoie UNIQUEMENT l'URL de la page créée (rien d'autre, pas de phrase, juste l'URL). Si l'outil échoue, renvoie 'ERROR: <raison>'."

# Appel claude -p avec MCP Notion (model haiku — création simple, pas besoin d'opus)
if [[ -x "$ROBUST" ]]; then
  RESULT=$(printf '%s' "$PROMPT" | "$ROBUST" --model haiku --dangerously-skip-permissions --output-format text 2>>"$LOG")
else
  RESULT=$(printf '%s' "$PROMPT" | "$CLAUDE_BIN" --print --model haiku --dangerously-skip-permissions --output-format text 2>>"$LOG")
fi

EXIT=$?

if [[ $EXIT -ne 0 || -z "$RESULT" ]]; then
  echo "[$(date)] FAIL exit=$EXIT result='$RESULT'" >> "$LOG"
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && \
    "$HOME/.local/bin/jarvis-notify" "❌ Push Notion session KO — voir log" --silent 2>/dev/null || true
  exit $EXIT
fi

# Extraire URL Notion du résultat (heuristique simple)
NOTION_URL=$(printf '%s' "$RESULT" | grep -oE 'https://[a-z0-9.-]*notion\.so/[A-Za-z0-9-]+' | head -1)

if [[ -n "$NOTION_URL" ]]; then
  echo "[$(date)] OK url=$NOTION_URL" >> "$LOG"
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && \
    "$HOME/.local/bin/jarvis-notify" "📥 Session sauvegardée : $NOTION_TITLE
$NOTION_URL" --silent 2>/dev/null || true
else
  echo "[$(date)] OK mais URL non extraite. Résultat : $RESULT" >> "$LOG"
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && \
    "$HOME/.local/bin/jarvis-notify" "📥 Session push Notion : $NOTION_TITLE (URL inconnue)" --silent 2>/dev/null || true
fi

exit 0
