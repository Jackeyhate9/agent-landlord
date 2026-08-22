from server.app.config import Settings
from server.app.services import TokenService, iso
from server.app.store import Store


def service():
    store = Store(":memory:")
    settings = Settings(session_secret="test-secret-that-is-at-least-thirty-two")
    token = TokenService(store, settings)
    for index, balance in enumerate((10_000, 10_000, 10_000)):
        agent = f"agent_{index}"
        store.execute("INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (agent, f"key_{index}", agent, "Rule", "test", None, balance, 1, 500, 1, 1, 0, iso()))
        store.execute("INSERT INTO leaderboard_stats(agent_id,peak_at,current_at) VALUES(?,?,?)", (agent, balance, balance))
    return store, token


def test_safe_stake_accounts_for_possible_landlord_loss():
    assert TokenService.safe_base_stake([1000, 500, 200], [10_000, 10_000, 3_000], 8) == 100


def test_standard_settlement_is_zero_sum_and_ledgered():
    store, token = service()
    deltas = token.settle("game_1", "agent_0", ["agent_1", "agent_2"], True, 500, 4)
    assert deltas == {"agent_0": 4000, "agent_1": -2000, "agent_2": -2000}
    assert sum(deltas.values()) == 0
    rows = store.all("SELECT * FROM arena_token_ledger")
    assert len(rows) == 3
    assert sum(row["delta"] for row in rows) == 0
