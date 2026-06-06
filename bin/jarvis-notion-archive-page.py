#!/usr/bin/env python3
"""jarvis-notion-archive-page — Crée une sous-page Notion (API directe) à partir d'un
recap de session markdown, sous la page Inbox Jarvis.

Imprime sur stdout :
  OK <url>      si la page a été créée (HTTP 200)
  ERR <detail>  sinon (le caller NE supprime PAS le fichier dans ce cas)

Env requis : NOTION_TOKEN, NOTION_VERSION, INBOX_JARVIS_ID.
Stdlib uniquement (urllib) — pas de dépendance externe, headless-safe.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

CHUNK = 1900          # < 2000 (limite rich_text content Notion)
MAX_BLOCKS = 95       # < 100 (limite children par create) ; garde marge pour l'entête

def main():
    if len(sys.argv) < 2:
        print("ERR usage: archive-page <file.md>")
        return 1
    path = sys.argv[1]
    token = os.environ.get("NOTION_TOKEN", "").strip()
    version = os.environ.get("NOTION_VERSION", "2025-09-03").strip()
    parent = os.environ.get("INBOX_JARVIS_ID", "").strip()
    if not token or not parent:
        print("ERR token/parent manquant")
        return 1

    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        print(f"ERR lecture fichier: {e}")
        return 1

    base = os.path.basename(path)
    # Titre : extrait du frontmatter `title:` si présent, sinon dérivé du nom de fichier.
    m = re.search(r'^title:\s*(.+)$', raw, re.M)
    if m:
        title = m.group(1).strip().strip('"').strip("'")
    else:
        # AAAA-MM-JJ-HHMM-<uuid>-<slug>.md -> "<slug> — AAAA-MM-JJ"
        stem = base[:-3] if base.endswith(".md") else base
        date = stem[:10]
        slug = re.sub(r'^\d{4}-\d{2}-\d{2}-\d{4}-[0-9a-f]+-', '', stem).replace('-', ' ')
        title = f"{slug} — {date}" if slug else stem
    title = f"[archive session] {title}"[:1900]

    # Découpe le markdown brut en blocs code (préserve tout, zéro parsing fragile).
    chunks = [raw[i:i+CHUNK] for i in range(0, len(raw), CHUNK)] or [""]
    truncated = len(chunks) > MAX_BLOCKS
    chunks = chunks[:MAX_BLOCKS]

    children = [{
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {
                "content": f"Archive automatique du recap local « {base} » (purge >90j). Contenu intégral ci-dessous."}}],
            "icon": {"emoji": "🗄️"},
        },
    }]
    for c in chunks:
        children.append({
            "object": "block", "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": c}}],
                "language": "markdown",
            },
        })
    if truncated:
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {
                "content": "⚠️ Contenu tronqué à l'archivage (session inhabituellement longue). Source git conservée."}}]},
        })

    payload = {
        "parent": {"type": "page_id", "page_id": parent},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": children,
    }

    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": version,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            url = body.get("url", "")
            print(f"OK {url}")
            return 0
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"ERR HTTP {e.code}: {detail}")
        return 1
    except Exception as e:
        print(f"ERR {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
