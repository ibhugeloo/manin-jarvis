#!/bin/zsh
# jarvis-context-watch.sh — garde-fou mécanique de discipline de contexte.
#
# Hook UserPromptSubmit : mesure la taille du transcript de la session et émet
# (une seule fois par palier franchi) un avertissement quand la session devient
# longue → risque de dégradation ("dumb zone").
#
# Heuristique VOLONTAIREMENT grossière : la taille du JSONL inclut l'historique
# brut (tool results compactés inclus), donc ≠ contexte effectif. C'est un proxy
# de "session marathon", pas une mesure exacte du %. Paliers ajustables ci-dessous.
#
# Ne bloque JAMAIS un prompt : toute erreur → exit 0 silencieux.
set +e

INPUT=$(cat 2>/dev/null)
command -v jq >/dev/null 2>&1 || exit 0

TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

BYTES=$(stat -f%z "$TRANSCRIPT" 2>/dev/null || echo 0)
MB=$(( BYTES / 1048576 ))

# Paliers (Mo de transcript) → niveau d'alerte
LEVEL=0
[ "$MB" -ge 6 ]  && LEVEL=1
[ "$MB" -ge 11 ] && LEVEL=2
[ "$MB" -ge 16 ] && LEVEL=3
[ "$LEVEL" -eq 0 ] && exit 0

# Anti-spam : un seul avertissement par palier et par session
STATE_DIR="$HOME/.local/var/jarvis-context-watch"
mkdir -p "$STATE_DIR" 2>/dev/null
STATE="$STATE_DIR/${SID}.level"
LAST=$(cat "$STATE" 2>/dev/null || echo 0)
[ "$LEVEL" -le "$LAST" ] 2>/dev/null && exit 0
echo "$LEVEL" > "$STATE" 2>/dev/null

case "$LEVEL" in
  1) MSG="🟡 Discipline de contexte — session substantielle (~${MB} Mo de transcript). Avant une nouvelle phase lourde, envisager un /compact ciblé (\"garde X, drop Y\"). (Heuristique grossière : taille transcript ≠ contexte exact.)" ;;
  2) MSG="🟠 Discipline de contexte — session longue (~${MB} Mo). Zone de dégradation possible. Recommandé : /compact ciblé maintenant, ou un récap-handoff si une tâche indépendante commence." ;;
  3) MSG="🔴 Discipline de contexte — session très longue (~${MB} Mo). Risque réel de dégradation / erreurs. Fortement recommandé : /compact, ou nouvelle session avec handoff AVANT toute action prod/risquée." ;;
esac

jq -nc --arg c "$MSG" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$c}}' 2>/dev/null || true
exit 0
