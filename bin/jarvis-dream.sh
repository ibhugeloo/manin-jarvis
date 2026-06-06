#!/bin/zsh
# Jarvis dream — consolidation de mémoire nocturne (pattern OpenClaw).
# Lancé par launchd à 04h00 chaque matin (avant finance 06h).
# Sortie : ~/Documents/Obsidian/vault/Brief/YYYY-MM-DD-dream.md

set -uo pipefail

DATE=$(date +%Y-%m-%d)
BRIEF_DIR="$HOME/Documents/Obsidian/vault/Brief"
BRIEF_FILE="$BRIEF_DIR/$DATE-dream.md"
PROMPT_FILE="$HOME/.local/share/jarvis/dream-prompt.md"
LOG="$HOME/.local/var/log/jarvis-dream.log"
CLAUDE_BIN="$HOME/.local/bin/claude"

mkdir -p "$BRIEF_DIR"
mkdir -p "$(dirname "$LOG")"

{
  echo ""
  echo "===================="
  echo "[$(date)] Dream start — date=$DATE"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary not found at $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt file not found at $PROMPT_FILE" >> "$LOG"
  exit 1
fi

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Substitue les placeholders dans le prompt
PROMPT=$(sed -e "s|__DATE__|$DATE|g" -e "s|__BRIEF_DIR__|$BRIEF_DIR|g" "$PROMPT_FILE")

# Lance via le wrapper robuste : retries + fallback Opus → Sonnet → Haiku
ROBUST="$HOME/.local/bin/claude-p-robust.sh"
if [[ -x "$ROBUST" ]]; then
  echo "$PROMPT" | "$ROBUST" --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
else
  echo "$PROMPT" | "$CLAUDE_BIN" --print --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
fi

EXIT=$?

if [[ $EXIT -eq 0 && -f "$BRIEF_FILE" ]]; then
  echo "[$(date)] Dream OK: $BRIEF_FILE ($(wc -l < "$BRIEF_FILE") lignes)" >> "$LOG"
else
  echo "[$(date)] Dream FAIL: exit=$EXIT, file_exists=$([[ -f "$BRIEF_FILE" ]] && echo yes || echo no)" >> "$LOG"
  exit 1
fi
