from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from ._schema import POSTGRES_SCHEMA


class PostgresStore:
    def __init__(self, postgres_url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for postgres_url but not installed. Install with: pip install 'psycopg[binary]'") from exc

        self.pg = psycopg.connect(postgres_url, autocommit=False)
        self.pg.autocommit = True
        self.lock = threading.RLock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        for stmt in POSTGRES_SCHEMA.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                self.pg.execute(stmt)
            except Exception:
                self.pg.rollback()
        self.pg.commit()

    @staticmethod
    def _to_pg(sql: str) -> str:
        # SQLite uses "?" placeholder, Postgres uses "%s"
        return sql.replace("?", "%s")

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self.lock:
            self.pg.execute("BEGIN")
            try:
                yield self.pg
                self.pg.commit()
            except Exception:
                self.pg.rollback()
                raise

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        with self.lock:
            cur = self.pg.cursor()
            cur.execute(self._to_pg(sql), list(params) if params else None)
            if cur.description:
                return cur
            return cur

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cur = self.execute(sql, params)
        row = cur.fetchone() if cur.description else None
        return dict(row) if row else None

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self.execute(sql, params)
        if not cur.description:
            return []
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def json(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
