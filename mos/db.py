"""MOS — DB layer (SQLite + sqlite-vec).

Source de vérité MISSIONS = filesystem markdown.
DB = miroir reconstructible.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import sqlite_vec  # type: ignore

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "jarvis" / "mos.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
EMBED_DIM = 384  # multilingual-e5-small (aligné avec vault-search-v2)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with sqlite-vec loaded and schema applied."""
    db_path = Path(db_path)
    _ensure_parent(db_path)
    db = sqlite3.connect(str(db_path), isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    _apply_schema(db)
    _ensure_vec_tables(db)
    return db


def _apply_schema(db: sqlite3.Connection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    db.executescript(sql)


def _ensure_vec_tables(db: sqlite3.Connection) -> None:
    # vec0 virtual tables — créées hors schema.sql car CREATE VIRTUAL nécessite extension chargée
    db.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_missions USING vec0(embedding float[{EMBED_DIM}])"
    )
    db.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_patterns USING vec0(embedding float[{EMBED_DIM}])"
    )


# =========================================================================
# events
# =========================================================================
def insert_event(
    db: sqlite3.Connection,
    *,
    hook: str,
    tool: str | None = None,
    session_id: str | None = None,
    cwd: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    cur = db.execute(
        "INSERT INTO events (hook, tool, session_id, cwd, payload) VALUES (?,?,?,?,?)",
        (
            hook,
            tool,
            session_id,
            cwd,
            json.dumps(payload, ensure_ascii=False) if payload is not None else None,
        ),
    )
    return int(cur.lastrowid or 0)


def prune_events(db: sqlite3.Connection, keep_days: int = 90) -> dict[str, Any]:
    """Delete events older than `keep_days`. Returns counts before/after."""
    before = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    cur = db.execute(
        "DELETE FROM events WHERE ts < datetime('now', ?)",
        (f"-{int(keep_days)} days",),
    )
    deleted = cur.rowcount or 0
    db.execute("VACUUM")
    after = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"before": before, "deleted": deleted, "after": after, "kept_days": keep_days}


def recent_events(db: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT id, ts, hook, tool, session_id, cwd, payload FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_event_row(r) for r in rows]


def _event_row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    if d.get("payload"):
        try:
            d["payload"] = json.loads(d["payload"])
        except json.JSONDecodeError:
            pass
    return d


# =========================================================================
# missions (DB-side; markdown reste source de vérité)
# =========================================================================
def upsert_mission(db: sqlite3.Connection, m: dict[str, Any]) -> None:
    """Insert or update a mission row from a parsed markdown file."""
    db.execute(
        """
        INSERT INTO missions
            (id, title, status, opened_at, closed_at, deadline, parent_dream,
             deliverable, tags, body, file_path, file_mtime, synced_at)
        VALUES
            (:id, :title, :status, :opened_at, :closed_at, :deadline, :parent_dream,
             :deliverable, :tags, :body, :file_path, :file_mtime,
             strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        ON CONFLICT(id) DO UPDATE SET
            title         = excluded.title,
            status        = excluded.status,
            opened_at     = excluded.opened_at,
            closed_at     = excluded.closed_at,
            deadline      = excluded.deadline,
            parent_dream  = excluded.parent_dream,
            deliverable   = excluded.deliverable,
            tags          = excluded.tags,
            body          = excluded.body,
            file_path     = excluded.file_path,
            file_mtime    = excluded.file_mtime,
            synced_at     = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        {
            "id": m["id"],
            "title": m["title"],
            "status": m["status"],
            "opened_at": m["opened_at"],
            "closed_at": m.get("closed_at"),
            "deadline": m.get("deadline"),
            "parent_dream": m.get("parent_dream"),
            "deliverable": m.get("deliverable"),
            "tags": json.dumps(m.get("tags") or [], ensure_ascii=False),
            "body": m.get("body", ""),
            "file_path": m["file_path"],
            "file_mtime": m["file_mtime"],
        },
    )


def list_missions(
    db: sqlite3.Connection,
    *,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if status:
        rows = db.execute(
            "SELECT * FROM missions WHERE status = ? ORDER BY opened_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM missions ORDER BY opened_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_mission_row(r) for r in rows]


def get_mission(db: sqlite3.Connection, mission_id: str) -> dict[str, Any] | None:
    r = db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
    return _mission_row(r) if r else None


def _mission_row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    if d.get("tags"):
        try:
            d["tags"] = json.loads(d["tags"])
        except json.JSONDecodeError:
            d["tags"] = []
    return d


def delete_missing_missions(db: sqlite3.Connection, present_ids: Iterable[str]) -> int:
    """Remove DB rows whose mission file no longer exists on disk."""
    present = list(present_ids)
    placeholders = ",".join("?" for _ in present) or "''"
    cur = db.execute(
        f"DELETE FROM missions WHERE id NOT IN ({placeholders})",
        present,
    )
    return cur.rowcount or 0
