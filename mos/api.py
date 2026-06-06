"""MOS — FastAPI daemon (127.0.0.1:3737).

Endpoints :
  GET  /health
  GET  /missions[?status=open|wip|blocked|done|dropped]
  GET  /missions/{id}
  GET  /events/recent[?limit=N]
  POST /events                 (body: {hook, tool?, session_id?, cwd?, payload?})
  POST /sync                   (force resync filesystem→DB ; nécessite TCC)

Local-first, bind 127.0.0.1 uniquement. Pas d'auth (intra-localhost).

⚠️ TCC : sous launchd macOS, ce daemon n'a PAS accès à ~/Documents/GIT PROD/.
Le sync filesystem → DB doit être déclenché par le CLI (depuis le shell user,
qui hérite du Full Disk Access). Voir bin/jarvis-mos sync.
Le daemon expose /sync mais ce dernier ne fonctionnera que si le user-process
appelant a déjà été autorisé pour le dossier ; sinon utiliser le CLI.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import db as mos_db
from . import missions_md

LOG = logging.getLogger("mos")

# DB connection partagée (sqlite WAL + check_same_thread=False)
_db = None


def get_db():
    global _db
    if _db is None:
        _db = mos_db.connect()
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pas de sync auto au boot — TCC bloque l'accès à ~/Documents/ depuis launchd.
    # Le sync est piloté par le CLI utilisateur ou par un hook de fichier.
    get_db()  # warm-up DB connection
    yield


app = FastAPI(title="Jarvis MOS", version="0.1.0", lifespan=lifespan)


class EventIn(BaseModel):
    hook: str = Field(..., description="SessionStart | UserPromptSubmit | PreToolUse | ...")
    tool: str | None = None
    session_id: str | None = None
    cwd: str | None = None
    payload: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    db = get_db()
    n_missions = db.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    n_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"ok": True, "missions": n_missions, "events": n_events}


@app.get("/missions")
def get_missions(
    status: str | None = Query(None, pattern="^(open|wip|blocked|done|dropped)$"),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    rows = mos_db.list_missions(get_db(), status=status, limit=limit)
    return {"count": len(rows), "missions": rows}


@app.get("/missions/{mission_id}")
def get_mission_by_id(mission_id: str) -> dict[str, Any]:
    m = mos_db.get_mission(get_db(), mission_id)
    if not m:
        raise HTTPException(404, f"mission {mission_id} not found")
    return m


@app.get("/events/recent")
def get_events_recent(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    rows = mos_db.recent_events(get_db(), limit=limit)
    return {"count": len(rows), "events": rows}


@app.post("/events")
def post_event(ev: EventIn) -> dict[str, Any]:
    new_id = mos_db.insert_event(
        get_db(),
        hook=ev.hook,
        tool=ev.tool,
        session_id=ev.session_id,
        cwd=ev.cwd,
        payload=ev.payload,
    )
    return {"id": new_id, "ok": True}


@app.post("/sync")
def post_sync() -> dict[str, Any]:
    """Sync filesystem → DB. Échoue silencieusement si TCC bloque l'accès.

    Préférer le CLI `jarvis-mos sync` qui s'exécute dans le contexte user.
    """
    stats = missions_md.sync_all(get_db())
    return stats
