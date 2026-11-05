"""SQLite storage. One database file is one workspace."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  commercial INTEGER NOT NULL DEFAULT 0,
  website TEXT NOT NULL DEFAULT '',
  sender_name TEXT NOT NULL DEFAULT '',
  sender_contact TEXT NOT NULL DEFAULT '',
  keywords TEXT NOT NULL DEFAULT '{}',
  searches TEXT NOT NULL DEFAULT '[]',
  sources TEXT NOT NULL DEFAULT '[]',
  daily_cap INTEGER NOT NULL DEFAULT 25,
  note_limit INTEGER NOT NULL DEFAULT 0,
  min_score REAL NOT NULL DEFAULT 0.45,
  followup_days INTEGER NOT NULL DEFAULT 7,
  followup_body TEXT NOT NULL DEFAULT '',
  auto_email INTEGER NOT NULL DEFAULT 0,
  email_subject TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('person','post','job')),
  external_key TEXT NOT NULL,
  contact_key TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  first_name TEXT NOT NULL DEFAULT '',
  name_confidence REAL NOT NULL DEFAULT 0,
  title TEXT NOT NULL DEFAULT '',
  company TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'manual',
  consent_basis TEXT NOT NULL DEFAULT 'none',
  connection_state TEXT NOT NULL DEFAULT 'none'
    CHECK (connection_state IN ('none','pending','connected')),
  email TEXT NOT NULL DEFAULT '',
  intents TEXT NOT NULL DEFAULT '[]',
  flags TEXT NOT NULL DEFAULT '[]',
  role_hint TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'new',
  rule_score REAL NOT NULL DEFAULT 0,
  ml_score REAL,
  score REAL NOT NULL DEFAULT 0,
  rule_why TEXT NOT NULL DEFAULT '[]',
  explain TEXT NOT NULL DEFAULT '[]',
  stars INTEGER,
  reason TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (campaign_id, external_key)
);
CREATE INDEX IF NOT EXISTS idx_items_rank ON items (campaign_id, kind, status, score DESC);
CREATE INDEX IF NOT EXISTS idx_items_contact ON items (contact_key);
CREATE TABLE IF NOT EXISTS rating_events (
  id INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL,
  campaign_id INTEGER NOT NULL,
  stars INTEGER NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  predicted REAL NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS models (
  campaign_id INTEGER PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
  weights TEXT NOT NULL,
  n INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS variants (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  step TEXT NOT NULL DEFAULT 'message' CHECK (step IN ('connect','message','email')),
  body TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  UNIQUE (campaign_id, name)
);
CREATE TABLE IF NOT EXISTS outreach (
  id INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  campaign_id INTEGER NOT NULL,
  contact_key TEXT NOT NULL,
  variant_id INTEGER,
  step TEXT NOT NULL DEFAULT 'message' CHECK (step IN ('connect','message','followup','email')),
  body TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'ready'
    CHECK (status IN ('ready','sent','replied','positive','skipped','failed')),
  error TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  sent_at TEXT,
  replied_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_outreach_contact ON outreach (contact_key, status);
CREATE TABLE IF NOT EXISTS suppressions (
  contact_key TEXT PRIMARY KEY,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  action TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


JSON_FIELDS = {"keywords", "searches", "sources", "intents", "flags", "explain", "rule_why"}


def row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    out = dict(r)
    for key in JSON_FIELDS & out.keys():
        out[key] = json.loads(out[key] or "null")
    return out


def rows(cursor) -> list[dict]:
    return [row(r) for r in cursor.fetchall()]
