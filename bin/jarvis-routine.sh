#!/bin/zsh
# jarvis-routine — Runner générique des routines Jarvis (soir, hebdo, mensuel, etc.)
# Usage : jarvis-routine.sh <type>
#
# Charge le prompt correspondant à $type depuis ~/.local/share/jarvis/routine-<type>-prompt.md
# et exécute claude headless. Le prompt indique lui-même le chemin du fichier de sortie.

set -uo pipefail

CLAUDE_BIN="$HOME/.local/bin/claude"
SHARE_DIR="$HOME/.local/share/jarvis"
LOG="$HOME/.local/var/log/jarvis-routine.log"
BRIEF_DIR="$HOME/Documents/Obsidian/vault/Brief"

if [[ $# -lt 1 ]]; then
  echo "Usage: jarvis-routine.sh <soir|hebdo|mensuel|...>"
  exit 1
fi

TYPE="$1"
PROMPT_FILE="$SHARE_DIR/routine-$TYPE-prompt.md"

mkdir -p "$BRIEF_DIR" "$(dirname "$LOG")"

# Gating cadence — pour les routines à intervalle non-quotidien lancées par un cron quotidien.
# Bypass : JARVIS_ROUTINE_FORCE=1 jarvis-routine.sh <type>
gate_min_seconds=0
case "$TYPE" in
  evaluation) gate_min_seconds=$((4 * 86400)) ;;  # 4 jours (décision 2026-05-07)
esac

if [[ $gate_min_seconds -gt 0 && "${JARVIS_ROUTINE_FORCE:-0}" != "1" ]]; then
  GATE_FILE="$HOME/.local/var/jarvis-routine-$TYPE-last-run"
  if [[ -f "$GATE_FILE" ]]; then
    last=$(cat "$GATE_FILE" 2>/dev/null || echo 0)
    now=$(date +%s)
    elapsed=$(( now - last ))
    if [[ $elapsed -lt $gate_min_seconds ]]; then
      remaining=$(( (gate_min_seconds - elapsed) / 3600 ))
      echo "[$(date)] Routine $TYPE skip — dernier run il y a ${elapsed}s (gate ${gate_min_seconds}s, reste ~${remaining}h)" >> "$LOG"
      exit 0
    fi
  fi
fi

DATE=$(date +%Y-%m-%d)
WEEK=$(date +%G-W%V)        # ISO year-week, ex: 2026-W18
MONTH=$(date +%Y-%m)
TIME=$(date +%H:%M)

{
  echo ""
  echo "===================="
  echo "[$(date)] Routine $TYPE start — date=$DATE"
} >> "$LOG"

if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "[$(date)] ERROR: claude binary not at $CLAUDE_BIN" >> "$LOG"
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[$(date)] ERROR: prompt introuvable : $PROMPT_FILE" >> "$LOG"
  exit 1
fi

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# --- Filet de fraîcheur memory-sync (décision 2026-05-27 : repo GitHub = source canonique) ---
# Le vault est mirroré vers le repo par memory-sync (23h30). Si le sync casse en silence,
# le repo canonique se périme vs le vault (et Leo, qui le lit read-only, raisonne sur du périmé).
# Détection 100% déterministe (git log) — pas de LLM (cf. agents.md §11.2). Verdict injecté dans
# le prompt eval via __MEMORY_SYNC_FRESHNESS__. Seuils : WARN > 2j (Mac peut être éteint la nuit),
# CRIT > 4j (sync probablement cassé → alerte Telegram).
MEMORY_SYNC_FRESHNESS="(non vérifié — type != evaluation)"
if [[ "$TYPE" == "evaluation" ]]; then
  REPO="$HOME/Documents/GIT PROD/manin-jarvis"
  SYNC_TS=$(git -C "$REPO" log -1 --format=%ct --grep='^memory: sync' 2>/dev/null || true)
  if [[ -z "$SYNC_TS" ]]; then
    MEMORY_SYNC_FRESHNESS="🔴 memory-sync : aucun commit memory:sync trouvé dans le repo canonique. Vérifier le LaunchAgent com.example.jarvis.memory-sync + le log jarvis-memory-sync.log."
    [[ -x "$HOME/.local/bin/jarvis-msg" ]] && "$HOME/.local/bin/jarvis-msg" "🔴 memory-sync : aucun commit memory:sync dans le repo canonique. Sync cassé ? Vérifier le LaunchAgent." 2>/dev/null || true
  else
    now=$(date +%s)
    days=$(( (now - SYNC_TS) / 86400 ))
    if [[ $days -gt 4 ]]; then
      MEMORY_SYNC_FRESHNESS="🔴 memory-sync PÉRIMÉ — dernier memory:sync il y a ${days}j (> seuil critique 4j). Le repo canonique diverge du vault → Leo lit une doctrine périmée. Vérifier launchctl list grep memory-sync + le log jarvis-memory-sync.log, relancer jarvis memory-sync."
      [[ -x "$HOME/.local/bin/jarvis-msg" ]] && "$HOME/.local/bin/jarvis-msg" "🔴 memory-sync périmé : ${days}j sans sync. Repo canonique diverge du vault. Vérifier le LaunchAgent memory-sync." 2>/dev/null || true
    elif [[ $days -gt 2 ]]; then
      MEMORY_SYNC_FRESHNESS="🟡 memory-sync à surveiller — dernier memory:sync il y a ${days}j (seuil warn 2j). Possible Mac éteint la nuit ; si ça persiste, vérifier le LaunchAgent."
    else
      MEMORY_SYNC_FRESHNESS="🟢 memory-sync frais — dernier memory:sync il y a ${days}j."
    fi
  fi
  echo "[$(date)] memory-sync freshness: $MEMORY_SYNC_FRESHNESS" >> "$LOG"
fi

# Substitue les variables dans le prompt
PROMPT=$(sed -e "s|__DATE__|$DATE|g" \
              -e "s|__WEEK__|$WEEK|g" \
              -e "s|__MONTH__|$MONTH|g" \
              -e "s|__TIME__|$TIME|g" \
              -e "s|__BRIEF_DIR__|$BRIEF_DIR|g" \
              -e "s|__MEMORY_SYNC_FRESHNESS__|$MEMORY_SYNC_FRESHNESS|g" \
              "$PROMPT_FILE")

ROBUST="$HOME/.local/bin/claude-p-robust.sh"
if [[ -x "$ROBUST" ]]; then
  echo "$PROMPT" | "$ROBUST" --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
else
  echo "$PROMPT" | "$CLAUDE_BIN" --print --model opus --dangerously-skip-permissions --output-format text >> "$LOG" 2>&1
fi

EXIT=$?

# Détermine le fichier de sortie attendu selon le type
case "$TYPE" in
  soir)       OUT="$BRIEF_DIR/$DATE-soir.md" ;;
  veille)     OUT="$BRIEF_DIR/$DATE-veille.md" ;;
  hebdo)      OUT="$BRIEF_DIR/$WEEK-hebdo.md" ;;
  mensuel)    OUT="$BRIEF_DIR/$MONTH-mensuel.md" ;;
  evaluation) OUT="$BRIEF_DIR/$DATE-evaluation.md" ;;
  *)          OUT="$BRIEF_DIR/$DATE-$TYPE.md" ;;
esac

if [[ $EXIT -eq 0 && -f "$OUT" ]]; then
  echo "[$(date)] Routine $TYPE OK : $OUT ($(wc -l < "$OUT") lignes)" >> "$LOG"
  # Marquer le dernier run pour le gating à intervalle (cf. en-tête)
  if [[ $gate_min_seconds -gt 0 ]]; then
    mkdir -p "$HOME/.local/var"
    date +%s > "$HOME/.local/var/jarvis-routine-$TYPE-last-run"
  fi
  osascript -e "display notification \"Routine $TYPE générée\" with title \"Jarvis\" subtitle \"$(basename "$OUT")\"" 2>/dev/null || true
  if [[ -x "$HOME/.local/bin/jarvis-notify" ]]; then
    case "$TYPE" in
      soir)       EMOJI="🌙"; LABEL="Récap soir" ;;
      veille)     EMOJI="📡"; LABEL="Veille du jour" ;;
      hebdo)      EMOJI="📊"; LABEL="Revue hebdo" ;;
      mensuel)    EMOJI="📈"; LABEL="Bilan mensuel" ;;
      evaluation) EMOJI="🧠"; LABEL="Auto-évaluation" ;;
      *)          EMOJI="📝"; LABEL="Routine $TYPE" ;;
    esac
    # Extrait : Suggestion ou Recommandations selon le type
    EXTRACT=$(awk '/^## (🎯 |Suggestion|Recommandations|Plan pour|Question ouverte)/{flag=1; print; next} /^## /{flag=0} flag' "$OUT" | head -15)
    "$HOME/.local/bin/jarvis-notify" "$EMOJI $LABEL — $(basename "$OUT" .md)

$EXTRACT

_Détail complet dans le vault._" --markdown 2>/dev/null || true
  fi
else
  echo "[$(date)] Routine $TYPE FAIL : exit=$EXIT, file_exists=$(test -f "$OUT" && echo yes || echo no)" >> "$LOG"
  osascript -e "display notification \"Échec routine $TYPE\" with title \"Jarvis\" sound name \"Basso\"" 2>/dev/null || true
  [[ -x "$HOME/.local/bin/jarvis-notify" ]] && "$HOME/.local/bin/jarvis-notify" "❌ Échec routine $TYPE — voir logs." 2>/dev/null || true
fi

exit $EXIT
