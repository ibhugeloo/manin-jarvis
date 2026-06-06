#!/bin/zsh
# jarvis-coolify-autodeploy — déclenche un deploy Coolify quand un push GitHub
# atterrit sur la branche surveillée. Lancé par launchd toutes les 5 minutes.
#
# Pour chaque app de config/coolify-autodeploy.yaml :
#   1. git fetch origin <branch>
#   2. lit origin/<branch>
#   3. compare au SHA déployé persisté dans ~/.local/var/jarvis-coolify-deployed/<uuid>.sha
#   4. si différent : POST /api/v1/deploy?uuid=<uuid> à Coolify
#   5. si trigger OK : enregistre le nouveau SHA + notif Telegram
#
# Idempotent. Silencieux quand rien à faire. Tolère :
#   - Coolify injoignable (Twingate off, VM down) → log warn, exit 0
#   - git fetch raté (réseau, auth) → log warn, app suivante
#   - First run par app : initialise le state file avec le SHA courant, pas de deploy
#
# Logs : ~/.local/var/log/jarvis-coolify-autodeploy.log (rotatif manuel si besoin)

set -uo pipefail

JARVIS_SRC="$HOME/Documents/GIT PROD/manin-jarvis"
CONFIG_FILE="$JARVIS_SRC/config/coolify-autodeploy.yaml"
STATE_DIR="$HOME/.local/var/jarvis-coolify-deployed"
LOG="$HOME/.local/var/log/jarvis-coolify-autodeploy.log"
LOCK_FILE="$HOME/.local/var/jarvis-coolify-autodeploy.lock"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$STATE_DIR" "$(dirname "$LOG")"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

# Verrou pour éviter qu'un tick chevauche le précédent (deploy lent)
if [[ -f "$LOCK_FILE" ]]; then
  pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    log "lock détenu par PID $pid, skip"
    exit 0
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# Charge le token Coolify
SECRETS_ENV="$HOME/.config/jarvis/secrets/env"
if [[ ! -f "$SECRETS_ENV" ]]; then
  log "ERREUR: $SECRETS_ENV introuvable, abort"
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$SECRETS_ENV"
set +a

if [[ -z "${COOLIFY_API_TOKEN:-}" ]] || [[ -z "${COOLIFY_API_BASE:-}" ]]; then
  log "ERREUR: COOLIFY_API_TOKEN ou COOLIFY_API_BASE manquant dans $SECRETS_ENV"
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  log "ERREUR: config $CONFIG_FILE introuvable"
  exit 1
fi

# Vérifie que Coolify est joignable (sinon Twingate down → no-op)
if ! curl -s --max-time 5 -o /dev/null "$COOLIFY_API_BASE/../api/health" 2>/dev/null; then
  if ! curl -s --max-time 5 -o /dev/null "$(echo "$COOLIFY_API_BASE" | sed 's|/api/v1||')/api/health" 2>/dev/null; then
    log "Coolify injoignable (Twingate down ou VM down), skip ce tick"
    exit 0
  fi
fi

# Lit la liste des apps depuis le YAML via /usr/bin/python3 (qui a yaml)
APPS_JSON=$(/usr/bin/python3 - <<PYEOF
import yaml, json, os, sys
try:
    with open("$CONFIG_FILE") as f:
        cfg = yaml.safe_load(f) or {}
    apps = cfg.get("apps") or []
    for a in apps:
        a["path"] = os.path.expanduser(a.get("path", ""))
    print(json.dumps(apps))
except Exception as e:
    print(f"ERREUR YAML: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [[ -z "$APPS_JSON" ]] || [[ "$APPS_JSON" == "[]" ]]; then
  log "Aucune app configurée, exit"
  exit 0
fi

# Itère via /usr/bin/python3 qui pipe ligne par ligne (TSV : name uuid path branch fqdn)
echo "$APPS_JSON" | /usr/bin/python3 -c "
import sys, json
for a in json.load(sys.stdin):
    print('\t'.join([a.get(k,'') for k in ('name','uuid','path','branch','fqdn')]))
" | while IFS=$'\t' read -r name uuid app_path branch fqdn; do
  # NB: ne JAMAIS nommer une variable de boucle `path` en zsh — c'est un alias array de PATH.

  if [[ -z "$uuid" ]] || [[ -z "$app_path" ]]; then
    log "[$name] config incomplète (uuid ou path vide), skip"
    continue
  fi

  if [[ ! -d "$app_path/.git" ]]; then
    log "[$name] $app_path n'est pas un repo git, skip"
    continue
  fi

  branch="${branch:-main}"
  state_file="$STATE_DIR/$uuid.sha"

  # Fetch silencieux. Pas de timeout externe (pas dispo sur macOS de base) ; git a
  # ses propres timeouts via http.lowSpeedTime, et le lock protège des runs concurrents.
  if ! git -C "$app_path" fetch -q origin "$branch" 2>/dev/null; then
    log "[$name] git fetch origin $branch échoué, skip"
    continue
  fi

  remote_sha=$(git -C "$app_path" rev-parse "origin/$branch" 2>/dev/null)
  if [[ -z "$remote_sha" ]]; then
    log "[$name] impossible de lire origin/$branch, skip"
    continue
  fi

  # First run : enregistre le SHA et sort sans deploy
  if [[ ! -f "$state_file" ]]; then
    echo "$remote_sha" > "$state_file"
    log "[$name] init state file → $remote_sha (pas de deploy déclenché)"
    continue
  fi

  last_sha=$(cat "$state_file" 2>/dev/null)
  if [[ "$remote_sha" == "$last_sha" ]]; then
    # Pas de log à chaque tick "rien à faire" pour ne pas spammer le log.
    continue
  fi

  short_remote="${remote_sha:0:10}"
  short_last="${last_sha:0:10}"
  log "[$name] nouveau commit détecté ($short_last → $short_remote), trigger deploy…"

  # Trigger deploy
  trigger_response=$(curl -s --max-time 20 -w '\nHTTP_CODE:%{http_code}' \
    -X POST \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    "$COOLIFY_API_BASE/deploy?uuid=$uuid")
  code=$(echo "$trigger_response" | awk -F: '/^HTTP_CODE:/{print $2}')

  if [[ "$code" == "200" ]] || [[ "$code" == "201" ]] || [[ "$code" == "202" ]]; then
    echo "$remote_sha" > "$state_file"
    deploy_uuid=$(echo "$trigger_response" | /usr/bin/python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read().split('HTTP_CODE')[0])
    deps = data.get('deployments') or []
    print(deps[0].get('deployment_uuid','') if deps else '')
except Exception:
    print('')
")
    log "[$name] deploy queued (HTTP $code, deployment_uuid=$deploy_uuid)"
    # Notif Telegram (best-effort, ne bloque pas si script absent)
    if command -v jarvis-msg >/dev/null 2>&1; then
      jarvis-msg "🚀 Coolify deploy : *$name* → \`$short_remote\` ($fqdn)" >/dev/null 2>&1 || true
    fi
  else
    log "[$name] ÉCHEC trigger deploy (HTTP $code) — response: $(echo "$trigger_response" | head -3 | tr '\n' ' ')"
    if command -v jarvis-msg >/dev/null 2>&1; then
      jarvis-msg "❌ Coolify deploy *$name* a échoué (HTTP $code)" >/dev/null 2>&1 || true
    fi
  fi
done

exit 0
