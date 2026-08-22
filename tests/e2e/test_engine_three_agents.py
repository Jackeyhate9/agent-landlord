from server.game_engine import Game, HouseAgent, Phase, RandomAgent, RuleAgent


def test_three_agents_finish_a_seeded_full_game():
    game = Game(seed=20260822)
    agents = [RandomAgent(1), RuleAgent(), HouseAgent()]
    turns = 0
    while not game.is_over:
        seat = game.current_player
        observation = game.observation(seat)
        result = agents[seat].act(observation)
        game.act(seat, result["game_id"], result["turn_id"], result["action_id"])
        turns += 1
        assert turns < 1000
    assert game.phase is Phase.FINISHED
    assert game.winner in (0, 1, 2)
    assert len(game.hands[game.winner]) == 0
    assert game.landlord is not None
    assert any(event["phase"] == "playing" for event in game.history)


def test_multiple_deals_never_deadlock_or_run_out_of_legal_actions():
    for seed in range(20):
        game = Game(seed=seed)
        agents = [RandomAgent(seed), RuleAgent(), HouseAgent()]
        for _ in range(999):
            if game.is_over:
                break
            seat = game.current_player
            observation = game.observation(seat)
            assert observation["legal_actions"]
            result = agents[seat].act(observation)
            game.act(seat, result["game_id"], result["turn_id"], result["action_id"])
        assert game.is_over, f"seed {seed} did not finish"
