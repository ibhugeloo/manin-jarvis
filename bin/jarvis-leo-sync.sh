#!/bin/zsh
# jarvis-leo-sync — pont mémoire Leo -> Jarvis.
#   Demande à Leo (Hermes/GPT-5.5, LXC <your-lxc-id>) un récap de ses conversations avec
#   le boss (Telegram) depuis le dernier sync, et l'écrit dans le vault Obsidian
#   (Brief/leo-feed.md, plus récent en haut). Jarvis lit ce feed pour rester synchro.
#
#   - Récap : GPT-5.5 (mémoire de Leo)  -> 0 token Anthropic.
#   - Écriture : locale dans le vault    -> fiable, déterministe, ni MCP ni token.
#
# Déclenché auto 1x/jour à 23h00 par le LaunchAgent com.example.jarvis.leo-sync,
# et à la demande :  jarvis leo-sync
set -uo pipefail

KEY="$HOME/.ssh/<your-homelab-key>"
PVE="root@<homelab-host>"
CTID="<your-lxc-id>"
FEED="$HOME/Documents/Obsidian/vault/Brief/leo-feed.md"
MARKER="$HOME/.local/var/jarvis-leo-sync-last"
LOG="$HOME/.local/var/log/jarvis-leo-sync.log"
mkdir -p "$(dirname "$LOG")" "$(dirname "$MARKER")" "$(dirname "$FEED")"

SINCE="$(cat "$MARKER" 2>/dev/null || echo 'le tout début')"
echo "[$(date)] leo-sync start (since=$SINCE)" >> "$LOG"

# 1. Récap demandé à Leo (GPT-5.5) depuis sa mémoire persistante
RECAP_PROMPT="Tu es Leo. Pour ton pair Jarvis, résume les points IMPORTANTS de tes conversations avec le boss (notamment via Telegram) depuis $SINCE : décisions prises, faits nouveaux, todos, préférences exprimées. Format en bullets groupés sous '## Décisions', '## Faits', '## Todos', '## Préférences' (n'écris que les sections non vides). Pas de transcript, juste l'essentiel actionnable pour Jarvis. Si rien de notable depuis $SINCE, réponds EXACTEMENT : RAS"
B64=$(printf '%s' "$RECAP_PROMPT" | base64 | tr -d '\n')
RECAP=$(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15 "$PVE" \
  "pct exec $CTID -- bash -c 'P=\$(printf %s $B64 | base64 -d); timeout 180 /usr/local/bin/hermes -z \"\$P\"'" 2>>"$LOG")

if [[ -z "$RECAP" ]]; then
  echo "[$(date)] ERREUR: récap vide (Leo injoignable ?)" >> "$LOG"
  echo "Erreur : récap Leo vide — voir $LOG" >&2; exit 1
fi

if printf '%s' "$RECAP" | grep -qiE '^[[:space:]]*RAS[[:space:]]*$'; then
  echo "[$(date)] RAS" >> "$LOG"
  echo "Leo : RAS depuis $SINCE — rien à transmettre à Jarvis."
  date '+%Y-%m-%d %H:%M' > "$MARKER"
  exit 0
fi

# 2. Écriture dans le vault (plus récent en haut). Jarvis lira ce feed.
STAMP="$(date '+%Y-%m-%d %H:%M')"
TMP="$(mktemp)"
{
  echo "## $STAMP — Leo sync (depuis $SINCE)"
  echo ""
  printf '%s\n' "$RECAP"
  echo ""
  echo "---"
  echo ""
  [[ -f "$FEED" ]] && cat "$FEED"
} > "$TMP"
mv "$TMP" "$FEED"

echo "[$(date)] OK -> $FEED" >> "$LOG"
echo "OK — récap Leo écrit dans le vault : $FEED (depuis $SINCE)."
date '+%Y-%m-%d %H:%M' > "$MARKER"
