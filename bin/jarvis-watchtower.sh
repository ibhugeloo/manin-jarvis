#!/bin/zsh
# Watchtower — surveillance quotidienne des projets clients (Agency).
# Lancé par launchd à 7h00 chaque matin.
# Génère deux rapports dans ~/Documents/Obsidian/vault/Watchtower/YYYY-MM-DD/
# Pousse sur Telegram uniquement si au moins un projet est 🔴.

set -uo pipefail

DATE=$(date +%Y-%m-%d)
WT_DIR="$HOME/Documents/Obsidian/vault/Watchtower/$DATE"
SUMMARY_FILE="$WT_DIR/summary.md"
DETAIL_FILE="$WT_DIR/detail.md"
PROMPT_FILE="$HOME/.local/share/jarvis/watchtower-prompt.md"
LOG="$HOME/.local/var/log/jarvis-watchtower.log"
CLAUDE_BIN="$HOME/.local/bin/claude"

mkdir -p "$WT_DIR"
mkdir -p "$(dirname "$LOG")"

{
  echo ""
  echo "===================="
  echo "[$(date)] Watchtower start — date=$DATE"
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

# Vérification : les deux fichiers doivent exister
if [[ $EXIT -ne 0 ]] || [[ ! -f "$SUMMARY_FILE" ]] || [[ ! -f "$DETAIL_FILE" ]]; then
  echo "[$(date)] Watchtower FAIL: exit=$EXIT, summary=$(test -f "$SUMMARY_FILE" && echo yes || echo no), detail=$(test -f "$DETAIL_FILE" && echo yes || echo no)" >> "$LOG"
  osascript -e "display notification \"Échec Watchtower — voir $LOG\" with title \"Jarvis Watchtower\" sound name \"Basso\"" 2>/dev/null || true
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "❌ Watchtower a échoué ce matin — voir logs sur le Mac." 2>/dev/null || true
  exit ${EXIT:-1}
fi

echo "[$(date)] Watchtower OK: $SUMMARY_FILE ($(wc -l < "$SUMMARY_FILE") lignes), $DETAIL_FILE ($(wc -l < "$DETAIL_FILE") lignes)" >> "$LOG"

# Notification macOS systématique (succès)
osascript -e "display notification \"Watchtower du $DATE généré\" with title \"Jarvis Watchtower\" subtitle \"Disponible dans Obsidian/Watchtower/\"" 2>/dev/null || true

# Push Telegram uniquement si au moins un projet est 🔴 dans le summary
# (cf. décision : ne notifier que sur rouge, pas sur jaune, pour ne pas sur-notifier)
if grep -q "🔴" "$SUMMARY_FILE"; then
  if [[ -x "$HOME/.local/bin/jarvis-notify" ]]; then
    # Extraire la section "Alertes 🔴" et la suggestion
    ALERTS=$(awk '/^## Alertes 🔴/{flag=1; next} /^## /{flag=0} flag' "$SUMMARY_FILE" | head -15)
    "$HOME/.local/bin/jarvis-notify" "🚨 Watchtower — alertes critiques

$ALERTS

_Détail : Obsidian/Watchtower/$DATE/_" --markdown 2>/dev/null || true
    echo "[$(date)] Watchtower 🔴 push Telegram envoyé" >> "$LOG"
  fi
else
  echo "[$(date)] Watchtower tout vert — pas de Telegram" >> "$LOG"
fi

exit 0
