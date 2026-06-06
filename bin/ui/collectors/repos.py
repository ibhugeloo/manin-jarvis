"""
collectors/repos.py — Collecteurs repos GIT PROD + domaines + config yaml.

Extrait de jarvis-ui-server.py (Phase 3 refacto MOS-004, 2026-05-09).
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ui.config import (
    HOME,
    GIT_PROD_EXCLUDE,
    REPOS_CONFIG_PATH,
    DOMAINS_CONFIG_PATH,
    _record_diag,
)


# ---------------------------------------------------------------------------
# Helpers git
# ---------------------------------------------------------------------------

def _is_git_repo(path: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path), capture_output=True, text=True, timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Repos config (catégories, URLs, exclusions)
# ---------------------------------------------------------------------------

def _write_repos_yaml_preserve_header(text: str, cfg: dict) -> None:
    """Écrit cfg dans REPOS_CONFIG_PATH en préservant le header de commentaires (#)."""
    import yaml
    header_lines = []
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            header_lines.append(line)
        else:
            break
    header = "\n".join(header_lines).rstrip()
    body = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, default_flow_style=False)
    final = (header + "\n\n" + body) if header else body
    REPOS_CONFIG_PATH.write_text(final)


def load_repos_config() -> dict:
    """Charge la config catégories."""
    fallback = {"default": "perso", "categories": {}, "order": [], "urls": {}, "excluded": []}
    if not REPOS_CONFIG_PATH.exists():
        _record_diag(
            "repos_yaml",
            loaded=False,
            error=f"file not found: {REPOS_CONFIG_PATH}",
            path=str(REPOS_CONFIG_PATH),
            categories=[],
        )
        print(f"[cfg] repos.yaml introuvable : {REPOS_CONFIG_PATH}", file=sys.stderr, flush=True)
        return fallback
    try:
        import yaml
        cfg = yaml.safe_load(REPOS_CONFIG_PATH.read_text())
        order = list((cfg.get("categories") or {}).keys())
        result = {
            "default": cfg.get("default", "perso"),
            "categories": cfg.get("categories") or {},
            "order": order,
            "urls": cfg.get("urls") or {},
            "excluded": cfg.get("excluded") or [],
        }
        _record_diag(
            "repos_yaml",
            loaded=True,
            error=None,
            path=str(REPOS_CONFIG_PATH),
            categories=order,
        )
        return result
    except Exception as e:
        _record_diag(
            "repos_yaml",
            loaded=False,
            error=f"{type(e).__name__}: {e}",
            path=str(REPOS_CONFIG_PATH),
            categories=[],
        )
        print(f"[cfg] repos.yaml ÉCHEC chargement : {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return fallback


def repo_category(repo_name: str, config: dict) -> str:
    for cat, data in (config.get("categories") or {}).items():
        if repo_name in (data.get("repos") or []):
            return cat
    return config.get("default", "perso")


def category_label(cat: str, config: dict) -> str:
    return (config.get("categories", {}).get(cat) or {}).get("label", cat)


def repo_url(repo_name: str, config: dict) -> str:
    return (config.get("urls") or {}).get(repo_name, "") or ""


def update_repo_url(repo_name: str, new_url: str) -> dict:
    """Met à jour (ou supprime si vide) l'URL associée à un repo dans config/repos.yaml."""
    if not REPOS_CONFIG_PATH.exists():
        return {"ok": False, "error": "config absente"}
    try:
        import yaml
    except ImportError:
        return {"ok": False, "error": "PyYAML non disponible"}

    new_url = (new_url or "").strip()
    if new_url and not (new_url.startswith("http://") or new_url.startswith("https://")):
        new_url = "https://" + new_url

    text = REPOS_CONFIG_PATH.read_text()
    cfg = yaml.safe_load(text) or {}
    urls = dict(cfg.get("urls") or {})

    if new_url:
        urls[repo_name] = new_url
    else:
        urls.pop(repo_name, None)
    cfg["urls"] = urls

    _write_repos_yaml_preserve_header(text, cfg)
    return {"ok": True, "repo": repo_name, "url": new_url}


def update_repo_category(repo_name: str, new_category: str) -> dict:
    """Déplace un repo vers une autre catégorie dans config/repos.yaml."""
    if not REPOS_CONFIG_PATH.exists():
        return {"ok": False, "error": "config absente"}
    try:
        import yaml
    except ImportError:
        return {"ok": False, "error": "PyYAML non disponible"}

    text = REPOS_CONFIG_PATH.read_text()
    cfg = yaml.safe_load(text) or {}
    cats = cfg.get("categories") or {}
    if new_category not in cats:
        return {"ok": False, "error": f"catégorie inconnue: {new_category}"}

    moved = False
    for cat, data in cats.items():
        repos = list(data.get("repos") or [])
        if repo_name in repos:
            if cat == new_category:
                return {"ok": True, "noop": True, "repo": repo_name, "category": cat}
            repos.remove(repo_name)
            data["repos"] = repos
            moved = True

    target_repos = list(cats[new_category].get("repos") or [])
    if repo_name not in target_repos:
        target_repos.append(repo_name)
        cats[new_category]["repos"] = target_repos
    cfg["categories"] = cats

    _write_repos_yaml_preserve_header(text, cfg)
    return {"ok": True, "moved": moved, "repo": repo_name, "category": new_category}


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------

def collect_repos() -> list[dict]:
    out = []
    git_prod = HOME / "Documents" / "GIT PROD"
    if not git_prod.exists():
        return out

    cfg_excluded = set(load_repos_config().get("excluded") or [])

    repos: list[Path] = []
    for d in sorted(git_prod.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        if d.name in GIT_PROD_EXCLUDE:
            continue
        if d.name in cfg_excluded:
            continue
        if _is_git_repo(d):
            repos.append(d)
            continue
        # Wrapper case : chercher un repo imbriqué (cf. agency-app/agency-platform)
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and not sub.name.startswith('.') and _is_git_repo(sub):
                rel_name = f"{d.name}/{sub.name}"
                if rel_name in cfg_excluded:
                    continue
                repos.append(sub)

    for d in repos:
        try:
            rel = d.relative_to(git_prod)
            name = str(rel) if len(rel.parts) > 1 else rel.parts[0]
        except Exception:
            name = d.name

        def git(args, _d=d):
            try:
                return subprocess.run(
                    ["git"] + args, cwd=str(_d), capture_output=True, text=True, timeout=3
                ).stdout.strip()
            except Exception:
                return ""

        branch = git(["rev-parse", "--abbrev-ref", "HEAD"]) or "?"
        modified = len([l for l in git(["status", "--porcelain"]).splitlines() if l.strip()])
        try:
            ahead = len([l for l in git(["log", "@{u}..HEAD", "--oneline"]).splitlines() if l.strip()])
        except Exception:
            ahead = 0
        last_commit_iso = git(["log", "-1", "--format=%cI"])
        last_commit_rel = git(["log", "-1", "--format=%cr"])

        days_idle = None
        if last_commit_iso:
            try:
                iso = re.sub(r"[+-]\d{2}:\d{2}$", "", last_commit_iso)
                dt = datetime.fromisoformat(iso)
                days_idle = (datetime.now() - dt).days
            except Exception:
                pass

        status = "clean"
        if modified > 0 or ahead > 0:
            status = "dirty"
        if days_idle is not None and days_idle > 30:
            status = "stale"

        out.append({
            "name": name,
            "branch": branch,
            "modified": modified,
            "ahead": ahead,
            "last_commit": last_commit_rel,
            "days_idle": days_idle,
            "status": status,
        })

    cfg = load_repos_config()
    for r in out:
        r["category"] = repo_category(r["name"], cfg)
        r["category_label"] = category_label(r["category"], cfg)
        r["url"] = repo_url(r["name"], cfg)
    cat_order = {c: i for i, c in enumerate(cfg.get("order", []))}
    out.sort(key=lambda r: (cat_order.get(r["category"], 999), r["name"]))
    return out


# ---------------------------------------------------------------------------
# Domaines
# ---------------------------------------------------------------------------

def _domains_yaml_header() -> str:
    return (
        "# Noms de domaine payés par le boss.\n"
        "# Édité depuis le dashboard Jarvis (zone Infrastructure) — le YAML est la source de vérité.\n"
        "#\n"
        "# Format de chaque entrée :\n"
        "#   - name      : domaine (ex. example.com)\n"
        "#     registrar : bureau d'enregistrement (ex. OVH, Gandi, Namecheap)\n"
        "#     expires   : date d'expiration au format YYYY-MM-DD\n"
        "#     price     : (optionnel) coût annuel en € — laisser vide si inconnu\n"
        "#     notes     : (optionnel) commentaire libre\n"
    )


def load_domains() -> list[dict]:
    if not DOMAINS_CONFIG_PATH.exists():
        return []
    try:
        import yaml
        cfg = yaml.safe_load(DOMAINS_CONFIG_PATH.read_text()) or {}
        items = cfg.get("domains") or []
        if not isinstance(items, list):
            return []
        return [d for d in items if isinstance(d, dict) and d.get("name")]
    except Exception:
        return []


def save_domains(items: list[dict]) -> None:
    import yaml
    DOMAINS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump({"domains": items}, allow_unicode=True, sort_keys=False, default_flow_style=False)
    DOMAINS_CONFIG_PATH.write_text(_domains_yaml_header() + "\n" + body)


def collect_domains() -> list[dict]:
    items = load_domains()
    today = datetime.now().date()
    out = []
    for d in items:
        name = (d.get("name") or "").strip().lower()
        if not name:
            continue
        registrar = (d.get("registrar") or "").strip()
        expires = (d.get("expires") or "").strip()
        notes = (d.get("notes") or "").strip()
        price = d.get("price")
        days = None
        if expires:
            try:
                exp_dt = datetime.strptime(expires, "%Y-%m-%d").date()
                days = (exp_dt - today).days
            except Exception:
                days = None
        out.append({
            "name": name,
            "registrar": registrar,
            "expires": expires,
            "days_until_expiry": days,
            "price": price if isinstance(price, (int, float)) else None,
            "notes": notes,
        })
    out.sort(key=lambda x: (
        x["days_until_expiry"] if x["days_until_expiry"] is not None else 10**6,
        x["name"],
    ))
    return out


def upsert_domain(payload: dict) -> dict:
    name = (payload.get("name") or "").strip().lower()
    if not name:
        return {"ok": False, "error": "nom requis"}
    if " " in name or "." not in name:
        return {"ok": False, "error": "format de domaine invalide"}

    expires = (payload.get("expires") or "").strip()
    if expires:
        try:
            datetime.strptime(expires, "%Y-%m-%d")
        except Exception:
            return {"ok": False, "error": "date attendue au format YYYY-MM-DD"}

    price_raw = payload.get("price")
    price = None
    if price_raw not in (None, ""):
        try:
            price = float(price_raw)
        except Exception:
            return {"ok": False, "error": "prix doit être un nombre"}

    items = load_domains()
    found = False
    for d in items:
        if (d.get("name") or "").strip().lower() == name:
            d["name"] = name
            d["registrar"] = (payload.get("registrar") or "").strip()
            d["expires"] = expires
            if price is not None:
                d["price"] = price
            elif "price" in d:
                d.pop("price", None)
            d["notes"] = (payload.get("notes") or "").strip()
            found = True
            break

    if not found:
        entry = {
            "name": name,
            "registrar": (payload.get("registrar") or "").strip(),
            "expires": expires,
            "notes": (payload.get("notes") or "").strip(),
        }
        if price is not None:
            entry["price"] = price
        items.append(entry)

    save_domains(items)
    return {"ok": True, "name": name, "created": not found}


def delete_domain(name: str) -> dict:
    name = (name or "").strip().lower()
    if not name:
        return {"ok": False, "error": "nom requis"}
    items = load_domains()
    new_items = [d for d in items if (d.get("name") or "").strip().lower() != name]
    if len(new_items) == len(items):
        return {"ok": False, "error": "domaine introuvable"}
    save_domains(new_items)
    return {"ok": True, "name": name}
