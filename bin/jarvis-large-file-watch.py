#!/usr/bin/env python3
"""jarvis-large-file-watch.py — logique du PostToolUse hook.

Invoqué par jarvis-large-file-watch.sh avec, sur stdin, le payload JSON
du hook Claude Code.

Émet sur stdout un JSON `hookSpecificOutput` quand un fichier dans
~/Documents/GIT PROD/ dépasse le seuil de lignes — pour nudger l'invocation
du subagent `refactor-cleaner`. Sinon ne sort rien.

Exit code : toujours 0 (un hook ne doit jamais bloquer l'écriture).
"""

from __future__ import annotations
import hashlib
import json
import os
import pathlib
import sys
import time

THRESHOLD = int(os.environ.get("JARVIS_REFACTOR_THRESHOLD", "1500"))
COOLDOWN = int(os.environ.get("JARVIS_REFACTOR_COOLDOWN", "1800"))
HOME = pathlib.Path(os.environ["HOME"])
GIT_PROD = HOME / "Documents" / "GIT PROD"
FLAGS_DIR = HOME / ".local" / "var" / "jarvis-large-files"
LOG_PATH = HOME / ".local" / "var" / "log" / "jarvis-large-file-watch.log"

SKIP_EXT = {
    ".json", ".lock", ".svg", ".css", ".scss", ".html", ".md", ".txt", ".log",
    ".yaml", ".yml", ".toml", ".csv", ".xml", ".min.js", ".map",
}
SKIP_PARTS = {
    "node_modules", ".next", "dist", "build", ".git", "venv", "__pycache__",
    "coverage", ".turbo", ".vercel", "out",
}


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def main() -> int:
    if os.environ.get("JARVIS_REFACTOR_BYPASS") == "1":
        return 0

    raw = sys.stdin.read() or "{}"
    try:
        payload = json.loads(raw)
    except Exception as e:
        log(f"bad json stdin ({e}): {raw[:200]!r}")
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0

    fp = pathlib.Path(file_path)
    if not fp.is_file():
        return 0

    try:
        fp_resolved = fp.resolve()
        fp_resolved.relative_to(GIT_PROD.resolve())
    except Exception:
        return 0

    if fp.suffix.lower() in SKIP_EXT:
        return 0
    if any(part in SKIP_PARTS for part in fp.parts):
        return 0

    try:
        with fp.open("rb") as f:
            lines = sum(1 for _ in f)
    except Exception as e:
        log(f"read error {fp}: {e}")
        return 0

    if lines < THRESHOLD:
        return 0

    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(str(fp_resolved).encode()).hexdigest()
    flag = FLAGS_DIR / f"{key}.flag"
    now = int(time.time())
    if flag.exists():
        try:
            last = int(flag.read_text().strip() or "0")
        except Exception:
            last = 0
        if now - last < COOLDOWN:
            return 0
    try:
        flag.write_text(str(now))
    except Exception:
        pass

    try:
        rel = fp_resolved.relative_to(GIT_PROD.resolve())
    except Exception:
        rel = fp

    msg = (
        f"🧹 Large file watch — `{rel}` est à {lines} lignes (seuil {THRESHOLD}).\n"
        f"Le subagent `refactor-cleaner` est tout indiqué : il listera le code mort, "
        f"les duplications et proposera une découpe en modules. "
        f"Si la taille est volontaire ou si vous êtes en train de tailler ce fichier "
        f"à l'instant, ignorez ce nudge — prochain rappel sur ce fichier dans "
        f"{COOLDOWN // 60} min."
    )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out))
    log(f"nudge {rel} ({lines} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
