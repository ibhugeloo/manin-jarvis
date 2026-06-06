"""
collectors/agents.py — Collecteurs subagents Claude Code + topologie.

Extrait de jarvis-ui-server.py (Phase 3 refacto MOS-004, 2026-05-09).
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from ui.config import (
    CLAUDE_AGENTS_DIR,
    CLAUDE_PROJECTS_DIR,
    CLAUDE_PLUGINS_DIR,
    CLAUDE_SETTINGS_FILE,
    ACTIVE_SESSIONS_FILE,
    GIT_PROD_DIR,
    GIT_PROD_EXCLUDE,
    BUILTIN_AGENTS,
)


# ---------------------------------------------------------------------------
# Helpers markdown
# ---------------------------------------------------------------------------

def _read_md_meta(path: Path) -> dict:
    """Extrait nom + description + 1ere ligne H1 d'un fichier markdown frontmatter."""
    out = {"name": path.stem, "description": "", "title": ""}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm = text[3:end]
            for line in fm.splitlines():
                line = line.strip()
                if line.startswith("name:"):
                    out["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    out["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            text = text[end + 4:]
    for line in text.splitlines():
        if line.startswith("# "):
            out["title"] = line[2:].strip()
            break
    return out


def _truncate_agent_desc(desc: str, limit: int = 240) -> str:
    """Tronque une description d'agent : enlève les <example> XML puis cap à limit chars."""
    if "<example>" in desc.lower():
        desc = desc.split("<example>")[0].strip()
    if len(desc) > limit:
        desc = desc[: limit - 3].rstrip() + "…"
    return desc


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

SUBAGENT_ROLE_MAP: dict[str, str] = {
    "architect": "analyst",
    "backend": "builder",
    "chief-of-staff": "orchestrator",
    "code-reviewer": "critic",
    "database-reviewer": "critic",
    "doc-updater": "tools",
    "nextjs-frontend-dev": "builder",
    "refactor-cleaner": "tools",
    "security-reviewer": "critic",
    "feature-builder": "builder",
    "supabase-migrator": "tools",
    "jarvis-internals": "tools",
    "Explore": "researcher",
    "explore": "researcher",
    "general-purpose": "researcher",
    "Plan": "analyst",
    "statusline-setup": "tools",
}


def _guess_role(name: str) -> str:
    if name in SUBAGENT_ROLE_MAP:
        return SUBAGENT_ROLE_MAP[name]
    n = name.lower()
    if any(k in n for k in ("review", "critic", "audit", "security")):
        return "critic"
    if any(k in n for k in ("design", "ui", "ux", "frontend", "backend", "mobile", "build")):
        return "builder"
    if any(k in n for k in ("plan", "architect", "tdd", "research", "explore")):
        return "analyst"
    if any(k in n for k in ("doc", "config", "refactor", "tool", "setup")):
        return "tools"
    if any(k in n for k in ("orchestr", "main", "chief")):
        return "orchestrator"
    return "tools"


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def _parse_unresolved_subagents(transcript: Path) -> tuple[set[str], dict[str, float]]:
    """Parse un transcript JSONL Claude Code."""
    pending: dict[str, str] = {}
    last_seen: dict[str, float] = {}
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                ts_epoch = None
                ts_str = entry.get("timestamp")
                if isinstance(ts_str, str):
                    try:
                        ts_epoch = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        ts_epoch = None
                msg = entry.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "tool_use" and block.get("name") in ("Task", "Agent"):
                        tid = block.get("id")
                        sub = (block.get("input") or {}).get("subagent_type")
                        if tid and sub:
                            pending[tid] = sub
                            if ts_epoch is not None:
                                prev = last_seen.get(sub, 0)
                                if ts_epoch > prev:
                                    last_seen[sub] = ts_epoch
                    elif btype == "tool_result":
                        tid = block.get("tool_use_id")
                        if tid and tid in pending:
                            del pending[tid]
    except Exception:
        return set(), {}
    return set(pending.values()), last_seen


def _detect_active_subagents() -> tuple[set[str], dict[str, dict]]:
    """Croise active-sessions.json avec les transcripts Claude Code."""
    running: set[str] = set()
    by_session: dict[str, list[dict]] = {}
    if not ACTIVE_SESSIONS_FILE.exists():
        return running, by_session
    try:
        raw = json.loads(ACTIVE_SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return running, by_session
    if isinstance(raw, dict):
        sessions = raw.get("sessions") or []
    elif isinstance(raw, list):
        sessions = raw
    else:
        return running, by_session
    for sess in sessions:
        if not isinstance(sess, dict):
            continue
        sid = sess.get("session_id") or sess.get("sessionId")
        cwd = sess.get("cwd") or ""
        if not sid:
            continue
        key = cwd.replace("/", "-")
        candidate = CLAUDE_PROJECTS_DIR / key / f"{sid}.jsonl"
        if not candidate.exists():
            matches = list(CLAUDE_PROJECTS_DIR.glob(f"*/{sid}.jsonl")) if CLAUDE_PROJECTS_DIR.exists() else []
            if not matches:
                continue
            candidate = matches[0]
        unresolved, _ = _parse_unresolved_subagents(candidate)
        for sub in unresolved:
            running.add(sub)
            by_session.setdefault(sub, []).append({"session_id": sid, "cwd": cwd})
    return running, by_session


def _last_used_subagents(window_days: int = 7) -> dict[str, float]:
    """Dernier usage epoch par subagent sur les N derniers jours."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return {}
    cutoff = time.time() - window_days * 86400
    last: dict[str, float] = {}
    try:
        for jsonl in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
            try:
                if jsonl.stat().st_mtime < cutoff:
                    continue
            except Exception:
                continue
            _, seen = _parse_unresolved_subagents(jsonl)
            for sub, ts in seen.items():
                if ts > last.get(sub, 0):
                    last[sub] = ts
    except Exception:
        pass
    return last


def _collect_invocations(window_days: int = 30) -> dict:
    """Parcourt tous les transcripts récents et compte les invocations de subagents."""
    by_sub: dict[str, dict] = {}
    co_occ: dict[tuple, int] = {}
    total = 0
    if not CLAUDE_PROJECTS_DIR.exists():
        return {"by_subagent": by_sub, "co_occurrence": co_occ, "total_invocations": 0}
    cutoff = time.time() - window_days * 86400
    try:
        for jsonl in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
            try:
                if jsonl.stat().st_mtime < cutoff:
                    continue
            except Exception:
                continue
            session_subs: set[str] = set()
            try:
                with jsonl.open("r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue
                        ts_epoch = None
                        ts_str = entry.get("timestamp")
                        if isinstance(ts_str, str):
                            try:
                                ts_epoch = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                            except Exception:
                                ts_epoch = None
                        msg = entry.get("message") or {}
                        content = msg.get("content")
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") == "tool_use" and block.get("name") in ("Task", "Agent"):
                                sub = (block.get("input") or {}).get("subagent_type")
                                if not sub:
                                    continue
                                session_subs.add(sub)
                                total += 1
                                slot = by_sub.setdefault(sub, {"count": 0, "last_ts": 0.0, "sessions": set()})
                                slot["count"] += 1
                                slot["sessions"].add(jsonl.stem)
                                if ts_epoch and ts_epoch > slot["last_ts"]:
                                    slot["last_ts"] = ts_epoch
            except Exception:
                continue
            ordered = sorted(session_subs)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    key = (a, b)
                    co_occ[key] = co_occ.get(key, 0) + 1
    except Exception:
        pass
    return {"by_subagent": by_sub, "co_occurrence": co_occ, "total_invocations": total}


# ---------------------------------------------------------------------------
# Project / plugin agents
# ---------------------------------------------------------------------------

def _project_agents_dirs() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    if not GIT_PROD_DIR.exists():
        return out
    try:
        for entry in GIT_PROD_DIR.iterdir():
            if not entry.is_dir() or entry.name in GIT_PROD_EXCLUDE:
                continue
            direct = entry / ".claude" / "agents"
            if direct.is_dir():
                out.append((entry.name, direct))
                continue
            for sub in entry.iterdir():
                if not sub.is_dir() or sub.name in GIT_PROD_EXCLUDE:
                    continue
                nested = sub / ".claude" / "agents"
                if nested.is_dir():
                    out.append((f"{entry.name}/{sub.name}", nested))
    except Exception:
        pass
    return out


def _collect_project_agents() -> list[dict]:
    out: list[dict] = []
    for proj_name, agents_dir in _project_agents_dirs():
        for md in sorted(agents_dir.glob("*.md")):
            if md.stem.lower() in ("agents", "readme", "_index"):
                continue
            meta = _read_md_meta(md)
            name = meta.get("name") or md.stem
            desc = _truncate_agent_desc(meta.get("description") or "", limit=240)
            out.append({
                "name": name,
                "file": md.name,
                "description": desc,
                "role": _guess_role(name),
                "model": meta.get("model"),
                "tools": meta.get("tools"),
                "source_project": proj_name,
                "project_path": str(md),
            })
    return out


def _enabled_plugin_paths() -> list[tuple[str, Path]]:
    if not CLAUDE_SETTINGS_FILE.exists() or not CLAUDE_PLUGINS_DIR.exists():
        return []
    try:
        settings = json.loads(CLAUDE_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    enabled = settings.get("enabledPlugins") or {}
    out: list[tuple[str, Path]] = []
    for key, val in enabled.items():
        if not val:
            continue
        if "@" in key:
            plug_name, marketplace = key.split("@", 1)
        else:
            plug_name, marketplace = key, "claude-plugins-official"
        plug_dir = CLAUDE_PLUGINS_DIR / marketplace / "plugins" / plug_name
        if plug_dir.exists():
            out.append((plug_name, plug_dir))
    return out


def _collect_plugin_agents() -> list[dict]:
    out: list[dict] = []
    for plug_name, plug_dir in _enabled_plugin_paths():
        agents_dir = plug_dir / "agents"
        if not agents_dir.exists():
            continue
        for md in sorted(agents_dir.glob("*.md")):
            if md.stem.lower() in ("agents", "readme", "_index"):
                continue
            meta = _read_md_meta(md)
            name = meta.get("name") or md.stem
            desc = _truncate_agent_desc(meta.get("description") or "", limit=240)
            out.append({
                "name": name,
                "file": md.name,
                "description": desc,
                "role": _guess_role(name),
                "model": meta.get("model"),
                "tools": meta.get("tools"),
                "source_plugin": plug_name,
                "plugin_path": str(md),
            })
    return out


# ---------------------------------------------------------------------------
# Public collectors
# ---------------------------------------------------------------------------

def collect_subagents() -> dict:
    """Liste les subagents Claude Code (~/.claude/agents/*.md) + état d'activité."""
    if not CLAUDE_AGENTS_DIR.exists():
        return {"agents": [], "running_count": 0, "total": 0}
    running, by_session = _detect_active_subagents()
    last_used = _last_used_subagents()
    agents = []
    for md in sorted(CLAUDE_AGENTS_DIR.glob("*.md")):
        if md.stem.lower() in ("agents", "readme", "_index"):
            continue
        meta = _read_md_meta(md)
        desc = _truncate_agent_desc(meta.get("description") or "", limit=220)
        name = meta.get("name") or md.stem
        ts = last_used.get(name)
        last_iso = None
        if ts:
            try:
                last_iso = datetime.fromtimestamp(ts).isoformat(timespec="seconds")
            except Exception:
                last_iso = None
        agents.append({
            "name": name,
            "file": md.name,
            "description": desc,
            "running": name in running,
            "running_in": by_session.get(name, []),
            "last_used": last_iso,
            "last_used_ts": ts,
        })
    agents.sort(key=lambda a: (not a["running"], -(a["last_used_ts"] or 0), a["name"]))
    for a in agents:
        a.pop("last_used_ts", None)
    return {
        "agents": agents,
        "running_count": sum(1 for a in agents if a["running"]),
        "total": len(agents),
    }


def collect_agent_topology() -> dict:
    """Topologie spawn parent→child : main = orchestrateur racine, edges = invocations."""
    invo = _collect_invocations(window_days=30)
    by_sub = invo["by_subagent"]
    co_occ = invo["co_occurrence"]
    running, _by_session = _detect_active_subagents()

    nodes: list[dict] = []
    main_count = sum(slot["count"] for slot in by_sub.values())
    nodes.append({
        "id": "main",
        "name": "main",
        "role": "orchestrator",
        "description": "Session Claude Code utilisateur — point de spawn racine.",
        "running": False,
        "last_used_ts": max((s["last_ts"] for s in by_sub.values()), default=0) or None,
        "invocation_count": main_count,
        "source": "session",
        "is_root": True,
    })
    # 1) Local agents (~/.claude/agents/)
    if CLAUDE_AGENTS_DIR.exists():
        for md in sorted(CLAUDE_AGENTS_DIR.glob("*.md")):
            if md.stem.lower() in ("agents", "readme", "_index"):
                continue
            meta = _read_md_meta(md)
            name = meta.get("name") or md.stem
            desc = _truncate_agent_desc(meta.get("description") or "", limit=240)
            slot = by_sub.get(name, {"count": 0, "last_ts": 0.0})
            nodes.append({
                "id": name,
                "name": name,
                "role": _guess_role(name),
                "description": desc,
                "running": name in running,
                "last_used_ts": slot["last_ts"] or None,
                "invocation_count": slot["count"],
                "tools": meta.get("tools"),
                "model": meta.get("model"),
                "file": md.name,
                "source": "local",
                "source_plugin": None,
                "is_root": False,
            })
    # 2) Project agents
    known = {n["id"] for n in nodes}
    for proj_agent in _collect_project_agents():
        name = proj_agent["name"]
        if name in known:
            continue
        slot = by_sub.get(name, {"count": 0, "last_ts": 0.0})
        nodes.append({
            "id": name,
            "name": name,
            "role": proj_agent["role"],
            "description": proj_agent["description"],
            "running": name in running,
            "last_used_ts": slot["last_ts"] or None,
            "invocation_count": slot["count"],
            "tools": proj_agent["tools"],
            "model": proj_agent["model"],
            "file": proj_agent["file"],
            "source": "project",
            "source_project": proj_agent["source_project"],
            "source_plugin": None,
            "is_root": False,
        })
        known.add(name)
    # 3) Plugin agents
    for plug_agent in _collect_plugin_agents():
        name = plug_agent["name"]
        if name in known:
            continue
        slot = by_sub.get(name, {"count": 0, "last_ts": 0.0})
        nodes.append({
            "id": name,
            "name": name,
            "role": plug_agent["role"],
            "description": plug_agent["description"],
            "running": name in running,
            "last_used_ts": slot["last_ts"] or None,
            "invocation_count": slot["count"],
            "tools": plug_agent["tools"],
            "model": plug_agent["model"],
            "file": plug_agent["file"],
            "source": "plugin",
            "source_plugin": plug_agent["source_plugin"],
            "is_root": False,
        })
        known.add(name)
    # 4) Builtins
    for bname, binfo in BUILTIN_AGENTS.items():
        if bname in known:
            continue
        slot = by_sub.get(bname, {"count": 0, "last_ts": 0.0})
        nodes.append({
            "id": bname,
            "name": bname,
            "role": binfo["role"],
            "description": binfo["description"],
            "running": bname in running,
            "last_used_ts": slot["last_ts"] or None,
            "invocation_count": slot["count"],
            "tools": None,
            "model": binfo.get("model"),
            "file": None,
            "source": "builtin",
            "source_plugin": None,
            "is_root": False,
        })
        known.add(bname)
    # 5) Safety net: invoked but unknown
    for sub_name, slot in by_sub.items():
        if sub_name in known:
            continue
        nodes.append({
            "id": sub_name,
            "name": sub_name,
            "role": _guess_role(sub_name),
            "description": "Subagent invoqué sans définition locale connue.",
            "running": sub_name in running,
            "last_used_ts": slot["last_ts"] or None,
            "invocation_count": slot["count"],
            "tools": None,
            "model": None,
            "file": None,
            "source": "unknown",
            "source_plugin": None,
            "is_root": False,
        })

    edges: list[dict] = []
    for sub_name, slot in by_sub.items():
        if slot["count"] <= 0:
            continue
        edges.append({
            "source": "main",
            "target": sub_name,
            "kind": "spawn",
            "weight": slot["count"],
            "last_ts": slot["last_ts"] or None,
        })
    for (a, b), count in co_occ.items():
        edges.append({
            "source": a,
            "target": b,
            "kind": "sibling",
            "weight": count,
            "last_ts": None,
        })

    edge_count = {n["id"]: 0 for n in nodes}
    for e in edges:
        edge_count[e["source"]] = edge_count.get(e["source"], 0) + 1
        edge_count[e["target"]] = edge_count.get(e["target"], 0) + 1
    for n in nodes:
        n["edges"] = edge_count.get(n["id"], 0)
        ts = n.get("last_used_ts")
        n["last_used"] = (
            datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else None
        )

    nodes.sort(key=lambda n: (not n["is_root"], not n["running"], -(n.get("last_used_ts") or 0), n["name"]))

    by_source: dict[str, int] = {}
    for n in nodes:
        if n.get("is_root"):
            continue
        src = n.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "running_count": sum(1 for n in nodes if n["running"]),
            "total_invocations": invo["total_invocations"],
            "window_days": 30,
            "by_source": by_source,
            "enabled_plugins": [name for name, _ in _enabled_plugin_paths()],
        },
    }
