"""Small deterministic demo/house agents. They only consume public observations."""

from __future__ import annotations

import random


class RandomAgent:
    def __init__(self, seed: int | None = None):
        self._random = random.Random(seed)

    def act(self, observation: dict) -> dict:
        action = self._random.choice(observation["legal_actions"])
        return {"game_id": observation["game_id"], "turn_id": observation["turn_id"], "action_id": action["id"]}


class RuleAgent:
    def act(self, observation: dict) -> dict:
        actions = observation["legal_actions"]
        if observation["phase"] == "bidding":
            action = max(actions, key=lambda item: item["bid"])
        else:
            playable = [a for a in actions if a["type"] not in ("pass", "bomb", "rocket")]
            action = min(playable or actions, key=lambda item: (len(item.get("cards", [])), item["id"]))
        return {"game_id": observation["game_id"], "turn_id": observation["turn_id"], "action_id": action["id"]}


class HouseAgent(RuleAgent):
    """Official fallback bot; intentionally transparent and credential-free."""

