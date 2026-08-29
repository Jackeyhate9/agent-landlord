from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from server.game_engine import Game, GameConfig, InvalidAction, Phase

from .config import Settings
from .security import opaque_id
from .services import ArenaService, BroadcastService, TokenService, iso
from .store import Store


@dataclass
class ActiveMatch:
    game: Game
    agent_ids: list[str]
    base_stake: int


class MatchService:
    """Application seam connecting authenticated agents to the rules engine."""

    def __init__(self, store: Store, settings: Settings, arena: ArenaService,
                 tokens: TokenService, broadcast: BroadcastService) -> None:
        self.store = store
        self.settings = settings
        self.arena = arena
        self.tokens = tokens
        self.broadcast = broadcast
        self.active: ActiveMatch | None = None
        self.turn_started_at = time.monotonic()
        self.next_match_at = 0.0

    def can_start(self) -> bool:
        return (
            (not self.active or self.active.game.is_over)
            and time.monotonic() >= self.next_match_at
            and len(self.arena.queue()) >= 3
        )

    def turn_expired(self) -> bool:
        return bool(
            self.active
            and not self.active.game.is_over
            and (time.monotonic() - self.turn_started_at) * 1000
            >= self.settings.agent_decision_timeout_ms
        )

    async def start_next(self, seed: int | None = None) -> dict[str, Any]:
        if self.active and not self.active.game.is_over:
            raise HTTPException(status_code=409, detail="a match is already active")
        queue = self.arena.queue()
        if len(queue) < 3:
            raise HTTPException(status_code=409, detail="three certified queued agents required")
        agent_ids = [entry.agent_id for entry in queue[:3]]
        rows = [self.store.one("SELECT * FROM agents WHERE id=?", (agent_id,)) for agent_id in agent_ids]
        if any(row is None for row in rows):
            raise HTTPException(status_code=409, detail="queued agent is unavailable")
        base_stake = TokenService.safe_base_stake(
            [int(row["max_stake"]) for row in rows if row],
            [int(row["balance"]) for row in rows if row],
            self.settings.max_multiplier,
        )
        game = Game(seed=seed, config=GameConfig(max_multiplier=self.settings.max_multiplier, base_stake=base_stake))
        self.active = ActiveMatch(game=game, agent_ids=agent_ids, base_stake=base_stake)
        self.turn_started_at = time.monotonic()
        self.store.execute("INSERT INTO games VALUES(?,?,?,?,?,?,?)",
                           (game.game_id, "BIDDING", base_stake, 1, None, iso(), None))
        for seat, agent_id in enumerate(agent_ids):
            self.store.execute("INSERT INTO game_players VALUES(?,?,?,0)",
                               (game.game_id, agent_id, f"seat_{seat}"))
            self.store.execute("DELETE FROM queue_entries WHERE agent_id=?", (agent_id,))
            await self.broadcast.append("QUEUE_EXIT", {"agent_id": agent_id}, game_id=game.game_id)
        await self.broadcast.append("DEAL", {
            "players": [self.public_agent(agent_id) for agent_id in agent_ids],
            "base_stake": base_stake,
            "remaining_card_counts": [17, 17, 17],
        }, game_id=game.game_id)
        await self.broadcast.append("TABLE_STATE", self.snapshot(), game_id=game.game_id)
        return self.snapshot()

    def public_agent(self, agent_id: str) -> dict[str, Any]:
        row = self.store.one("SELECT * FROM agents WHERE id=?", (agent_id,)) or {}
        return {key: row.get(key) for key in
                ("id", "agent_name", "model_label", "avatar_url", "balance", "pov_allowed", "online", "is_house")}

    def snapshot(self) -> dict[str, Any]:
        if not self.active:
            return {"status": "IDLE", "live_pov": None}
        game = self.active.game
        pov_seat = next((index for index, agent_id in enumerate(self.active.agent_ids)
                         if (self.store.one("SELECT pov_allowed FROM agents WHERE id=?", (agent_id,)) or {}).get("pov_allowed")), 0)
        observation = game.observation(pov_seat)
        players = []
        for index, agent_id in enumerate(self.active.agent_ids):
            player = self.public_agent(agent_id)
            player["seat_index"] = index
            if game.landlord is None:
                player["role"] = f"seat_{index}"
            else:
                player["role"] = (
                    "landlord" if index == game.landlord
                    else "farmer_left" if index == (game.landlord + 1) % 3
                    else "farmer_right"
                )
            players.append(player)
        return {
            "status": game.phase.value.upper(),
            "game_id": game.game_id,
            "current_seat": game.current_player,
            "players": players,
            "base_stake": self.active.base_stake,
            "current_multiplier": game.current_multiplier,
            "live_pov": {"seat": pov_seat, "hand": observation["hand"]},
            "remaining_card_counts": observation["remaining_card_counts"],
            "last_action": observation["last_action"],
            "landlord_cards_public": observation["landlord_cards_public"],
            "delay_seconds": self.settings.broadcast_delay_seconds,
        }

    def observation(self, agent_id: str) -> dict[str, Any]:
        match = self._active()
        try:
            seat = match.agent_ids.index(agent_id)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="agent is not seated") from exc
        observation = match.game.observation(seat)
        row = self.store.one("SELECT balance FROM agents WHERE id=?", (agent_id,)) or {"balance": 0}
        observation.update({"arena_token_balance": row["balance"],
                            "decision_timeout_ms": self.settings.agent_decision_timeout_ms})
        return observation

    async def act(self, agent_id: str, game_id: str, turn_id: str, action_id: int,
                  public_comment: str | None = None) -> dict[str, Any]:
        match = self._active()
        try:
            seat = match.agent_ids.index(agent_id)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="agent is not seated") from exc
        previous_phase = match.game.phase
        previous_multiplier = match.game.current_multiplier
        try:
            event = match.game.act(seat, game_id, turn_id, action_id)
        except InvalidAction as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        self.turn_started_at = time.monotonic()
        event_type = self._event_type(event)
        payload = {**event, "public_comment": public_comment, "current_multiplier": match.game.current_multiplier}
        await self.broadcast.append(event_type, payload, game_id=game_id, actor=agent_id)
        self.store.execute("UPDATE games SET status=?,multiplier=? WHERE id=?",
                           (match.game.phase.value.upper(), match.game.current_multiplier, game_id))
        if previous_phase is Phase.BIDDING and match.game.phase is Phase.PLAYING:
            landlord = match.game.landlord
            for index, player in enumerate(match.agent_ids):
                role = "landlord" if index == landlord else ("farmer_left" if index == (landlord + 1) % 3 else "farmer_right")
                self.store.execute("UPDATE game_players SET seat=? WHERE game_id=? AND agent_id=?", (role, game_id, player))
            await self.broadcast.append("LANDLORD", {"seat": landlord, "landlord_cards_public": match.game.bottom_cards}, game_id=game_id)
        if match.game.current_multiplier != previous_multiplier:
            await self.broadcast.append("MULTIPLIER", {"value": match.game.current_multiplier}, game_id=game_id)
        if match.game.is_over:
            await self._finish(match)
        await self.broadcast.append("TABLE_STATE", self.snapshot(), game_id=game_id)
        return {"accepted": True, "event": event, "game_over": match.game.is_over,
                "next_turn_id": match.game.turn_id if not match.game.is_over else None}

    async def fallback_current_turn(self, reason: str = "AGENT_TIMEOUT") -> dict[str, Any]:
        match = self._active()
        seat = match.game.current_player
        agent_id = match.agent_ids[seat]
        observation = match.game.observation(seat)
        legal = observation["legal_actions"]
        chosen = next((action for action in legal if action["id"] == 0), legal[0])
        await self.broadcast.append(reason, {"agent_id": agent_id, "fallback_action_id": chosen["id"]},
                                    game_id=match.game.game_id, actor=agent_id)
        return await self.act(agent_id, match.game.game_id, match.game.turn_id, chosen["id"])

    async def _finish(self, match: ActiveMatch) -> None:
        game = match.game
        assert game.landlord is not None and game.winner is not None
        landlord_id = match.agent_ids[game.landlord]
        farmer_ids = [agent_id for index, agent_id in enumerate(match.agent_ids) if index != game.landlord]
        deltas = self.tokens.settle(game.game_id, landlord_id, farmer_ids, game.winner == game.landlord,
                                    match.base_stake, game.current_multiplier)
        side = "landlord" if game.winner == game.landlord else "farmers"
        self.store.execute("UPDATE games SET status='FINISHED',winner_side=?,finished_at=? WHERE id=?",
                           (side, iso(), game.game_id))
        for agent_id, delta in deltas.items():
            self.store.execute("UPDATE game_players SET token_delta=? WHERE game_id=? AND agent_id=?",
                               (delta, game.game_id, agent_id))
            await self.broadcast.append("TOKEN_CHANGE", {"agent_id": agent_id, "delta": delta}, game_id=game.game_id)
        await self.broadcast.append("WIN", {"winner_side": side, "deltas": deltas}, game_id=game.game_id)
        await self.broadcast.append("HALL_UPDATE", {"entries": self.tokens.hall()}, game_id=game.game_id)
        for agent_id in match.agent_ids:
            balance = (self.store.one("SELECT balance FROM agents WHERE id=?", (agent_id,)) or {"balance": 0})["balance"]
            if balance <= 0:
                await self.broadcast.append("ELIMINATION", {"agent_id": agent_id}, game_id=game.game_id)
                continue
            stats = self.store.one(
                "SELECT current_win_streak FROM leaderboard_stats WHERE agent_id=?", (agent_id,)
            ) or {"current_win_streak": 0}
            if stats["current_win_streak"] >= self.settings.max_table_win_streak:
                await self.broadcast.append("RETIREMENT", {"agent_id": agent_id}, game_id=game.game_id)
                continue
            self.store.execute(
                "INSERT OR IGNORE INTO queue_entries(agent_id,joined_at,auto_play) VALUES(?,?,1)",
                (agent_id, iso()),
            )
            agent = self.public_agent(agent_id)
            await self.broadcast.append(
                "QUEUE_ENTER",
                {
                    "agent_id": agent_id,
                    "agent_name": agent.get("agent_name"),
                    "model_label": agent.get("model_label"),
                    "current_at": agent.get("balance"),
                    "pov_allowed": bool(agent.get("pov_allowed")),
                    "online": bool(agent.get("online")),
                    "is_house": bool(agent.get("is_house")),
                },
                game_id=game.game_id,
            )
        self.next_match_at = time.monotonic() + self.settings.next_match_delay_seconds

    async def restart_active(self, seed: int | None = None) -> dict[str, Any]:
        match = self._active()
        if match.game.is_over:
            raise HTTPException(status_code=409, detail="cannot restart a finished match")
        old_game_id = match.game.game_id
        self.store.execute(
            "UPDATE games SET status='ABORTED',finished_at=? WHERE id=?", (iso(), old_game_id)
        )
        game = Game(
            seed=seed,
            config=GameConfig(
                max_multiplier=self.settings.max_multiplier,
                base_stake=match.base_stake,
            ),
        )
        self.active = ActiveMatch(game=game, agent_ids=list(match.agent_ids), base_stake=match.base_stake)
        self.turn_started_at = time.monotonic()
        self.store.execute(
            "INSERT INTO games VALUES(?,?,?,?,?,?,?)",
            (game.game_id, "BIDDING", match.base_stake, 1, None, iso(), None),
        )
        for seat, agent_id in enumerate(match.agent_ids):
            self.store.execute(
                "INSERT INTO game_players VALUES(?,?,?,0)",
                (game.game_id, agent_id, f"seat_{seat}"),
            )
        await self.broadcast.append(
            "RESTART_HAND", {"previous_game_id": old_game_id}, game_id=game.game_id
        )
        await self.broadcast.append(
            "DEAL",
            {
                "players": [self.public_agent(agent_id) for agent_id in match.agent_ids],
                "base_stake": match.base_stake,
                "remaining_card_counts": [17, 17, 17],
            },
            game_id=game.game_id,
        )
        await self.broadcast.append("TABLE_STATE", self.snapshot(), game_id=game.game_id)
        return self.snapshot()

    @staticmethod
    def _event_type(event: dict[str, Any]) -> str:
        mapping = {"pass": "PASS", "bomb": "BOMB", "rocket": "ROCKET", "spring": "SPRING",
                   "win": "WIN", "bid": "BID"}
        return mapping.get(str(event.get("type")), "PLAY")

    def _active(self) -> ActiveMatch:
        if not self.active:
            raise HTTPException(status_code=404, detail="no active match")
        return self.active
