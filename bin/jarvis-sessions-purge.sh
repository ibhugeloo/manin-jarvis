#!/usr/bin/env bash
# jarvis-sessions-purge — Archive les recaps de session > N jours vers Notion (API directe),
# puis supprime le fichier local UNIQUEMENT si l'archivage Notion a réussi (HTTP 200).
#
# Pourquoi API directe et pas MCP : un cron n'a pas de contexte interactif, donc le
# connecteur claude.ai Notion (claude -p + MCP) échoue en headless. L'API Notion avec
# un token d'intégration est fiable en headless. Cf. décision leo-sync 2026-05-25.
#
# Garde de sûreté : aucune suppression sans 200 OK Notion. Le fichier reste sinon,
# re-tenté au prochain run. Idempotent : une session déjà archivée+supprimée ne revient pas.
#
# Token : lu dans ~/.config/jarvis/notion-archive.env (NOTION_TOKEN=ntn_xxx), chmod 600,
# JAMAIS versionné ni synchronisé (hors vault, hors repo).
#
# Usage :
#   jarvis-sessions-purge.sh            # run réel
#   jarvis-sessions-purge.sh --dry-run  # liste ce qui serait archivé+supprimé, ne touche rien
#
set -uo pipefail

RETENTION_DAYS="${JARVIS_SESSIONS_RETENTION_DAYS:-90}"
SESSIONS_DIR="$HOME/Documents/Obsidian/vault/Claude/Sessions"
TOKEN_FILE="$HOME/.config/jarvis/notion-archive.env"
INBOX_JARVIS_ID="<your-notion-inbox-page-id>"
NOTION_VERSION="2025-09-03"
LOG="$HOME/.local/var/log/jarvis-sessions-purge.log"
mkdir -p "$(dirname "$LOG")"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

log "=== run start (retention=${RETENTION_DAYS}j, dry_run=${DRY_RUN}) ==="

[[ -d "$SESSIONS_DIR" ]] || { log "FATAL: SESSIONS_DIR absent: $SESSIONS_DIR"; echo "Sessions dir absent"; exit 1; }

# Token (sauf en dry-run où on ne contacte pas Notion)
NOTION_TOKEN=""
if [[ -f "$TOKEN_FILE" ]]; then
  # shellcheck disable=SC1090
  NOTION_TOKEN="$(grep -E '^NOTION_TOKEN=' "$TOKEN_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r\n')"
fi
if [[ $DRY_RUN -eq 0 && -z "$NOTION_TOKEN" ]]; then
  log "FATAL: token Notion absent ($TOKEN_FILE) — rien supprimé."
  echo "❌ Token Notion absent : $TOKEN_FILE — voir setup. Aucune suppression."
  exit 1
fi

# Date de coupure (macOS BSD date)
CUTOFF="$(date -v-"${RETENTION_DAYS}"d +%Y-%m-%d)"
log "cutoff date = $CUTOFF (fichiers dont le préfixe AAAA-MM-JJ est antérieur seront traités)"

archived=0 deleted=0 skipped=0 failed=0 candidates=0

# Sélection par DATE DU NOM DE FICHIER (déterministe, robuste vs mtime modifié par rsync).
# Format attendu : AAAA-MM-JJ-HHMM-<uuid>-<slug>.md
while IFS= read -r f; do
  base="$(basename "$f")"
  fdate="${base:0:10}"
  [[ "$fdate" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { log "skip (nom non daté): $base"; continue; }
  [[ "$fdate" < "$CUTOFF" ]] || continue
  candidates=$((candidates+1))

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] archiverait+supprimerait : $base"
    log "dry-run candidate: $base"
    continue
  fi

  # Archive Notion via API. Le helper python imprime 'OK <url>' sur 200, sinon 'ERR <détail>'.
  result="$(NOTION_TOKEN="$NOTION_TOKEN" NOTION_VERSION="$NOTION_VERSION" \
            INBOX_JARVIS_ID="$INBOX_JARVIS_ID" python3 "$(dirname "$0")/jarvis-notion-archive-page.py" "$f" 2>>"$LOG")"
  if [[ "$result" == OK* ]]; then
    archived=$((archived+1))
    if rm -f "$f"; then
      deleted=$((deleted+1))
      log "ARCHIVED+DELETED: $base — ${result#OK }"
    else
      log "WARN archivé mais rm échoué: $base"
    fi
  else
    failed=$((failed+1))
    log "FAIL archive Notion (conservé): $base — $result"
  fi
done < <(find "$SESSIONS_DIR" -maxdepth 1 -type f -name '*.md' | sort)

summary="candidats=$candidates archivés=$archived supprimés=$deleted échecs=$failed"
log "=== run end : $summary ==="
echo "$summary"

# Notification seulement si quelque chose s'est passé ou a échoué
if [[ $DRY_RUN -eq 0 && ( $deleted -gt 0 || $failed -gt 0 ) ]]; then
  NOTIFY="$HOME/.local/bin/jarvis-notify"
  if [[ -x "$NOTIFY" ]]; then
    if [[ $failed -gt 0 ]]; then
      "$NOTIFY" "🧹 Purge sessions : $deleted archivées+supprimées, ⚠️ $failed échecs Notion (conservées). Voir log." --silent 2>/dev/null || true
    else
      "$NOTIFY" "🧹 Purge sessions : $deleted sessions >90j archivées dans Notion puis supprimées du vault." --silent 2>/dev/null || true
    fi
  fi
fi

exit 0
