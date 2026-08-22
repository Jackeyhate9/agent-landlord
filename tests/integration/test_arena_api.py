import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from server.app.config import Settings
from server.app.main import create_app


def client(delay: float = 0) -> TestClient:
    settings = Settings(sqlite_path=":memory:", session_secret="test-secret-that-is-at-least-thirty-two", broadcast_delay_seconds=delay,
                        admin_password="test-admin")
    return TestClient(create_app(settings))


def register(test_client: TestClient, key: str = "ed25519:" + "a" * 48):
    code = test_client.post("/api/join-codes").json()["code"]
    response = test_client.post("/api/bridge/join", json={"code": code, "owner_public_key": key})
    assert response.status_code == 200
    return response.json()


def test_join_code_is_single_use_and_initial_grant_is_idempotent():
    with client() as test_client:
        created = test_client.post("/api/join-codes").json()
        assert created["code"].startswith("AL-")
        body = {"code": created["code"], "owner_public_key": "ed25519:" + "b" * 48}
        first = test_client.post("/api/bridge/join", json=body)
        assert first.status_code == 200 and first.json()["initial_grant"] is True
        assert test_client.post("/api/bridge/join", json=body).status_code == 410
        next_code = test_client.post("/api/join-codes").json()["code"]
        second = test_client.post("/api/bridge/join", json={**body, "code": next_code})
        assert second.json()["initial_grant"] is False
        ledger = test_client.app.state.arena.store.all("SELECT * FROM arena_token_ledger")
        assert len(ledger) == 1 and ledger[0]["type"] == "INITIAL_GRANT"


def test_bridge_v1_join_verifies_ed25519_and_returns_ws_contract():
    with client() as test_client:
        code = test_client.post("/api/join-codes").json()["code"]
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes_raw()
        encode = lambda value: base64.urlsafe_b64encode(value).rstrip(b"=").decode()
        payload = {"protocol_version": 1, "join_code": code, "public_key": encode(public),
                   "signature": encode(private.sign(code.encode())), "adapter": "custom-http"}
        response = test_client.post("/api/agent/join", json=payload)
        assert response.status_code == 200, response.text
        session = response.json()
        assert session["websocket_url"].endswith("/ws/agent")
        assert session["session_token"] and session["resume_id"]


def test_bridge_v1_rejects_forged_signature_without_consuming_code():
    with client() as test_client:
        code = test_client.post("/api/join-codes").json()["code"]
        private = Ed25519PrivateKey.generate()
        other = Ed25519PrivateKey.generate()
        encode = lambda value: base64.urlsafe_b64encode(value).rstrip(b"=").decode()
        payload = {"protocol_version": 1, "join_code": code,
                   "public_key": encode(private.public_key().public_bytes_raw()),
                   "signature": encode(other.sign(code.encode())), "adapter": "custom-cli"}
        assert test_client.post("/api/agent/join", json=payload).status_code == 401
        payload["signature"] = encode(private.sign(code.encode()))
        assert test_client.post("/api/agent/join", json=payload).status_code == 200


def test_certification_gates_queue_and_public_view_hides_keys():
    with client() as test_client:
        joined = register(test_client)
        auth = {"Authorization": f"Bearer {joined['session_token']}"}
        assert test_client.post("/api/queue", headers=auth).status_code == 403
        config = {"agent_name": "CatBot", "model_label": "Claude", "runtime_label": "Custom CLI",
                  "max_stake": 500, "pov_allowed": True}
        assert test_client.post("/api/agents/me/configure", headers=auth, json=config).status_code == 200
        tests = ["connection", "heartbeat", "observation_parse", "valid_action", "timeout_behavior", "three_turns"]
        assert test_client.post("/api/agents/me/certify", headers=auth, json={"passed_tests": tests}).status_code == 200
        assert test_client.post("/api/queue", headers=auth).status_code == 200
        queue = test_client.get("/api/public/queue").json()
        assert queue[0]["agent_name"] == "CatBot"
        assert "owner_public_key" not in queue[0] and "session_token" not in queue[0]


def test_public_events_obey_server_delay():
    with client(delay=60) as test_client:
        joined = register(test_client)
        auth = {"Authorization": f"Bearer {joined['session_token']}"}
        test_client.post("/api/agents/me/configure", headers=auth, json={
            "agent_name": "Delayed", "model_label": "Rule", "runtime_label": "test",
            "max_stake": 100, "pov_allowed": True,
        })
        tests = ["connection", "heartbeat", "observation_parse", "valid_action", "timeout_behavior", "three_turns"]
        test_client.post("/api/agents/me/certify", headers=auth, json={"passed_tests": tests})
        test_client.post("/api/queue", headers=auth)
        assert test_client.get("/api/public/events").json() == []
        assert test_client.get("/api/public/queue").json() == []
        assert test_client.get("/api/public/hall").json() == []
        assert test_client.get("/api/public/table").json()["status"] == "IDLE"
        stored = test_client.app.state.arena.store.one("SELECT * FROM game_events")
        assert stored["broadcast_at"] > stored["created_at"]


def test_admin_adjustment_is_audited_and_cannot_make_balance_negative():
    with client() as test_client:
        joined = register(test_client)
        admin = test_client.post("/api/admin/login", json={"password": "test-admin"}).json()["token"]
        headers = {"Authorization": f"Bearer {admin}"}
        body = {"agent_id": joined["agent_id"], "operation": "subtract", "amount": 100, "reason": "tournament ruling"}
        response = test_client.post("/api/admin/tokens", headers=headers, json=body)
        assert response.json() == {"before": 10000, "after": 9900}
        assert len(test_client.app.state.arena.store.all("SELECT * FROM admin_audit_logs")) == 1
        body["amount"] = 20_000
        assert test_client.post("/api/admin/tokens", headers=headers, json=body).status_code == 422
