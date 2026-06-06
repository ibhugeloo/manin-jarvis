"""
collectors/watchtower.py — Collecteur état Watchtower (santé prod clients).

Extrait de jarvis-ui-server.py (Phase 3 refacto MOS-004, 2026-05-09).
"""
from __future__ import annotations

import sys
from pathlib import Path

from ui.config import VAULT, JARVIS_SRC, _record_diag


WATCHTOWER_DIR = VAULT / "Watchtower"
WATCHTOWER_CONFIG = JARVIS_SRC / "config" / "watchtower-projects.yaml"

_WT_STATUS_BY_EMOJI = {"🟢": "green", "🟡": "yellow", "🔴": "red"}


def _watchtower_load_projects() -> list[dict]:
    """Charge la liste des projets surveillés depuis le yaml."""
    if not WATCHTOWER_CONFIG.exists():
        _record_diag(
            "watchtower_yaml",
            loaded=False,
            error=f"file not found: {WATCHTOWER_CONFIG}",
            path=str(WATCHTOWER_CONFIG),
            projects_count=0,
        )
        print(f"[cfg] watchtower-projects.yaml introuvable : {WATCHTOWER_CONFIG}", file=sys.stderr, flush=True)
        return []
    try:
        import yaml
        cfg = yaml.safe_load(WATCHTOWER_CONFIG.read_text())
        projects = cfg.get("projects") or []
        _record_diag(
            "watchtower_yaml",
            loaded=True,
            error=None,
            path=str(WATCHTOWER_CONFIG),
            projects_count=len(projects),
        )
        return projects
    except Exception as e:
        _record_diag(
            "watchtower_yaml",
            loaded=False,
            error=f"{type(e).__name__}: {e}",
            path=str(WATCHTOWER_CONFIG),
            projects_count=0,
        )
        print(f"[cfg] watchtower-projects.yaml ÉCHEC : {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return []


def _watchtower_latest_report_dir() -> Path | None:
    """Retourne le dossier <date> le plus récent contenant un summary.md."""
    if not WATCHTOWER_DIR.exists():
        return None
    candidates = [
        d for d in WATCHTOWER_DIR.iterdir()
        if d.is_dir() and (d / "summary.md").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.name)


def _watchtower_parse_summary(summary_path: Path) -> dict:
    """Extrait les rows du tableau status global du summary.md."""
    out: dict[str, dict] = {}
    if not summary_path.exists():
        return out

    in_table = False
    try:
        for raw_line in summary_path.read_text().splitlines():
            line = raw_line.strip()
            if line.startswith("| Projet") or line.startswith("|Projet"):
                in_table = True
                continue
            if in_table and line.startswith("|---"):
                continue
            if in_table:
                if not line.startswith("|"):
                    in_table = False
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) < 4:
                    continue
                slug, _client, status_cell, alerts = cells[0], cells[1], cells[2], cells[3]
                status = "green"
                for emoji, code in _WT_STATUS_BY_EMOJI.items():
                    if emoji in status_cell:
                        status = code
                        break
                out[slug] = {"status": status, "alerts": alerts}
    except Exception:
        return {}
    return out


def collect_watchtower() -> dict:
    """État Watchtower du dernier rapport disponible."""
    projects_cfg = _watchtower_load_projects()
    latest = _watchtower_latest_report_dir()

    out: dict = {
        "exists": False,
        "report_date": None,
        "summary_path": None,
        "detail_path": None,
        "modified": None,
        "global_status": "unknown",
        "projects": [],
    }

    parsed: dict[str, dict] = {}
    if latest is not None:
        summary_p = latest / "summary.md"
        detail_p = latest / "detail.md"
        out["exists"] = True
        out["report_date"] = latest.name
        out["summary_path"] = str(summary_p)
        out["detail_path"] = str(detail_p) if detail_p.exists() else None
        out["modified"] = summary_p.stat().st_mtime if summary_p.exists() else None
        parsed = _watchtower_parse_summary(summary_p)

    severity = {"red": 3, "yellow": 2, "green": 1, "unknown": 0}
    max_sev = 0

    for p in projects_cfg:
        slug = p.get("slug", "")
        match = parsed.get(slug, {})
        status = match.get("status", "unknown")
        alerts = match.get("alerts", "")
        sev = severity.get(status, 0)
        if sev > max_sev:
            max_sev = sev
        out["projects"].append({
            "slug": slug,
            "client": p.get("client", ""),
            "name": p.get("name", slug),
            "status": status,
            "alerts": alerts,
            "repo": p.get("repo", ""),
            "obsidian_note": p.get("obsidian_note", ""),
            "deployed_at": p.get("deployed_at", ""),
            "description": (p.get("description") or "").strip(),
        })

    inv = {v: k for k, v in severity.items()}
    out["global_status"] = inv.get(max_sev, "unknown")
    return out
