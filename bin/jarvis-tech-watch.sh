#!/bin/zsh
# Jarvis tech watch — lancé par launchd à 8h00 chaque matin (après brief 7h30).
# Veille quotidienne sur l'écosystème agentic (Hermes/OpenClaude/Claude Code/patterns memory).
# Sortie : ~/Documents/Obsidian/vault/Brief/YYYY-MM-DD-tech-watch.md

set -uo pipefail

DATE=$(date +%Y-%m-%d)
BRIEF_DIR="$HOME/Documents/Obsidian/vault/Brief"
BRIEF_FILE="$BRIEF_DIR/$DATE-tech-watch.md"
PROMPT_FILE="$HOME/.local/share/jarvis/tech-watch-prompt.md"
LOG="$HOME/.local/var/log/jarvis-tech-watch.log"
CLAUDE_BIN="$HOME/.local/bin/claude"

mkdir -p "$BRIEF_DIR"
mkdir -p "$(dirname "$LOG")"

{
  echo ""
  echo "===================="
  echo "[$(date)] Tech watch start — date=$DATE"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary not found at $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt file not found at $PROMPT_FILE" >> "$LOG"
  exit 1
fi

# PATH minimal (launchd a un PATH très restreint par défaut)
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Substitue date + brief dir dans le prompt
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
  echo "[$(date)] Tech watch OK: $BRIEF_FILE ($(wc -l < "$BRIEF_FILE") lignes)" >> "$LOG"
  # Notification macOS native (pas de Telegram ici — la session Claude se charge du push si 🔴)
  osascript -e "display notification \"Veille tech du $DATE générée\" with title \"Jarvis\" subtitle \"Brief/$DATE-tech-watch.md\"" 2>/dev/null || true
else
  echo "[$(date)] Tech watch FAIL: exit=$EXIT, file_exists=$([[ -f "$BRIEF_FILE" ]] && echo yes || echo no)" >> "$LOG"
  exit 1
fi
