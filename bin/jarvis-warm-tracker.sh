#!/bin/zsh
# jarvis-warm-tracker — Hook PreToolUse:Read pour mesurer le tier WARM/COLD.
#
# Logge chaque lecture de fichier WARM ou COLD dans ~/.local/var/log/jarvis-warm-hits.log
# Format CSV : timestamp,cwd,file_path,tier
#
# Filtres : seulement WARM (Obsidian/<contexte>/) et COLD (decisions-archive/detail, _archives/, Sessions/).
# Les Read de fichiers code ou autres sont ignorés silencieusement.
#
# Le hook est non-bloquant : jamais d'erreur remontée à Claude Code (exit 0 systématique).
# Bypass : env JARVIS_WARM_TRACKER_OFF=1

set -uo pipefail

# Bypass explicite
if [[ "${JARVIS_WARM_TRACKER_OFF:-0}" == "1" ]]; then
  exit 0
fi

LOG="$HOME/.local/var/log/jarvis-warm-hits.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || exit 0

INPUT=$(cat)

# Extraction tool_name + file_path (silent-fail si jq manque ou JSON invalide)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)

# Filtre : on ne s'occupe que de Read (sécurité — devrait déjà être filtré par matcher)
[[ "$TOOL_NAME" != "Read" ]] && exit 0
[[ -z "$FILE_PATH" ]] && exit 0

# Détection tier
TIER=""

# WARM patterns (cf. agents.md §10) — vault path est Obsidian/vault/<bucket>/
case "$FILE_PATH" in
  */vault/ClientA/*)        TIER="WARM:client" ;;
  */vault/ShopApp/*)      TIER="WARM:shop-app" ;;
  */vault/AgencyApp/*)   TIER="WARM:agency-app" ;;
  */vault/Agency/*)       TIER="WARM:agency" ;;
  */vault/Holding/*)      TIER="WARM:holding" ;;
  */vault/Homelab/*)     TIER="WARM:homelab" ;;
  */vault/Personnes/*)   TIER="WARM:personnes" ;;
  */vault/Ressources/*)  TIER="WARM:ressources" ;;
esac

# COLD patterns (si pas déjà WARM)
if [[ -z "$TIER" ]]; then
  case "$FILE_PATH" in
    */Memory/decisions-archive.md)      TIER="COLD:decisions-archive" ;;
    */Memory/decisions-detail.md)       TIER="COLD:decisions-detail" ;;
    */Memory/_archives/*)               TIER="COLD:memory-archives" ;;
    */Memory/auto/_negative-signals.md) TIER="COLD:negative-signals" ;;
    */Claude/Sessions/*)                TIER="COLD:sessions-history" ;;
    */Brief/*-evaluation.md)            TIER="COLD:brief-evaluation" ;;
    */Brief/*-dream.md)                 TIER="COLD:brief-dream" ;;
  esac
fi

# Pas WARM/COLD → silence
[[ -z "$TIER" ]] && exit 0

# Log CSV (best-effort, jamais bloquant)
{
  printf '%s,%s,%s,%s\n' \
    "$(date +%Y-%m-%dT%H:%M:%S)" \
    "$PWD" \
    "$FILE_PATH" \
    "$TIER" \
    >> "$LOG"
} 2>/dev/null || true

exit 0
