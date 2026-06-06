#!/bin/zsh
# jarvis-save-current-session — Sauvegarde manuelle de la session Claude Code
# en cours, SANS fermer la session via /exit.
#
# Usage : appelé via le slash command Claude Code `/save` ou directement en
# ligne de commande depuis un terminal Claude actif.
#
# Logique :
#   1. Identifie le cwd courant (la session Claude Code l'hérite par défaut)
#   2. Mappe vers ~/.claude/projects/<cwd-key>/ (Claude Code remplace / et
#      espaces par -)
#   3. Prend le .jsonl le plus récemment modifié = transcript de la session
#      active dans ce dossier
#   4. Reconstruit le JSON d'input attendu par jarvis-session-recap.sh
#      (transcript_path, session_id, cwd, reason="manual_save")
#   5. Pipe vers le hook qui détache automatiquement en background
#
# Le `reason="manual_save"` indique au hook recap de NE PAS désinscrire la
# session du registre actif (elle continue de tourner après la sauvegarde).

set -uo pipefail

CWD="${PWD}"

# Mapping cwd → dossier transcripts Claude Code
CWD_KEY=$(printf '%s' "$CWD" | sed 's|[/ ]|-|g')
TRANSCRIPTS_DIR="$HOME/.claude/projects/$CWD_KEY"

if [[ ! -d "$TRANSCRIPTS_DIR" ]]; then
  echo "❌ Aucun transcript Claude Code trouvé pour ce cwd."
  echo "   cwd : $CWD"
  echo "   cherché dans : $TRANSCRIPTS_DIR"
  exit 1
fi

# Transcript le plus récemment modifié = session active courante
TRANSCRIPT_PATH=$(ls -t "$TRANSCRIPTS_DIR"/*.jsonl 2>/dev/null | head -1)

if [[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]]; then
  echo "❌ Aucun fichier .jsonl trouvé dans $TRANSCRIPTS_DIR"
  exit 1
fi

SESSION_ID=$(basename "$TRANSCRIPT_PATH" .jsonl)
LINES=$(wc -l < "$TRANSCRIPT_PATH" | tr -d ' ')
SHORT_ID=$(printf '%s' "$SESSION_ID" | head -c 8)

echo "📝 Sauvegarde session $SHORT_ID ($LINES lignes JSONL)"

if ! command -v jq >/dev/null 2>&1; then
  echo "❌ jq absent (requis pour construire le JSON d'input)"
  exit 1
fi

INPUT=$(jq -nc \
  --arg p "$TRANSCRIPT_PATH" \
  --arg s "$SESSION_ID" \
  --arg c "$CWD" \
  --arg r "manual_save" \
  '{transcript_path: $p, session_id: $s, cwd: $c, reason: $r}')

RECAP_HOOK="$HOME/.local/bin/jarvis-session-recap.sh"
if [[ ! -x "$RECAP_HOOK" ]]; then
  echo "❌ Hook recap absent : $RECAP_HOOK"
  exit 1
fi

# Le hook détache en background → retour instantané (< 1s)
printf '%s' "$INPUT" | "$RECAP_HOOK"

echo "✅ Récap lancé en background."
echo "   Sortie attendue sous ~30-60s :"
echo "   ~/Documents/Obsidian/vault/Claude/Sessions/"
echo "   Suivi log : tail -f ~/.local/var/log/jarvis-session-recap.log"
exit 0
