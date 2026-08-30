from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_landlord_mcp import bridge


def test_normalize_arena_url_rejects_credentials() -> None:
    with pytest.raises(bridge.ArenaError):
        bridge.normalize_arena_url("https://user:secret@example.com")


def test_normalize_arena_url_removes_trailing_slash() -> None:
    assert bridge.normalize_arena_url("https://arena.example/") == "https://arena.example"


def test_bridge_manager_starts_verified_binary_and_auto_queues(monkeypatch, tmp_path) -> None:
    fake_process = Mock(pid=4242)
    fake_process.poll.return_value = None
    popen = Mock(return_value=fake_process)
    responses = iter([{"status": "ok"}, {"code": "AL-TEST-CODE"}])
    monkeypatch.setattr(bridge, "_request_json", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(bridge, "download_bridge", lambda: tmp_path / "arena-bridge")
    monkeypatch.setattr(bridge, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(bridge.subprocess, "Popen", popen)
    monkeypatch.setattr(bridge.time, "sleep", lambda *_: None)

    manager = bridge.BridgeManager()
    result = manager.start("Test Agent", "codex", "https://arena.example", 200, True)

    command = popen.call_args.args[0]
    assert command[:3] == [str(tmp_path / "arena-bridge"), "join", "AL-TEST-CODE"]
    assert command[-1] == "--pov"
    assert result["queued"] is True
    assert result["pid"] == 4242
    manager.process = None
    manager.stop()


def test_bridge_manager_rejects_unknown_adapter() -> None:
    with pytest.raises(bridge.ArenaError, match="Unsupported adapter"):
        bridge.BridgeManager().start("Test Agent", "unsafe-shell")
