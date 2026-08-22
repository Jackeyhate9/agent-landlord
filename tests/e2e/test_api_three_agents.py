from fastapi.testclient import TestClient

from server.app.config import Settings
from server.app.main import create_app


CERTS = ["connection", "heartbeat", "observation_parse", "valid_action", "timeout_behavior", "three_turns"]


def register(client: TestClient, index: int) -> tuple[str, str]:
    code = client.post("/api/join-codes").json()["code"]
    joined = client.post("/api/bridge/join", json={
        "code": code,
        "owner_public_key": f"ed25519:key-{index}-" + "x" * 40,
    }).json()
    headers = {"Authorization": f"Bearer {joined['session_token']}"}
    client.post("/api/agents/me/configure", headers=headers, json={
        "agent_name": f"Agent {index}", "model_label": "Rule", "runtime_label": "E2E HTTP",
        "max_stake": 500, "pov_allowed": index == 0,
    }).raise_for_status()
    client.post("/api/agents/me/certify", headers=headers, json={"passed_tests": CERTS}).raise_for_status()
    client.post("/api/queue", headers=headers).raise_for_status()
    return joined["agent_id"], joined["session_token"]


def test_three_external_agent_sessions_complete_a_match_through_api():
    settings = Settings(sqlite_path=":memory:", session_secret="test-secret-that-is-at-least-thirty-two",
                        broadcast_delay_seconds=0, admin_password="admin")
    with TestClient(create_app(settings)) as client:
        agents = [register(client, index) for index in range(3)]
        admin_token = client.post("/api/admin/login", json={"password": "admin"}).json()["token"]
        started = client.post("/api/admin/start-next-match", headers={"Authorization": f"Bearer {admin_token}"})
        assert started.status_code == 200
        game_id = started.json()["game_id"]
        turns = 0
        while turns < 500:
            progressed = False
            for _, token in agents:
                headers = {"Authorization": f"Bearer {token}"}
                observation = client.get("/api/agents/me/observation", headers=headers).json()
                if observation.get("legal_actions"):
                    legal = observation["legal_actions"]
                    # Bid 3 to start promptly; play the first non-pass option thereafter.
                    chosen = next((action for action in legal if action.get("bid") == 3),
                                  next((action for action in legal if action["id"] != 0), legal[0]))
                    response = client.post("/api/agents/me/action", headers=headers, json={
                        "protocol_version": 1, "game_id": observation["game_id"],
                        "turn_id": observation["turn_id"], "action_id": chosen["id"],
                    })
                    assert response.status_code == 200, response.text
                    turns += 1
                    progressed = True
                    if response.json()["game_over"]:
                        progressed = False
                        break
            if not progressed:
                break
        replay = client.get(f"/api/games/{game_id}").json()
        assert replay["status"] == "FINISHED"
        assert sum(player["token_delta"] for player in replay["players"]) == 0
        ledger = client.app.state.arena.store.all("SELECT * FROM arena_token_ledger WHERE game_id=?", (game_id,))
        assert len(ledger) == 3 and sum(row["delta"] for row in ledger) == 0
        event_types = {row["type"] for row in client.app.state.arena.store.all("SELECT * FROM game_events WHERE game_id=?", (game_id,))}
        assert {"DEAL", "LANDLORD", "WIN", "TOKEN_CHANGE"}.issubset(event_types)
