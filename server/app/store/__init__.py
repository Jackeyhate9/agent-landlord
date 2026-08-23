from __future__ import annotations

from typing import Any

from ._postgres import PostgresStore
from ._sqlite import SqliteStore


class Store:
    """Factory that selects the correct backend at startup."""

    def __init__(self, path: str = ":memory:", postgres_url: str = "") -> None:
        if postgres_url:
            try:
                self._impl = PostgresStore(postgres_url)
                return
            except Exception as exc:
                # In production, crash loudly. In dev/test, fallback to SQLite with warning.
                import os

                if os.getenv("APP_ENV", "").lower() in ("production", "prod"):
                    raise
                print(f"[store] postgres_url set but Postgres unavailable ({exc}), falling back to SQLite for dev/test")
        self._impl = SqliteStore(path)

    def transaction(self):
        return self._impl.transaction()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        return self._impl.execute(sql, params)

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        return self._impl.one(sql, params)

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return self._impl.all(sql, params)

    @staticmethod
    def json(value: Any) -> str:
        import json

        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
