#!/usr/bin/env python3
"""
demo.py — Standalone, runnable demo of the semantic vault search pipeline.

This is a portfolio showcase. It demonstrates the *same* retrieval pipeline that
powers the production CLI (`bin/vault-search-v2.py` + `bin/jarvis-vault-index.py`)
on a tiny, public sample corpus shipped alongside this file — so a reader can run
it WITHOUT access to the owner's private Obsidian vault.

It does NOT fork the production code. It imports the real chunking and embedding
logic from the production files by path (see `_load_production_module`), then runs
the same flow end to end:

    markdown files
        -> chunk_markdown()            (production chunker)
        -> embed "passage: <chunk>"    (production e5 prefix convention)
        -> sqlite-vec vec0 table       (same vector store as production)
        -> embed "query: <question>"   (production query prefix)
        -> cosine top-K                (same MATCH ... k = ? query shape)

Graceful degradation:
- If `sentence-transformers` / `sqlite-vec` are missing, the script prints clear
  install instructions and exits 0 (so CI / a curious reader is never left with a
  cryptic stack trace).

Usage:
    python demo.py                       # run the built-in query suite
    python demo.py "your question here"  # ad-hoc query
    python demo.py --bench               # print timing it actually measured

Requirements (production venv has these; see README "How to run"):
    pip install "sentence-transformers>=2.7" sqlite-vec numpy
First run downloads the embedding model (~470 MB) into the HuggingFace cache.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent  # showcase/semantic-vault-search -> repo root
PROD_INDEXER = REPO_ROOT / "bin" / "jarvis-vault-index.py"
PROD_SEARCH = REPO_ROOT / "bin" / "vault-search-v2.py"
SAMPLE_CORPUS = HERE / "sample_corpus"

MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384


def _load_production_module(path: Path, name: str):
    """Import a hyphenated production script as a module, by file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _check_deps() -> bool:
    """Return True if heavy deps are importable; print guidance and return False otherwise."""
    missing = []
    for mod in ("sentence_transformers", "sqlite_vec", "numpy"):
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)
    if missing:
        print("=" * 70)
        print("Demo cannot run: missing optional dependencies:", ", ".join(missing))
        print("=" * 70)
        print()
        print("This demo runs the REAL embedding + vector-search pipeline, so it")
        print("needs the same libraries as production. Install them with:")
        print()
        print('    pip install "sentence-transformers>=2.7" sqlite-vec numpy')
        print()
        print("The first run also downloads the embedding model (~470 MB):")
        print(f"    {MODEL_NAME}")
        print()
        print("Then re-run:  python demo.py")
        print()
        print("(Exiting 0 — this is expected graceful degradation, not a failure.)")
        return False
    return True


def build_index(db: sqlite3.Connection, model, chunk_fn) -> tuple[int, int]:
    """Index the sample corpus into an in-memory sqlite-vec DB. Returns (files, chunks)."""
    db.executescript(
        f"""
        CREATE TABLE files  (id INTEGER PRIMARY KEY, path TEXT, source TEXT);
        CREATE TABLE chunks (id INTEGER PRIMARY KEY, file_id INTEGER, chunk_index INTEGER, text TEXT);
        CREATE VIRTUAL TABLE vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}]
        );
        """
    )

    md_files = sorted(SAMPLE_CORPUS.glob("*.md"))
    if not md_files:
        sys.exit(f"No sample corpus found in {SAMPLE_CORPUS}")

    n_files = 0
    n_chunks = 0
    cur = db.cursor()
    for fpath in md_files:
        text = fpath.read_text(encoding="utf-8")
        chunks = chunk_fn(text)  # production chunker
        if not chunks:
            continue
        cur.execute(
            "INSERT INTO files (path, source) VALUES (?, ?)",
            (str(fpath), "sample"),
        )
        file_id = cur.lastrowid
        # Production convention: documents are embedded with the "passage:" prefix.
        prefixed = [f"passage: {c}" for c in chunks]
        vectors = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            cur.execute(
                "INSERT INTO chunks (file_id, chunk_index, text) VALUES (?, ?, ?)",
                (file_id, idx, chunk),
            )
            chunk_id = cur.lastrowid
            cur.execute(
                "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                (chunk_id, json.dumps(vec.tolist())),
            )
            n_chunks += 1
        n_files += 1
    db.commit()
    return n_files, n_chunks


def search(db: sqlite3.Connection, model, question: str, k: int = 3) -> list[dict]:
    """Same query shape as production: e5 'query:' prefix + sqlite-vec MATCH ... k = ?."""
    vec = model.encode([f"query: {question}"], normalize_embeddings=True, show_progress_bar=False)[0]
    sql = """
        SELECT v.distance, c.text, f.path
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.chunk_id
        JOIN files  f ON f.id = c.file_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
    """
    rows = db.execute(sql, (json.dumps(vec.tolist()), k)).fetchall()
    return [{"distance": r[0], "chunk": r[1], "path": r[2]} for r in rows]


def fmt_result(r: dict) -> str:
    score = round((1 - r["distance"]) * 100, 1)
    name = Path(r["path"]).name
    snippet = " ".join(r["chunk"].split())
    if len(snippet) > 140:
        snippet = snippet[:140].rsplit(" ", 1)[0] + "…"
    return f"  {score:5.1f}%  {name:14}  {snippet}"


# Queries chosen so a keyword grep would MISS the right file (no shared word),
# but semantic retrieval finds it by concept.
DEMO_QUERIES = [
    "what's my strategy for splitting up my savings",  # -> investing.md ("allocation/weighting")
    "keeping my home network secure",                  # -> homelab.md ("VLAN/firewall/segmentation")
    "I get queasy on long bus rides",                  # -> travel.md ("motion sickness")
    "vegetarian comfort meal for a cold evening",      # -> cooking.md ("lentils/rice")
    "how do I bulk up without losing endurance",       # -> fitness.md ("lean mass + cardio")
]


def open_vec_db() -> sqlite3.Connection:
    import sqlite_vec
    db = sqlite3.connect(":memory:")
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="*", help="Ad-hoc query (default: run the built-in suite)")
    ap.add_argument("-k", type=int, default=3, help="Top-K results (default 3)")
    ap.add_argument("--bench", action="store_true", help="Print timings actually measured this run")
    args = ap.parse_args()

    if not _check_deps():
        return 0

    # Pull the REAL chunker from the production indexer (no fork).
    indexer = _load_production_module(PROD_INDEXER, "prod_indexer")
    chunk_fn = indexer.chunk_markdown

    from sentence_transformers import SentenceTransformer

    t0 = time.perf_counter()
    model = SentenceTransformer(MODEL_NAME)
    t_model = time.perf_counter() - t0

    db = open_vec_db()
    t0 = time.perf_counter()
    n_files, n_chunks = build_index(db, model, chunk_fn)
    t_index = time.perf_counter() - t0

    print(f"\nIndexed {n_files} files / {n_chunks} chunks from {SAMPLE_CORPUS.name}/")
    print(f"Model load: {t_model:.2f}s   Index build: {t_index:.2f}s\n")

    queries = [" ".join(args.question)] if args.question else DEMO_QUERIES
    query_times = []
    for q in queries:
        t0 = time.perf_counter()
        results = search(db, model, q, k=args.k)
        dt = time.perf_counter() - t0
        query_times.append(dt)
        print(f'Q: "{q}"   ({dt * 1000:.0f} ms)')
        for r in results:
            print(fmt_result(r))
        print()

    if args.bench and query_times:
        avg_ms = sum(query_times) / len(query_times) * 1000
        print("-" * 70)
        print("Measured on this machine (your numbers will differ):")
        print(f"  model load (cold)   : {t_model:.2f} s")
        print(f"  index {n_chunks} chunks   : {t_index:.2f} s")
        print(f"  query (avg of {len(query_times):>2})    : {avg_ms:.0f} ms")
        print("-" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
