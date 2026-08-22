"""Move due durable events to the Redis public stream in strict sequence order."""

import asyncio
import json

from redis.asyncio import Redis

from .config import get_settings
from .services import iso
from .store import Store


async def run() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for the broadcast worker")
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    store = Store(settings.sqlite_path)
    while True:
        rows = store.all(
            "SELECT * FROM game_events WHERE published_at IS NULL AND broadcast_at<=? ORDER BY sequence LIMIT 100", (iso(),)
        )
        for row in rows:
            await redis.xadd("arena:public-events", {
                "event_id": row["event_id"], "game_id": row["game_id"] or "", "sequence": row["sequence"],
                "type": row["type"], "actor": row["actor"] or "", "payload": row["payload_json"],
                "created_at": row["created_at"], "broadcast_at": row["broadcast_at"],
            }, id=f"{row['sequence']}-0")
            store.execute("UPDATE game_events SET published_at=? WHERE event_id=?", (iso(), row["event_id"]))
        await asyncio.sleep(0.1 if rows else 0.5)


if __name__ == "__main__":
    asyncio.run(run())

