#!/bin/zsh
# Jarvis daily brief — lancé par launchd à 7h30 chaque matin.
# Génère un brief matinal dans ~/Documents/Obsidian/vault/Brief/YYYY-MM-DD.md

set -uo pipefail

DATE=$(date +%Y-%m-%d)
BRIEF_DIR="$HOME/Documents/Obsidian/vault/Brief"
BRIEF_FILE="$BRIEF_DIR/$DATE.md"
PROMPT_FILE="$HOME/.local/share/jarvis/brief-prompt.md"
LOG="$HOME/.local/var/log/jarvis-brief.log"
CLAUDE_BIN="$HOME/.local/bin/claude"

mkdir -p "$BRIEF_DIR"
mkdir -p "$(dirname "$LOG")"

{
  echo ""
  echo "===================="
  echo "[$(date)] Brief start — date=$DATE"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary not found at $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt file not found at $PROMPT_FILE" >> "$LOG"
  exit 1
fi

# Charge le PATH minimal (launchd a un PATH très restreint par défaut)
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Charge les secrets centralisés (AGENCY_API_TOKEN, etc.) si présents
SECRETS_ENV="$HOME/.config/jarvis/secrets/env"
if [[ -f "$SECRETS_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SECRETS_ENV"
  set +a
fi

# Régénère l'index du vault (carte du second cerveau auto-loadée par CLAUDE.md)
# Coût : <100 ms, rafraîchit _vault-index.md avant que les sessions du jour démarrent.
if [[ -x "$HOME/.local/bin/jarvis-vault-index-build" ]]; then
  "$HOME/.local/bin/jarvis-vault-index-build" >> "$LOG" 2>&1 || \
    echo "[$(date)] WARN: jarvis-vault-index-build a échoué (non bloquant)" >> "$LOG"
fi

# Régénère l'index des skills auto-promus (Memory/auto/_index.md auto-loadé par CLAUDE.md)
# Pattern Hermes-like : skills auto-écrits par routine eval ou hook session-recap.
if [[ -x "$HOME/.local/bin/jarvis-skills-bundle" ]]; then
  "$HOME/.local/bin/jarvis-skills-bundle" >> "$LOG" 2>&1 || \
    echo "[$(date)] WARN: jarvis-skills-bundle a échoué (non bloquant)" >> "$LOG"
fi

# Substitue la date dans le prompt
PROMPT=$(sed "s|__DATE__|$DATE|g" "$PROMPT_FILE")

# Lance via le wrapper robuste : retries + fallback Opus → Sonnet → Haiku
# (résilience aux pannes API, cf. lessons.md #18)
ROBUST="$HOME/.local/bin/claude-p-robust.sh"
if [[ -x "$ROBUST" ]]; then
  echo "$PROMPT" | "$ROBUST" --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
else
  echo "$PROMPT" | "$CLAUDE_BIN" --print --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
fi

EXIT=$?

if [[ $EXIT -eq 0 && -f "$BRIEF_FILE" ]]; then
  echo "[$(date)] Brief OK: $BRIEF_FILE ($(wc -l < "$BRIEF_FILE") lignes)" >> "$LOG"
  osascript -e "display notification \"Brief du $DATE généré\" with title \"Jarvis\" subtitle \"Disponible dans Obsidian/Brief/\"" 2>/dev/null || true
  # Push Telegram avec extrait : titre + section "Suggestion du jour"
  if [[ -x "$HOME/.local/bin/jarvis-notify" ]]; then
    SUGGESTION=$(awk '/^## 🎯 Suggestion du jour/{flag=1; next} /^## /{flag=0} flag' "$BRIEF_FILE" | head -10)
    "$HOME/.local/bin/jarvis-notify" "📅 Brief du $DATE

$SUGGESTION

_Détail complet dans le vault._" --markdown 2>/dev/null || true
  fi
else
  echo "[$(date)] Brief FAIL: exit=$EXIT, file_exists=$(test -f "$BRIEF_FILE" && echo yes || echo no)" >> "$LOG"
  osascript -e "display notification \"Échec du brief — voir $LOG\" with title \"Jarvis\" sound name \"Basso\"" 2>/dev/null || true
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "❌ Échec du brief matinal — voir logs sur le Mac." 2>/dev/null || true
fi

exit $EXIT
