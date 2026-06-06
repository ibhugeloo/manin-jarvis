#!/bin/zsh
# notion-export — Mirror les pages Notion listées vers ~/Documents/Obsidian/vault/Notion-Mirror/
# Usage : notion-export.sh [--dry-run]
#
# Lit la liste depuis ~/Documents/Obsidian/vault/Claude/Jarvis/notion-pages.txt
# Une page (URL ou UUID) par ligne. Les lignes vides et # sont ignorées.

set -uo pipefail

CLAUDE_BIN="$HOME/.local/bin/claude"
JARVIS_DIR="$HOME/Documents/Obsidian/vault/Claude/Jarvis"
PAGES_FILE="$JARVIS_DIR/notion-pages.txt"
PROMPT_FILE="$HOME/.local/share/jarvis/notion-export-prompt.md"
MIRROR_DIR="$HOME/Documents/Obsidian/vault/Notion-Mirror"
LOG="$HOME/.local/var/log/jarvis-notion-export.log"

mkdir -p "$MIRROR_DIR" "$(dirname "$LOG")"

DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

{
  echo ""
  echo "===================="
  echo "[$(date)] Notion export start"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary absent" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PAGES_FILE" ]]; then
  echo "[$(date)] ERROR: $PAGES_FILE absent" >> "$LOG"
  exit 1
fi

# Extraire les pages non commentées et non vides
PAGES_LIST=$(grep -vE '^\s*(#|$)' "$PAGES_FILE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

if [[ -z "$PAGES_LIST" ]]; then
  echo "[$(date)] No pages to export (notion-pages.txt is empty)" >> "$LOG"
  echo "ℹ️  Aucune page configurée dans $PAGES_FILE — rien à exporter."
  echo "    Éditez ce fichier pour ajouter des URLs ou IDs Notion."
  exit 0
fi

PAGE_COUNT=$(echo "$PAGES_LIST" | wc -l | tr -d ' ')
echo "[$(date)] Pages à exporter : $PAGE_COUNT" >> "$LOG"

if [[ "$DRY" -eq 1 ]]; then
  echo "DRY RUN — pages qui seraient exportées :"
  echo "$PAGES_LIST" | sed 's/^/  → /'
  echo ""
  echo "Vers : $MIRROR_DIR"
  exit 0
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt $PROMPT_FILE absent" >> "$LOG"
  exit 1
fi

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Substitue les variables dans le prompt
PROMPT=$(sed -e "s|__DATE__|$DATE|g" \
              -e "s|__TIME__|$TIME|g" \
              -e "s|__MIRROR_DIR__|$MIRROR_DIR|g" \
              "$PROMPT_FILE")

# Injection de la liste des pages
PROMPT="${PROMPT//__PAGES_LIST__/$PAGES_LIST}"

ROBUST="$HOME/.local/bin/claude-p-robust.sh"
if [[ -x "$ROBUST" ]]; then
  echo "$PROMPT" | "$ROBUST" --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
else
  echo "$PROMPT" | "$CLAUDE_BIN" --print --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
fi

EXIT=$?

if [[ $EXIT -eq 0 && -f "$MIRROR_DIR/_sync-status.md" ]]; then
  echo "[$(date)] Notion export OK — voir $MIRROR_DIR/_sync-status.md" >> "$LOG"
  osascript -e "display notification \"Notion mirror synchronisé ($PAGE_COUNT pages)\" with title \"Jarvis\"" 2>/dev/null || true
  # Notif Telegram silencieuse (pas d'alerte sonore — c'est juste du sync)
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "🔄 Notion mirror sync OK ($PAGE_COUNT pages)" --silent 2>/dev/null || true
else
  echo "[$(date)] Notion export FAIL : exit=$EXIT" >> "$LOG"
  osascript -e "display notification \"Échec mirror Notion — voir log\" with title \"Jarvis\" sound name \"Basso\"" 2>/dev/null || true
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "❌ Échec sync Notion mirror" 2>/dev/null || true
fi

exit $EXIT
