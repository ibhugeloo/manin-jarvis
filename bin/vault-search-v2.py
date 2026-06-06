#!/usr/bin/env python3
"""
vault-search-v2 — Recherche sémantique sur le vault.

Charge le modèle d'embedding local, embed la question, fait un cosine similarity
search dans la DB sqlite-vec, ressort les top K passages avec leur fichier source.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

HOME = Path.home()
DB_PATH = HOME / ".local" / "share" / "jarvis" / "vault.db"
MODEL_NAME = "intfloat/multilingual-e5-small"

# Couleurs ANSI
def supports_color() -> bool:
    return sys.stdout.isatty()

R = "\033[31m" if supports_color() else ""
G = "\033[32m" if supports_color() else ""
Y = "\033[33m" if supports_color() else ""
B = "\033[34m" if supports_color() else ""
D = "\033[2m" if supports_color() else ""
N = "\033[0m" if supports_color() else ""


def open_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(f"❌ DB introuvable : {DB_PATH}\n   Lancez `jarvis-vault-index` pour la créer.")
    db = sqlite3.connect(str(DB_PATH))
    db.enable_load_extension(True)
    import sqlite_vec
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def search(question: str, k: int = 10, source: str | None = None) -> list[dict]:
    db = open_db()

    # Charger le modèle (5-10s au premier appel à cause de PyTorch init)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    # e5 attend 'query:' prefix pour les requêtes
    vec = model.encode(
        [f"query: {question}"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]

    # Recherche cosine top-K — sqlite-vec exige `k = ?` dans le WHERE pour vec0
    # Quand on filtre par source : récupère plus large puis filtre Python
    fetch_k = k * 5 if source else k

    sql = """
        SELECT
            v.distance AS distance,
            c.text AS chunk,
            f.path AS path,
            f.source AS source
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.chunk_id
        JOIN files f ON f.id = c.file_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
    """
    rows = db.execute(sql, (json.dumps(vec.tolist()), fetch_k)).fetchall()

    if source:
        rows = [r for r in rows if r[3] == source][:k]
    else:
        rows = rows[:k]
    return [
        {"distance": row[0], "chunk": row[1], "path": row[2], "source": row[3]}
        for row in rows
    ]


def format_path(path: str) -> str:
    """Raccourcit ~/Documents/Obsidian/vault/... en relatif."""
    p = Path(path)
    home = str(HOME)
    if str(p).startswith(home):
        return "~" + str(p)[len(home):]
    return str(p)


def truncate_chunk(text: str, max_chars: int = 350) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="+", help="Question en langage naturel")
    p.add_argument("-k", type=int, default=10, help="Nombre de résultats (défaut: 10)")
    p.add_argument("-s", "--source", help="Filtrer par source (vault, sessions, memory-mirror, jarvis-repo-docs)")
    p.add_argument("--full", action="store_true", help="Afficher les chunks complets (sans tronquer)")
    p.add_argument("--json", action="store_true", help="Sortie JSON pour pipe")
    args = p.parse_args()

    question = " ".join(args.question)

    results = search(question, k=args.k, source=args.source)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return 0

    if not results:
        print(f"{Y}Aucun résultat.{N}")
        return 1

    print()
    print(f"{B}═══════════════════════════════════════════════════════════════{N}")
    print(f"{B}  Recherche : {question}{N}")
    if args.source:
        print(f"{D}  Filtre source : {args.source}{N}")
    print(f"{B}═══════════════════════════════════════════════════════════════{N}")
    print()

    for i, r in enumerate(results, 1):
        # distance: 0 = identique, plus c'est bas mieux c'est
        score = round((1 - r["distance"]) * 100, 1) if r["distance"] is not None else 0
        path_short = format_path(r["path"])
        chunk = r["chunk"] if args.full else truncate_chunk(r["chunk"])

        print(f"{G}{i:2}.{N} {Y}{score}%{N}  {B}{path_short}{N}  {D}({r['source']}){N}")
        # Indenter le chunk
        for line in chunk.splitlines():
            print(f"      {line}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
