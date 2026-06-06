#!/usr/bin/env bash
# jarvis-large-file-watch.sh — wrapper bash pour le hook PostToolUse.
# Délègue toute la logique à jarvis-large-file-watch.py (parse JSON, cooldown,
# détection seuil, output additionalContext). Le hook ne bloque jamais.

set -uo pipefail

# Résoudre les symlinks (macOS BSD readlink n'a pas -f)
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
    target="$(readlink "$src")"
    case "$target" in
        /*) src="$target" ;;
        *)  src="$(dirname -- "$src")/$target" ;;
    esac
done
SCRIPT_DIR="$(cd -- "$(dirname -- "$src")" >/dev/null 2>&1 && pwd)"
PY_SCRIPT="$SCRIPT_DIR/jarvis-large-file-watch.py"

# Si le .py est manquant (cas exotique), on sort silencieusement
if [ ! -f "$PY_SCRIPT" ]; then
    exit 0
fi

# Lire stdin une fois pour pouvoir l'envoyer à la fois à MOS et au script Python.
INPUT=$(cat)

# MOS event (best-effort, fork & forget) — n'affecte pas le hook
if [ -x "$HOME/.local/bin/jarvis-mos-emit" ]; then
    TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    printf '%s' "$INPUT" | "$HOME/.local/bin/jarvis-mos-emit" PostToolUse "$TOOL_NAME" >/dev/null 2>&1 &
fi

# Auto-sync MOS missions si un fichier share/missions/*.md est touché
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
case "$FILE_PATH" in
    *"/share/missions/"*.md)
        if [ -x "$HOME/.local/bin/jarvis-mos" ]; then
            "$HOME/.local/bin/jarvis-mos" sync >/dev/null 2>&1 &
        fi
        ;;
esac

printf '%s' "$INPUT" | /usr/bin/env python3 "$PY_SCRIPT"
exit $?
