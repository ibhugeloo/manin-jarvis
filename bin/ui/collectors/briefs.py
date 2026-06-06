"""
collectors/briefs.py — Collecteurs briefs et sessions.

Extrait de jarvis-ui-server.py (Phase 3 refacto MOS-004, 2026-05-09).
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ui.config import BRIEF_DIR, SESSIONS_DIR, HOME


# ---------------------------------------------------------------------------
# Preview helper
# ---------------------------------------------------------------------------

def _preview(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    try:
        text = path.read_text()
        return text[:8000]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def collect_briefs() -> dict:
    """Liste le brief du jour et les derniers hebdo/mensuel/evaluation."""
    today = datetime.now().strftime("%Y-%m-%d")
    out = {}

    jour = BRIEF_DIR / f"{today}.md"
    out["jour"] = {
        "exists": jour.exists(),
        "path": str(jour),
        "modified": jour.stat().st_mtime if jour.exists() else None,
        "preview": _preview(jour),
    }

    inbox = BRIEF_DIR / "Inbox.md"
    out["inbox"] = {
        "exists": inbox.exists(),
        "path": str(inbox),
        "modified": inbox.stat().st_mtime if inbox.exists() else None,
        "preview": _preview(inbox),
    }

    if BRIEF_DIR.exists():
        hebdos = sorted(BRIEF_DIR.glob("*-hebdo.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        mensuels = sorted(BRIEF_DIR.glob("*-mensuel.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        evals = sorted(BRIEF_DIR.glob("*-evaluation.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        out["hebdo"] = {
            "exists": bool(hebdos),
            "path": str(hebdos[0]) if hebdos else None,
            "name": hebdos[0].name if hebdos else None,
            "preview": _preview(hebdos[0]) if hebdos else None,
        }
        out["mensuel"] = {
            "exists": bool(mensuels),
            "path": str(mensuels[0]) if mensuels else None,
            "name": mensuels[0].name if mensuels else None,
            "preview": _preview(mensuels[0]) if mensuels else None,
        }
        out["evaluation"] = {
            "exists": bool(evals),
            "path": str(evals[0]) if evals else None,
            "name": evals[0].name if evals else None,
            "preview": _preview(evals[0]) if evals else None,
        }
    else:
        out["hebdo"] = out["mensuel"] = out["evaluation"] = {"exists": False}

    return out


def collect_sessions(limit: int = 5) -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    files = sorted(SESSIONS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out = []
    for f in files:
        try:
            text = f.read_text()
        except Exception:
            continue
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else f.stem
        date_match = re.search(r"^date:\s*(.+)$", text, re.MULTILINE)
        date = date_match.group(1).strip() if date_match else "?"
        proj_match = re.search(r"^projet:\s*(.+)$", text, re.MULTILINE)
        projet = proj_match.group(1).strip() if proj_match else "?"
        done_match = re.search(r"##\s*Ce qui a été fait\n((?:- .+\n?)+)", text)
        done = []
        if done_match:
            for line in done_match.group(1).splitlines():
                if line.strip().startswith("- "):
                    done.append(line.strip()[2:].strip())
        out.append({
            "name": f.name,
            "title": title,
            "date": date,
            "projet": Path(projet).name if projet != "?" else "?",
            "done": done[:3],
        })
    return out


