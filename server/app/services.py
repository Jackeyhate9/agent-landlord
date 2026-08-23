from __future__ import annotations

import asyncio
import hashlib
import math
import random
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from ..protocol_constants import STAKE_TIERS

from .config import Settings
from .schemas import PublicEvent, QueueView
from .security import opaque_id, sign_token
from .store import Store


def now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime | None = None) -> str:
    return (value or now()).isoformat()


class JoinService:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def create_code(self) -> tuple[str, str]:
        while True:
            code = "AL-" + "".join(secrets.choice(self.alphabet) for _ in range(4)) + "-" + "".join(
                secrets.choice(self.alphabet) for _ in range(4)
            )
            digest = hashlib.sha256(code.encode()).hexdigest()
            expires = now() + timedelta(seconds=self.settings.join_code_ttl_seconds)
            try:
                self.store.execute("INSERT INTO join_codes VALUES(?,?,NULL)", (digest, iso(expires)))
                return code, iso(expires)
            except Exception:
                continue

    def redeem(self, code: str, public_key: str, detected_runtime: str | None = None,
               detected_model: str | None = None) -> dict[str, Any]:
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM join_codes WHERE code_hash=?", (digest,)).fetchone()
            if not row or row["used_at"] or datetime.fromisoformat(row["expires_at"]) <= now():
                raise HTTPException(status_code=410, detail="join code expired or already used")
            db.execute("UPDATE join_codes SET used_at=? WHERE code_hash=?", (iso(), digest))
            existing = db.execute("SELECT * FROM agents WHERE owner_public_key=?", (public_key,)).fetchone()
            first_registration = existing is None
            if existing:
                agent_id = existing["id"]
            else:
                agent_id = opaque_id("agent")
                created = iso()
                # 首次注册时采用隐私友好的自动检测结果（仅类型名/模型名标签），
                # 之后用户可在 /join 配置页自行修改，服务器不据此做任何认证。
                runtime_label = (detected_runtime or "Bridge")[:32]
                model_label = (detected_model or "Custom")[:24]
                db.execute(
                    "INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (agent_id, public_key, "New Agent", model_label, runtime_label, None,
                     self.settings.initial_arena_tokens, 0, 100, 0, 1, 0, created),
                )
                db.execute("INSERT INTO agent_keys VALUES(?,?)", (agent_id, public_key))
                db.execute(
                    "INSERT INTO leaderboard_stats(agent_id,peak_at,current_at) VALUES(?,?,?)",
                    (agent_id, self.settings.initial_arena_tokens, self.settings.initial_arena_tokens),
                )
                db.execute(
                    "INSERT INTO arena_token_ledger VALUES(?,?,?,?,?,?,?,?)",
                    (opaque_id("ledger"), agent_id, None, self.settings.initial_arena_tokens, 0,
                     self.settings.initial_arena_tokens, "INITIAL_GRANT", created),
                )
            session_id = opaque_id("session")
            expires = now() + timedelta(days=1)
            db.execute(
                "INSERT INTO agent_sessions VALUES(?,?,?,?,?,1)",
                (session_id, agent_id, iso(), iso(expires), iso()),
            )
        return {
            "agent_id": agent_id,
            "session_token": sign_token(agent_id, "agent"),
            "session_id": session_id,
            "initial_grant": first_registration,
        }


class ArenaService:
    REQUIRED_CERTS = {"connection", "heartbeat", "observation_parse", "valid_action", "timeout_behavior", "three_turns"}

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def configure(self, agent_id: str, values: dict[str, Any]) -> dict[str, Any]:
        self.store.execute(
            "UPDATE agents SET agent_name=?,model_label=?,runtime_label=?,avatar_url=?,max_stake=?,pov_allowed=? WHERE id=?",
            (values["agent_name"], values["model_label"], values["runtime_label"], values.get("avatar_url"),
             values["max_stake"], int(values["pov_allowed"]), agent_id),
        )
        return self.store.one("SELECT * FROM agents WHERE id=?", (agent_id,)) or {}

    def certify(self, agent_id: str, passed: list[str]) -> bool:
        complete = self.REQUIRED_CERTS.issubset(set(passed))
        if not complete:
            raise HTTPException(status_code=422, detail="all six certification tests must pass")
        self.store.execute("UPDATE agents SET certified=1 WHERE id=?", (agent_id,))
        return True

    def join_queue(self, agent_id: str) -> None:
        agent = self.store.one("SELECT * FROM agents WHERE id=?", (agent_id,))
        if not agent or not agent["certified"]:
            raise HTTPException(status_code=403, detail="AGENT CERTIFIED required")
        self.store.execute(
            "INSERT OR IGNORE INTO queue_entries(agent_id,joined_at,auto_play) VALUES(?,?,1)", (agent_id, iso())
        )

    def leave_queue(self, agent_id: str) -> None:
        self.store.execute("DELETE FROM queue_entries WHERE agent_id=?", (agent_id,))

    def queue(self) -> list[QueueView]:
        rows = self.store.all(
            "SELECT a.*,q.id AS queue_id FROM queue_entries q JOIN agents a ON a.id=q.agent_id ORDER BY q.id"
        )
        return [QueueView(position=index + 1, agent_id=row["id"], agent_name=row["agent_name"],
                          model_label=row["model_label"], current_at=row["balance"],
                          pov_allowed=bool(row["pov_allowed"]), online=bool(row["online"]),
                          is_house=bool(row["is_house"])) for index, row in enumerate(rows)]

    def heartbeat(self, agent_id: str) -> None:
        self.store.execute("UPDATE agents SET online=1 WHERE id=?", (agent_id,))
        self.store.execute("UPDATE agent_sessions SET last_heartbeat=? WHERE agent_id=? AND active=1", (iso(), agent_id))


class TokenService:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    @staticmethod
    def safe_base_stake(requested: list[int], balances: list[int], max_multiplier: int) -> int:
        if len(requested) != 3 or len(balances) != 3:
            raise ValueError("exactly three players required")
        # Any seat may become landlord; every participant must cover 2x unit loss.
        capacity = min(balance // (2 * max_multiplier) for balance in balances)
        allowed = [stake for stake in STAKE_TIERS if stake <= min(requested) and stake <= capacity]
        if not allowed:
            raise ValueError("insufficient Arena Token for minimum base stake")
        return max(allowed)

    def settle(self, game_id: str, landlord_id: str, farmer_ids: list[str], landlord_won: bool,
               base_stake: int, multiplier: int) -> dict[str, int]:
        if len(farmer_ids) != 2 or len(set(farmer_ids + [landlord_id])) != 3:
            raise ValueError("settlement requires three distinct agents")
        unit = base_stake * min(multiplier, self.settings.max_multiplier)
        deltas = ({landlord_id: 2 * unit, farmer_ids[0]: -unit, farmer_ids[1]: -unit} if landlord_won else
                  {landlord_id: -2 * unit, farmer_ids[0]: unit, farmer_ids[1]: unit})
        if sum(deltas.values()) != 0:
            raise AssertionError("token settlement must be zero-sum")
        with self.store.transaction() as db:
            for agent_id, delta in deltas.items():
                row = db.execute("SELECT balance FROM agents WHERE id=?", (agent_id,)).fetchone()
                if not row or row["balance"] + delta < 0:
                    raise ValueError("settlement would create negative balance")
            for agent_id, delta in deltas.items():
                before = db.execute("SELECT balance FROM agents WHERE id=?", (agent_id,)).fetchone()["balance"]
                after = before + delta
                db.execute("UPDATE agents SET balance=? WHERE id=?", (after, agent_id))
                db.execute(
                    "INSERT INTO arena_token_ledger VALUES(?,?,?,?,?,?,?,?)",
                    (opaque_id("ledger"), agent_id, game_id, delta, before, after,
                     "GAME_WIN" if delta > 0 else "GAME_LOSS", iso()),
                )
                won = delta > 0
                db.execute(
                    "UPDATE leaderboard_stats SET matches_played=matches_played+1,wins=wins+?,losses=losses+?,"
                    "current_at=?,peak_at=MAX(peak_at,?),current_win_streak=CASE WHEN ? THEN current_win_streak+1 ELSE 0 END,"
                    "max_win_streak=MAX(max_win_streak,CASE WHEN ? THEN current_win_streak+1 ELSE 0 END),"
                    "landlord_wins=landlord_wins+?,farmer_wins=farmer_wins+? WHERE agent_id=?",
                    (int(won), int(not won), after, after, int(won), int(won),
                     int(won and agent_id == landlord_id), int(won and agent_id != landlord_id), agent_id),
                )
        return deltas

    def adjust(self, admin: str, agent_id: str, operation: str, amount: int, reason: str) -> dict[str, int]:
        with self.store.transaction() as db:
            row = db.execute("SELECT balance FROM agents WHERE id=?", (agent_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="agent not found")
            before = int(row["balance"])
            after = self.settings.initial_arena_tokens if operation == "reset" else before + (amount if operation == "add" else -amount)
            if after < 0:
                raise HTTPException(status_code=422, detail="Arena Token cannot be negative")
            db.execute("UPDATE agents SET balance=? WHERE id=?", (after, agent_id))
            db.execute("UPDATE leaderboard_stats SET current_at=?,peak_at=MAX(peak_at,?) WHERE agent_id=?", (after, after, agent_id))
            timestamp = iso()
            db.execute("INSERT INTO arena_token_ledger VALUES(?,?,?,?,?,?,?,?)",
                       (opaque_id("ledger"), agent_id, None, after - before, before, after,
                        "RESET" if operation == "reset" else "ADMIN_ADJUSTMENT", timestamp))
            db.execute("INSERT INTO admin_audit_logs VALUES(?,?,?,?,?,?,?)",
                       (opaque_id("audit"), admin, agent_id, before, after, reason, timestamp))
        return {"before": before, "after": after}

    def hall(self) -> list[dict[str, Any]]:
        rows = self.store.all(
            "SELECT s.*,a.agent_name,a.model_label,a.avatar_url FROM leaderboard_stats s JOIN agents a ON a.id=s.agent_id "
            "WHERE matches_played>=5"
        )
        if not rows:
            return []
        peaks = sorted(row["peak_at"] for row in rows)
        streaks = sorted(row["max_win_streak"] for row in rows)

        def percentile(values: list[int], value: int) -> float:
            if len(values) == 1:
                return 100.0
            # Standard percentile: (below + 0.5*equal) / n  → 0-100, ties share top
            below = sum(candidate < value for candidate in values)
            equal = sum(candidate == value for candidate in values)
            return 100.0 * (below + 0.5 * equal) / len(values)

        for row in rows:
            row["hof_score"] = round(0.7 * percentile(peaks, row["peak_at"]) +
                                     0.3 * percentile(streaks, row["max_win_streak"]), 1)
        rows.sort(key=lambda item: (-item["hof_score"], -item["peak_at"], -item["max_win_streak"], -item["wins"]))
        return rows


class BroadcastService:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.condition = asyncio.Condition()
        self.sequence = self.store.one("SELECT COALESCE(MAX(sequence),0) AS value FROM game_events")["value"]

    async def append(self, event_type: str, payload: dict[str, Any], game_id: str | None = None,
                     actor: str | None = None) -> PublicEvent:
        created = now()
        async with self.condition:
            self.sequence += 1
            event = PublicEvent(event_id=opaque_id("event"), game_id=game_id, sequence=self.sequence,
                                type=event_type, actor=actor, payload=payload, created_at=iso(created),
                                broadcast_at=iso(created + timedelta(seconds=self.settings.broadcast_delay_seconds)))
            self.store.execute("INSERT INTO game_events VALUES(?,?,?,?,?,?,?,?,NULL)",
                               (event.event_id, game_id, event.sequence, event.type, actor,
                                self.store.json(payload), event.created_at, event.broadcast_at))
            self.condition.notify_all()
            return event

    def due(self, after_sequence: int = 0) -> list[PublicEvent]:
        rows = self.store.all(
            "SELECT * FROM game_events WHERE sequence>? AND broadcast_at<=? ORDER BY sequence", (after_sequence, iso())
        )
        return [PublicEvent(event_id=row["event_id"], game_id=row["game_id"], sequence=row["sequence"],
                            type=row["type"], actor=row["actor"], payload=__import__("json").loads(row["payload_json"]),
                            created_at=row["created_at"], broadcast_at=row["broadcast_at"]) for row in rows]

    def table_projection(self) -> dict[str, Any]:
        states = [event for event in self.due() if event.type == "TABLE_STATE"]
        return states[-1].payload if states else {"status": "IDLE", "live_pov": None, "delay_seconds": self.settings.broadcast_delay_seconds}

    def queue_projection(self) -> list[dict[str, Any]]:
        queue: list[dict[str, Any]] = []
        for event in self.due():
            agent_id = event.payload.get("agent_id")
            if event.type == "QUEUE_ENTER" and agent_id:
                queue = [entry for entry in queue if entry.get("agent_id") != agent_id]
                queue.append(dict(event.payload))
            elif event.type == "QUEUE_EXIT" and agent_id:
                queue = [entry for entry in queue if entry.get("agent_id") != agent_id]
            elif event.type == "TOKEN_CHANGE" and agent_id:
                for entry in queue:
                    if entry.get("agent_id") == agent_id:
                        entry["current_at"] = event.payload.get("after", entry.get("current_at", 0) + event.payload.get("delta", 0))
        for position, entry in enumerate(queue, 1):
            entry["position"] = position
        return queue

    def hall_projection(self) -> list[dict[str, Any]]:
        updates = [event for event in self.due() if event.type == "HALL_UPDATE"]
        return list(updates[-1].payload.get("entries", [])) if updates else []

    async def wait_for_due(self, after_sequence: int, timeout: float = 1.0) -> list[PublicEvent]:
        due = self.due(after_sequence)
        if due:
            return due
        async with self.condition:
            try:
                await asyncio.wait_for(self.condition.wait(), timeout=timeout)
            except TimeoutError:
                pass
        return self.due(after_sequence)
