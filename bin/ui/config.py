"""
ui/config.py — Constantes partagées entre tous les collectors.

Importé par collectors/*.py via `from ui.config import ...`.
"""
from __future__ import annotations

import time
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "Documents" / "Obsidian" / "vault"
BRIEF_DIR = VAULT / "Brief"
SESSIONS_DIR = VAULT / "Claude" / "Sessions"
JARVIS_SRC = HOME / "Documents" / "GIT PROD" / "manin-jarvis"
LOG_DIR = HOME / ".local" / "var" / "log"
LOCAL_BIN = HOME / ".local" / "bin"

GIT_PROD_DIR = HOME / "Documents" / "GIT PROD"
GIT_PROD_EXCLUDE: set[str] = {"archives"}

REPOS_CONFIG_PATH = JARVIS_SRC / "config" / "repos.yaml"
DOMAINS_CONFIG_PATH = JARVIS_SRC / "config" / "domains.yaml"

CLAUDE_AGENTS_DIR = HOME / ".claude" / "agents"
CLAUDE_PROJECTS_DIR = HOME / ".claude" / "projects"
CLAUDE_PLUGINS_DIR = HOME / ".claude" / "plugins" / "marketplaces"
CLAUDE_SETTINGS_FILE = HOME / ".claude" / "settings.json"
ACTIVE_SESSIONS_FILE = HOME / ".jarvis" / "active-sessions.json"

_SERVER_STARTED_TS = time.time()
_SERVER_STARTED_AT = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(_SERVER_STARTED_TS))

_CONFIG_DIAGNOSTICS: dict[str, dict] = {
    "repos_yaml": {"loaded": False, "error": None, "path": None, "categories": []},
    "watchtower_yaml": {"loaded": False, "error": None, "path": None, "projects_count": 0},
}


def _record_diag(key: str, **fields) -> None:
    diag = _CONFIG_DIAGNOSTICS.setdefault(key, {})
    diag.update(fields)


BUILTIN_AGENTS: dict[str, dict] = {
    "Explore": {
        "role": "researcher",
        "description": "Fast read-only search agent for locating code. Find files by pattern, grep for symbols or keywords, answer 'where is X defined' / 'which files reference Y'. Built into Claude Code.",
        "model": None,
    },
    "Plan": {
        "role": "analyst",
        "description": "Software architect agent for designing implementation plans. Returns step-by-step plans, identifies critical files, considers architectural trade-offs. Built into Claude Code.",
        "model": None,
    },
    "general-purpose": {
        "role": "researcher",
        "description": "General-purpose agent for researching complex questions, multi-step tasks, broad codebase searches. Built into Claude Code.",
        "model": None,
    },
}
