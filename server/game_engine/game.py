"""Authoritative state machine for one three-player Dou Dizhu hand."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from ..protocol_constants import MAX_MULTIPLIER, MULTIPLIER_FACTOR

from .actions import generate_plays
from .cards import make_deck, sort_cards
from .patterns import CardPattern, InvalidAction, classify_cards


class Phase(str, Enum):
    BIDDING = "bidding"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass(frozen=True)
class GameConfig:
    max_multiplier: int = MAX_MULTIPLIER
    bomb_multiplier: int = MULTIPLIER_FACTOR
    rocket_multiplier: int = MULTIPLIER_FACTOR
    spring_multiplier: int = MULTIPLIER_FACTOR
    base_stake: int = 500

    def __post_init__(self):
        if self.max_multiplier < 1 or min(self.bomb_multiplier, self.rocket_multiplier, self.spring_multiplier) < 1:
            raise ValueError("multipliers must be positive")


class Game:
    """Public API: construct, call observation(seat), then act with echoed IDs."""

    def __init__(self, *, seed: int | None = None, config: GameConfig | None = None, starting_seat: int = 0):
        if starting_seat not in range(3):
            raise ValueError("starting_seat must be 0, 1, or 2")
        self.config = config or GameConfig()
        self._random = random.Random(seed)
        self.game_id = f"game_{self._random.getrandbits(64):016x}"
        deck = make_deck()
        self._random.shuffle(deck)
        self.hands = [sort_cards(deck[index * 17 : (index + 1) * 17]) for index in range(3)]
        self.bottom_cards = sort_cards(deck[51:])
        self.phase = Phase.BIDDING
        self.current_player = starting_seat
        self.starting_seat = starting_seat
        self.landlord: int | None = None
        self.winner: int | None = None
        self.current_multiplier = 1
        self._turn_number = 0
        self._bids: dict[int, int] = {}
        self._incumbent: CardPattern | None = None
        self._last_play_seat: int | None = None
        self._passes = 0
        self._nonpass_plays = [0, 0, 0]
        self.history: list[dict] = []

    @property
    def is_over(self) -> bool:
        return self.phase is Phase.FINISHED

    @property
    def turn_id(self) -> str:
        return f"{self.game_id}_turn_{self._turn_number}"

    def _actions(self) -> list[dict]:
        if self.phase is Phase.BIDDING:
            highest = max(self._bids.values(), default=0)
            bids = [0] + [bid for bid in range(1, 4) if bid > highest]
            return [{"id": 100 + bid, "type": "bid", "bid": bid, "cards": []} for bid in bids]
        if self.phase is Phase.PLAYING:
            plays = generate_plays(self.hands[self.current_player], self._incumbent)
            actions = []
            for action_id, cards in enumerate(plays, 1):
                pattern = classify_cards(cards)
                actions.append({"id": action_id, "type": pattern.kind, "cards": list(cards)})
            if self._incumbent is not None:
                actions.insert(0, {"id": 0, "type": "pass", "cards": []})
            return actions
        return []

    def observation(self, seat: int) -> dict:
        if seat not in range(3):
            raise InvalidAction("unknown seat")
        roles = self._roles()
        last_action = self.history[-1] if self.history else None
        return {
            "protocol_version": 1,
            "game_id": self.game_id,
            "turn_id": self.turn_id,
            "phase": self.phase.value,
            "seat": roles[seat],
            "seat_index": seat,
            "hand": list(self.hands[seat]),
            "landlord_cards_public": list(self.bottom_cards) if self.landlord is not None else [],
            "last_action": last_action,
            "action_history": list(self.history),
            "remaining_card_counts": {roles[index]: len(hand) for index, hand in enumerate(self.hands)},
            "legal_actions": self._actions() if seat == self.current_player and not self.is_over else [],
            "base_stake": self.config.base_stake,
            "current_multiplier": self.current_multiplier,
        }

    def _roles(self) -> list[str]:
        if self.landlord is None:
            return ["seat_0", "seat_1", "seat_2"]
        return ["landlord" if i == self.landlord else ("farmer_left" if i == (self.landlord + 1) % 3 else "farmer_right") for i in range(3)]

    def act(self, seat: int, game_id: str, turn_id: str, action_id: int) -> dict:
        if self.is_over:
            raise InvalidAction("game is already finished")
        if game_id != self.game_id:
            raise InvalidAction("game_id mismatch")
        if turn_id != self.turn_id:
            raise InvalidAction("stale or invalid turn_id")
        if seat != self.current_player:
            raise InvalidAction("action submitted out of turn")
        legal = {action["id"]: action for action in self._actions()}
        if not isinstance(action_id, int) or isinstance(action_id, bool) or action_id not in legal:
            raise InvalidAction("unknown or illegal action_id")
        action = legal[action_id]
        if self.phase is Phase.BIDDING:
            self._bid(seat, action["bid"])
        else:
            self._play(seat, action)
        self._turn_number += 1
        return dict(self.history[-1])

    def _bid(self, seat: int, bid: int):
        self._bids[seat] = bid
        self.history.append({"phase": "bidding", "seat": seat, "type": "bid", "bid": bid})
        if bid == 3 or len(self._bids) == 3:
            highest = max(self._bids.values(), default=0)
            self.landlord = max(self._bids, key=self._bids.get) if highest else self.starting_seat
            self.current_multiplier = max(1, highest)
            self.hands[self.landlord] = sort_cards(self.hands[self.landlord] + self.bottom_cards)
            self.phase = Phase.PLAYING
            self.current_player = self.landlord
            return
        self.current_player = (seat + 1) % 3

    def _play(self, seat: int, action: dict):
        if action["type"] == "pass":
            self._passes += 1
            self.history.append({"phase": "playing", "seat": seat, "type": "pass", "cards": []})
            self.current_player = (seat + 1) % 3
            if self._passes == 2:
                self._incumbent = None
                self._passes = 0
            return
        cards = action["cards"]
        for card in cards:
            try:
                self.hands[seat].remove(card)
            except ValueError as exc:
                raise InvalidAction("play contains a card absent from hand") from exc
        pattern = classify_cards(cards)
        self._incumbent = pattern
        self._last_play_seat = seat
        self._passes = 0
        self._nonpass_plays[seat] += 1
        self.history.append({"phase": "playing", "seat": seat, "type": pattern.kind, "cards": list(cards)})
        if pattern.kind in ("bomb", "rocket"):
            self._apply_multiplier(pattern.kind)
        if not self.hands[seat]:
            self.winner = seat
            if self._is_spring():
                self._apply_multiplier("spring")
                self.history.append({"phase": "finished", "seat": seat, "type": "spring", "cards": []})
            self.phase = Phase.FINISHED
            self.history.append({"phase": "finished", "seat": seat, "type": "win", "cards": []})
        else:
            self.current_player = (seat + 1) % 3

    def _is_spring(self) -> bool:
        if self.landlord is None or self.winner is None:
            return False
        if self.winner == self.landlord:
            return all(self._nonpass_plays[seat] == 0 for seat in range(3) if seat != self.landlord)
        return self._nonpass_plays[self.landlord] == 1

    def _apply_multiplier(self, reason: str):
        factor = {
            "bomb": self.config.bomb_multiplier,
            "rocket": self.config.rocket_multiplier,
            "spring": self.config.spring_multiplier,
        }[reason]
        self.current_multiplier = min(self.config.max_multiplier, self.current_multiplier * factor)
