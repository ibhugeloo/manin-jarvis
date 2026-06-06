#!/bin/zsh
# Finance — déclenche l'analyse earnings du jour J pour le portefeuille (votre broker).
# Lancé par launchd à 6h00 (votre fuseau local) chaque matin.
# Lit ~/.local/share/jarvis/config/finance.yaml, déclenche /earnings-watch
# sur les tickers à analyser, écrit dans ~/Documents/Obsidian/vault/Holding/Earnings/
# Pousse sur Telegram pour chaque nouveau rapport généré.

set -uo pipefail

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="$HOME/Documents/Obsidian/vault/Holding/Earnings"
PROMPT_FILE="$HOME/.local/share/jarvis/finance-prompt.md"
LOG="$HOME/.local/var/log/jarvis-finance.log"
CLAUDE_BIN="$HOME/.local/bin/claude"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$(dirname "$LOG")"

{
  echo ""
  echo "===================="
  echo "[$(date)] Finance start — date=$DATE"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary not found at $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt file not found at $PROMPT_FILE" >> "$LOG"
  exit 1
fi

# PATH minimal pour launchd
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Snapshot des notes earnings AVANT exécution (pour détecter les nouvelles).
BEFORE_LIST=$(mktemp)
ls "$OUTPUT_DIR" 2>/dev/null | sort > "$BEFORE_LIST"

# Substitue la date dans le prompt
PROMPT=$(sed "s|__DATE__|$DATE|g" "$PROMPT_FILE")

# Lance via le wrapper robuste : retries + fallback Opus → Sonnet → Haiku
ROBUST="$HOME/.local/bin/claude-p-robust.sh"
if [[ -x "$ROBUST" ]]; then
  echo "$PROMPT" | "$ROBUST" --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
else
  echo "$PROMPT" | "$CLAUDE_BIN" --print --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
fi

EXIT=$?

# Snapshot APRÈS exécution + diff = nouvelles notes
AFTER_LIST=$(mktemp)
ls "$OUTPUT_DIR" 2>/dev/null | sort > "$AFTER_LIST"

NEW_NOTES=$(comm -13 "$BEFORE_LIST" "$AFTER_LIST" | grep -E "^[A-Z.]+-${DATE}\.md$" || true)
NEW_COUNT=$(echo "$NEW_NOTES" | grep -c . || echo 0)

rm -f "$BEFORE_LIST" "$AFTER_LIST"

if [[ $EXIT -ne 0 ]]; then
  echo "[$(date)] Finance FAIL: exit=$EXIT, new_notes=$NEW_COUNT" >> "$LOG"
  osascript -e "display notification \"Échec Finance — voir $LOG\" with title \"Jarvis Finance\" sound name \"Basso\"" 2>/dev/null || true
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "❌ jarvis-finance a échoué ce matin — voir logs sur le Mac." 2>/dev/null || true
  exit "$EXIT"
fi

if [[ $NEW_COUNT -eq 0 ]]; then
  echo "[$(date)] Finance OK: aucune earnings à analyser aujourd'hui" >> "$LOG"
  exit 0
fi

echo "[$(date)] Finance OK: $NEW_COUNT nouvelle(s) note(s) earnings" >> "$LOG"

# Notification macOS systématique
osascript -e "display notification \"$NEW_COUNT rapport(s) earnings du $DATE généré(s)\" with title \"Jarvis Finance\" subtitle \"Disponible dans Obsidian/Holding/Earnings/\"" 2>/dev/null || true

# Push Telegram pour chaque nouveau rapport
if [[ -x "$HOME/.local/bin/jarvis-notify" ]]; then
  while IFS= read -r note; do
    [[ -z "$note" ]] && continue
    NOTE_PATH="$OUTPUT_DIR/$note"
    TICKER="${note%-${DATE}.md}"

    # Extraire l'action concrète (ligne en gras sous "## Action concrète")
    ACTION=$(awk '/^## Action concrète/{flag=1; next} flag && /^\*\*/{print; exit} flag && /^## /{flag=0}' "$NOTE_PATH" | head -1 | sed 's/\*\*//g' || echo "?")

    # Extraire 3 premières lignes de "Confrontation à la thèse perso"
    THESIS=$(awk '/^## Confrontation à la thèse perso/{flag=1; next} /^## /{flag=0} flag' "$NOTE_PATH" | grep -v "^$" | grep -v "^Thèse le boss" | head -3)

    "$HOME/.local/bin/jarvis-notify" "📊 *$TICKER — earnings $DATE*

Action : $ACTION

$THESIS

_Détail : Obsidian/Holding/Earnings/$note_" --markdown 2>/dev/null || true

    echo "[$(date)] Finance push Telegram envoyé pour $note" >> "$LOG"
  done <<< "$NEW_NOTES"
fi

exit 0
