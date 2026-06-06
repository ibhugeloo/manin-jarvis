-- MOS — Mission Operating System
-- Schéma SQLite + sqlite-vec (vec0)
--
-- Source de vérité MISSIONS = filesystem markdown (share/missions/*.md).
-- DB = miroir + index sémantique. Reconstructible depuis le filesystem.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- =========================================================================
-- events : tous les hooks Claude Code captés
-- =========================================================================
CREATE TABLE IF NOT EXISTS events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  hook        TEXT NOT NULL,            -- SessionStart, PreToolUse, PostToolUse, UserPromptSubmit, SessionEnd, ...
  tool        TEXT,                     -- Edit, Bash, Read, ... (si applicable)
  session_id  TEXT,                     -- Claude Code session id si dispo
  cwd         TEXT,                     -- working directory
  payload     TEXT                      -- JSON brut, schemaless
);
CREATE INDEX IF NOT EXISTS idx_events_ts      ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_hook    ON events(hook);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

-- =========================================================================
-- missions : miroir des fichiers share/missions/*.md
-- =========================================================================
CREATE TABLE IF NOT EXISTS missions (
  id            TEXT PRIMARY KEY,        -- ex: MOS-001
  title         TEXT NOT NULL,
  status        TEXT NOT NULL CHECK(status IN ('open','wip','blocked','done','dropped')),
  opened_at     TEXT NOT NULL,
  closed_at     TEXT,
  deadline      TEXT,
  parent_dream  TEXT,                    -- ref à dreams.md (slug)
  deliverable   TEXT,                    -- une ligne, ce qui prouve que c'est fait
  tags          TEXT,                    -- JSON array
  body          TEXT,                    -- corps markdown brut (pour search vec0)
  file_path     TEXT NOT NULL UNIQUE,
  file_mtime    REAL NOT NULL,           -- pour détection changement
  synced_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_missions_dream  ON missions(parent_dream);

-- =========================================================================
-- patterns : observations user-model (promues depuis observations.md)
-- =========================================================================
CREATE TABLE IF NOT EXISTS patterns (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  text        TEXT NOT NULL,
  confidence  TEXT NOT NULL CHECK(confidence IN ('low','medium','high')),
  target      TEXT,                      -- profil.md, agents.md, jarvis_soul.md, ...
  occurrences INTEGER NOT NULL DEFAULT 1,
  promoted    INTEGER NOT NULL DEFAULT 0 -- 0/1, marqué quand intégré au target
);

-- =========================================================================
-- vec0 virtual tables (embeddings)
-- Chargées via sqlite_vec.load(db) avant CREATE.
-- 384 = dim de multilingual-e5-small (cohérent avec vault-search-v2)
-- =========================================================================
-- vec_missions : 1 vecteur par mission, rowid = ROWID interne mission_vec_map
-- vec_patterns : 1 vecteur par pattern observé

-- Table de mapping mission_id ↔ rowid vec0
CREATE TABLE IF NOT EXISTS mission_vec_map (
  rowid       INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id  TEXT NOT NULL UNIQUE REFERENCES missions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pattern_vec_map (
  rowid      INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_id INTEGER NOT NULL UNIQUE REFERENCES patterns(id) ON DELETE CASCADE
);
