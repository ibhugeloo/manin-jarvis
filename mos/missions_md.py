"""MOS — bridge filesystem markdown ↔ SQLite.

Source de vérité = share/missions/*.md.
Cette couche reflète vers la DB sur appel `sync_all()` (idempotent).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml  # PyYAML, déjà dans le venv jarvis

from . import db as mos_db


def _default_missions_dir() -> Path:
    """Resolve the missions directory.

    Order of resolution:
      1. env var MOS_MISSIONS_DIR (absolute path)
      2. <repo>/share/missions if this module is loaded from the source repo
      3. ~/Documents/GIT PROD/manin-jarvis/share/missions (deployed default)
    """
    env = os.environ.get("MOS_MISSIONS_DIR")
    if env:
        return Path(env).expanduser()
    repo_local = Path(__file__).resolve().parent.parent / "share" / "missions"
    if repo_local.exists():
        return repo_local
    return Path.home() / "Documents" / "GIT PROD" / "manin-jarvis" / "share" / "missions"


MISSIONS_DIR = _default_missions_dir()

VALID_STATUSES = {"open", "wip", "blocked", "done", "dropped"}
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_mission_file(path: Path) -> dict[str, Any] | None:
    """Parse a single mission markdown file.

    Returns a dict suitable for `mos_db.upsert_mission`, or None if the file
    doesn't have valid frontmatter / required fields / is the _FORMAT.md template.
    """
    if path.name.startswith("_"):
        return None  # template/index files
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    front_raw, body = m.group(1), m.group(2)
    try:
        front = yaml.safe_load(front_raw) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(front, dict):
        return None

    mid = front.get("id")
    title = front.get("title")
    status = front.get("status")
    opened_at = front.get("opened_at")
    if not (mid and title and status and opened_at):
        return None
    if status not in VALID_STATUSES:
        return None
    if str(mid).startswith("TEMPLATE"):
        return None

    return {
        "id": str(mid),
        "title": str(title),
        "status": str(status),
        "opened_at": str(opened_at),
        "closed_at": _opt_str(front.get("closed_at")),
        "deadline": _opt_str(front.get("deadline")),
        "parent_dream": _opt_str(front.get("parent_dream")),
        "deliverable": _opt_str(front.get("deliverable")),
        "tags": front.get("tags") or [],
        "body": body.strip(),
        "file_path": str(path),
        "file_mtime": path.stat().st_mtime,
    }


def _opt_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def sync_all(db, missions_dir: Path = MISSIONS_DIR) -> dict[str, int]:
    """Scan all mission files and reflect them to DB.

    Returns counts: {scanned, upserted, removed}.
    """
    if not missions_dir.exists():
        return {"scanned": 0, "upserted": 0, "removed": 0}

    seen_ids: list[str] = []
    upserted = 0

    for path in sorted(missions_dir.glob("*.md")):
        parsed = parse_mission_file(path)
        if not parsed:
            continue
        mos_db.upsert_mission(db, parsed)
        seen_ids.append(parsed["id"])
        upserted += 1

    removed = mos_db.delete_missing_missions(db, seen_ids)
    return {"scanned": len(list(missions_dir.glob("*.md"))), "upserted": upserted, "removed": removed}
