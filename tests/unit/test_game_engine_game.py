import pytest

from server.game_engine import Game, GameConfig, InvalidAction, Phase, RandomAgent


def finish_bidding(game, bids=(1, 0, 0)):
    for bid in bids:
        obs = game.observation(game.current_player)
        game.act(
            seat=game.current_player,
            game_id=obs["game_id"],
            turn_id=obs["turn_id"],
            action_id=next(a["id"] for a in obs["legal_actions"] if a.get("bid") == bid),
        )


def test_standard_deal_and_observation_hide_opponents():
    game = Game(seed=41)
    assert sorted(map(len, game.hands)) == [17, 17, 17]
    assert len(game.bottom_cards) == 3
    all_cards = [c for hand in game.hands for c in hand] + game.bottom_cards
    assert len(all_cards) == len(set(all_cards)) == 54
    obs = game.observation(0)
    assert len(obs["hand"]) == 17
    assert "hands" not in obs and "bottom_cards" not in obs
    assert obs["landlord_cards_public"] == []


def test_bidding_assigns_landlord_and_adds_bottom_cards():
    game = Game(seed=2)
    finish_bidding(game, (1, 3))
    assert game.phase is Phase.PLAYING
    assert game.landlord == 1
    assert len(game.hands[1]) == 20
    assert game.current_multiplier == 3
    assert game.observation(0)["landlord_cards_public"] == game.bottom_cards


def test_pass_only_when_following_and_ids_are_strictly_validated():
    game = Game(seed=8)
    finish_bidding(game)
    obs = game.observation(game.current_player)
    assert all(a["type"] != "pass" for a in obs["legal_actions"])
    with pytest.raises(InvalidAction):
        game.act(game.current_player, "wrong", obs["turn_id"], obs["legal_actions"][0]["id"])
    with pytest.raises(InvalidAction):
        game.act((game.current_player + 1) % 3, game.game_id, obs["turn_id"], obs["legal_actions"][0]["id"])
    action = obs["legal_actions"][0]
    game.act(game.current_player, game.game_id, obs["turn_id"], action["id"])
    follower = game.observation(game.current_player)
    assert any(a["type"] == "pass" for a in follower["legal_actions"])
    with pytest.raises(InvalidAction):
        game.act(game.current_player, game.game_id, obs["turn_id"], follower["legal_actions"][0]["id"])
    with pytest.raises(InvalidAction):
        game.act(game.current_player, game.game_id, follower["turn_id"], 999999)


def test_bomb_rocket_and_spring_multiplier_cap():
    game = Game(config=GameConfig(max_multiplier=8), seed=4)
    game.current_multiplier = 4
    game._apply_multiplier("bomb")
    assert game.current_multiplier == 8
    game._apply_multiplier("rocket")
    game._apply_multiplier("spring")
    assert game.current_multiplier == 8


def test_seed_reproducibly_completes_with_random_agents():
    def run():
        game = Game(seed=123)
        agents = [RandomAgent(10), RandomAgent(11), RandomAgent(12)]
        steps = 0
        while not game.is_over:
            seat = game.current_player
            obs = game.observation(seat)
            response = agents[seat].act(obs)
            game.act(seat, response["game_id"], response["turn_id"], response["action_id"])
            steps += 1
            assert steps < 1000
        return game.winner, game.current_multiplier, game.history
    assert run() == run()
