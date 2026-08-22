from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SQLITE_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS agents (
 id TEXT PRIMARY KEY, owner_public_key TEXT NOT NULL UNIQUE, agent_name TEXT NOT NULL,
 model_label TEXT NOT NULL, runtime_label TEXT NOT NULL, avatar_url TEXT,
 balance INTEGER NOT NULL CHECK(balance >= 0), certified INTEGER NOT NULL DEFAULT 0,
 max_stake INTEGER NOT NULL DEFAULT 100, pov_allowed INTEGER NOT NULL DEFAULT 0,
 online INTEGER NOT NULL DEFAULT 1, is_house INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_sessions (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, last_heartbeat TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS agent_keys (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), owner_public_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS join_codes (
 code_hash TEXT PRIMARY KEY, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS queue_entries (
 id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL UNIQUE REFERENCES agents(id),
 joined_at TEXT NOT NULL, auto_play INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS games (
 id TEXT PRIMARY KEY, status TEXT NOT NULL, base_stake INTEGER NOT NULL,
 multiplier INTEGER NOT NULL DEFAULT 1, winner_side TEXT, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS game_players (
 game_id TEXT NOT NULL REFERENCES games(id), agent_id TEXT NOT NULL REFERENCES agents(id),
 seat TEXT NOT NULL, token_delta INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(game_id, agent_id)
);
CREATE TABLE IF NOT EXISTS game_events (
 event_id TEXT PRIMARY KEY, game_id TEXT, sequence INTEGER NOT NULL UNIQUE, type TEXT NOT NULL,
 actor TEXT, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, broadcast_at TEXT NOT NULL,
 published_at TEXT
);
CREATE TABLE IF NOT EXISTS arena_token_ledger (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), game_id TEXT,
 delta INTEGER NOT NULL, balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL CHECK(balance_after >= 0),
 type TEXT NOT NULL, timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leaderboard_stats (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), matches_played INTEGER NOT NULL DEFAULT 0,
 wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
 peak_at INTEGER NOT NULL, current_at INTEGER NOT NULL, max_win_streak INTEGER NOT NULL DEFAULT 0,
 current_win_streak INTEGER NOT NULL DEFAULT 0, landlord_wins INTEGER NOT NULL DEFAULT 0,
 farmer_wins INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admin_audit_logs (
 id TEXT PRIMARY KEY, admin TEXT NOT NULL, agent_id TEXT NOT NULL, before INTEGER NOT NULL,
 after INTEGER NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL
);
"""


class _Backend:
    """Minimal SQL backend abstraction. Supports SQLite and PostgreSQL."""

    def __init__(self, use_postgres: bool = False, path: str = ":memory:", postgres_url: str = "") -> None:
        self.use_postgres = use_postgres
        try:
            if use_postgres:
                import psycopg  # local import to keep sqlite path dependency-light

                self.pg = psycopg.connect(postgres_url, autocommit=False)
                self.pg.autocommit = True
                self.lock = threading.RLock()
                self._ensure_schema()
                return
        except Exception as exc:
            # Fallback to SQLite if psycopg missing or connect fails (dev/test safety)
            self.use_postgres = False
        # SQLite path (default runtime + fallback)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.sqlite = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.sqlite.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.sqlite.executescript(SQLITE_SCHEMA)

    def _ensure_schema(self) -> None:
        # PostgreSQL port of SQLite_SCHEMA (uses BOOLEAN, SERIAL, and %s not needed here)
        schema = SQLITE_SCHEMA.replace("AUTOINCREMENT", "GENERATED ALWAYS AS IDENTITY")
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            # PostgreSQL has no PRAGMA; skip it
            if stmt.upper().startswith("PRAGMA"):
                continue
            try:
                self.pg.execute(stmt)
            except Exception:
                self.pg.rollback()
        self.pg.commit()

    def _placeholder(self, sql: str) -> str:
        # Convert '?' to '%s' for psycopg; naive but adequate for our fixed SQL
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        with self.lock:
            if self.use_postgres:
                cur = self.pg.cursor()
                cur.execute(self._placeholder(sql), list(params) if params else None)
                if cur.description:
                    return cur
                return cur
            return self.sqlite.execute(sql, params)

    def transaction(self):
        if self.use_postgres:
            return _PgTx(self)
        return _SqliteTx(self)

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cur = self.execute(sql, params)
        row = cur.fetchone() if cur.description else None
        return dict(row) if row else None

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self.execute(sql, params)
        if not cur.description:
            return []
        return [dict(row) for row in cur.fetchall()]

    def commit(self) -> None:
        if self.use_postgres:
            self.pg.commit()
        else:
            self.sqlite.commit()

    def rollback(self) -> None:
        if self.use_postgres:
            self.pg.rollback()
        else:
            self.sqlite.rollback()

    def close(self) -> None:
        if self.use_postgres:
            self.pg.close()
        else:
            self.sqlite.close()


class _SqliteTx:
    def __init__(self, store: _Backend) -> None:
        self.store = store

    def __enter__(self) -> sqlite3.Connection:
        with self.store.lock:
            self.store.sqlite.execute("BEGIN IMMEDIATE")
            return self.store.sqlite

    def __exit__(self, exc_type, exc, tb) -> None:
        with self.store.lock:
            if exc_type:
                self.store.sqlite.execute("ROLLBACK")
            else:
                self.store.sqlite.execute("COMMIT")
        return False


class _PgTx:
    def __init__(self, store: _Backend) -> None:
        self.store = store

    def __enter__(self):
        with self.store.lock:
            self.store.pg.execute("BEGIN")
            return self.store.pg

    def __exit__(self, exc_type, exc, tb) -> None:
        with self.store.lock:
            if exc_type:
                self.store.pg.rollback()
            else:
                self.store.pg.commit()
        return False


class Store:
    """Application seam. Uses PostgreSQL when POSTGRES_URL is set, else SQLite."""

    def __init__(self, path: str = ":memory:", postgres_url: str = "") -> None:
        self.backend = _Backend(use_postgres=bool(postgres_url), path=path, postgres_url=postgres_url)

    @contextmanager
    def transaction(self):
        with self.backend.transaction() as db:
            yield db

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        return self.backend.execute(sql, params)

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        return self.backend.one(sql, params)

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return self.backend.all(sql, params)

    @staticmethod
    def json(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
