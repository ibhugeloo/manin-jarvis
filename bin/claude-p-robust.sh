#!/bin/zsh
# claude-p-robust — Wrapper résilient autour de `claude -p`.
#
# Apporte :
# - Retry automatique (2 tentatives) avec backoff
# - Fallback de modèle : si Opus échoue → Sonnet → Haiku
# - Log structuré dans ~/.local/var/log/claude-p-robust.log
# - Notification Telegram si échec définitif
#
# Usage :
#     echo "prompt" | claude-p-robust [--model opus|sonnet|haiku] [args claude -p]
#
# Conçu pour les routines critiques (brief matinal, routines récurrentes)
# qui ne doivent pas planter à cause d'un hoquet API.

set -uo pipefail

CLAUDE_BIN="$HOME/.local/bin/claude"
LOG="$HOME/.local/var/log/claude-p-robust.log"
RETRIES=2
RETRY_BACKOFF=5  # secondes

mkdir -p "$(dirname "$LOG")"

# Parse les args : extraire --model, garder le reste pour passer à claude
MODEL=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --model=*)
      MODEL="${1#--model=}"
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

# Si pas de modèle spécifié, défaut Sonnet (compromis vitesse/qualité)
[[ -z "$MODEL" ]] && MODEL="sonnet"

# Chaîne de fallback selon le modèle initial
case "$MODEL" in
  opus)   MODELS=("opus" "sonnet" "haiku") ;;
  sonnet) MODELS=("sonnet" "haiku") ;;
  haiku)  MODELS=("haiku") ;;
  *)      MODELS=("$MODEL") ;;  # modèle custom, pas de fallback
esac

# Lire stdin une fois (on va le retransmettre à chaque tentative)
PROMPT=$(cat)
PROMPT_HASH=$(printf '%s' "$PROMPT" | shasum -a 256 | cut -c 1-12)

ATTEMPT=0
TOTAL_ATTEMPTS=0

for current_model in "${MODELS[@]}"; do
  for retry in $(seq 0 $RETRIES); do
    TOTAL_ATTEMPTS=$((TOTAL_ATTEMPTS + 1))
    ATTEMPT=$((ATTEMPT + 1))
    started=$(date +%s)

    {
      echo "[$(date)] attempt=$TOTAL_ATTEMPTS model=$current_model retry=$retry hash=$PROMPT_HASH"
    } >> "$LOG"

    # Lancer claude avec le modèle courant
    OUTPUT=$(printf '%s' "$PROMPT" | "$CLAUDE_BIN" --print --model "$current_model" "${ARGS[@]}" 2>>"$LOG")
    EXIT=$?
    elapsed=$(( $(date +%s) - started ))

    if [[ $EXIT -eq 0 && -n "$OUTPUT" ]]; then
      echo "[$(date)] OK attempt=$TOTAL_ATTEMPTS model=$current_model elapsed=${elapsed}s len=${#OUTPUT}" >> "$LOG"
      printf '%s' "$OUTPUT"
      exit 0
    fi

    echo "[$(date)] FAIL attempt=$TOTAL_ATTEMPTS model=$current_model exit=$EXIT elapsed=${elapsed}s" >> "$LOG"

    # Backoff entre retries (sauf après le dernier retry pour ce modèle)
    if [[ $retry -lt $RETRIES ]]; then
      sleep $((RETRY_BACKOFF * (retry + 1)))
    fi
  done
done

# Tous les modèles ont échoué
echo "[$(date)] DEFINITIVE FAIL after $TOTAL_ATTEMPTS attempts across ${#MODELS[@]} models" >> "$LOG"

# Notif Telegram si dispo
if [[ -x "$HOME/.local/bin/jarvis-notify" ]]; then
  "$HOME/.local/bin/jarvis-notify" "❌ claude -p a échoué $TOTAL_ATTEMPTS fois sur ${#MODELS[@]} modèles. Voir $LOG" 2>/dev/null || true
fi

exit 1
