from __future__ import annotations

import atexit
import hashlib
import json
import os
import platform
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_ARENA_URL = "https://api.thbianhua.cn"
RELEASE_BASE = "https://github.com/Jackeyhate9/agent-landlord/releases/latest/download"
SUPPORTED_ADAPTERS = {"codex", "claude-code", "ollama", "openai-compatible", "custom-http", "custom-cli"}
SUPPORTED_STAKES = {100, 200, 500, 1000}


class ArenaError(RuntimeError):
    """A recoverable Agent Landlord integration error."""


def _cache_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "agent-landlord"


def _asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows" and machine in {"amd64", "x86_64"}:
        return "arena-bridge-windows.exe"
    if system == "linux" and machine in {"amd64", "x86_64"}:
        return "arena-bridge-linux"
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "arena-bridge-macos"
    raise ArenaError(f"Unsupported platform: {platform.system()} {platform.machine()}")


def _request_json(url: str, method: str = "GET", timeout: float = 12) -> Any:
    request = urllib.request.Request(url, method=method, headers={"Accept": "application/json", "User-Agent": "agent-landlord-mcp/0.1.7"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ArenaError(f"Arena request failed: {url}: {exc}") from exc


def normalize_arena_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ArenaError("Arena URL must be an http(s) origin without embedded credentials")
    return value


def download_bridge(force: bool = False) -> Path:
    override = os.environ.get("AGENT_LANDLORD_BRIDGE")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise ArenaError(f"AGENT_LANDLORD_BRIDGE does not exist: {path}")
        return path

    asset = _asset_name()
    cache = _cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / asset
    if target.is_file() and not force:
        return target

    checksum_url = f"{RELEASE_BASE}/{asset}.sha256"
    binary_url = f"{RELEASE_BASE}/{asset}"
    try:
        with urllib.request.urlopen(checksum_url, timeout=30) as response:
            expected = response.read().decode("ascii").split()[0].lower()
        with urllib.request.urlopen(binary_url, timeout=90) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, IndexError, UnicodeDecodeError) as exc:
        raise ArenaError(f"Could not download Bridge release: {exc}") from exc

    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ArenaError("Bridge checksum verification failed")
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(target)
    if os.name != "nt":
        target.chmod(0o755)
    return target


class BridgeManager:
    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.log_path: Path | None = None
        self._log_handle = None
        atexit.register(self.stop)

    def start(
        self,
        agent_name: str,
        adapter: str = "codex",
        arena_url: str = DEFAULT_ARENA_URL,
        max_stake: int = 100,
        pov: bool = False,
    ) -> dict[str, Any]:
        if self.process and self.process.poll() is None:
            raise ArenaError(f"A Bridge is already running with PID {self.process.pid}")
        if adapter not in SUPPORTED_ADAPTERS:
            raise ArenaError(f"Unsupported adapter: {adapter}")
        if max_stake not in SUPPORTED_STAKES:
            raise ArenaError("max_stake must be one of 100, 200, 500, 1000")
        agent_name = agent_name.strip()
        if not agent_name or len(agent_name) > 48:
            raise ArenaError("agent_name must contain 1 to 48 characters")

        origin = normalize_arena_url(arena_url)
        ready = _request_json(f"{origin}/ready")
        if ready.get("status") != "ok":
            raise ArenaError("Arena is not ready")
        join = _request_json(f"{origin}/api/join-codes", method="POST")
        code = join.get("code")
        if not isinstance(code, str):
            raise ArenaError("Arena returned an invalid join code")

        bridge = download_bridge()
        cache = _cache_dir()
        self.log_path = cache / "bridge.log"
        self._log_handle = self.log_path.open("ab", buffering=0)
        command = [
            str(bridge), "join", code, "--server", origin, "--adapter", adapter,
            "--name", agent_name, "--max-stake", str(max_stake),
        ]
        if pov:
            command.append("--pov")
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=creation_flags,
        )
        time.sleep(1)
        if self.process.poll() is not None:
            detail = self.log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
            self.stop()
            raise ArenaError(f"Bridge exited during startup: {detail}")
        return {
            "connected": True,
            "queued": True,
            "pid": self.process.pid,
            "agent_name": agent_name,
            "adapter": adapter,
            "arena_url": origin,
            "join_code": code,
            "log_path": str(self.log_path),
        }

    def stop(self) -> dict[str, Any]:
        process = self.process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        pid = process.pid if process else None
        self.process = None
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None
        return {"stopped": pid is not None, "pid": pid}

    def status(self, arena_url: str = DEFAULT_ARENA_URL) -> dict[str, Any]:
        origin = normalize_arena_url(arena_url)
        ready = _request_json(f"{origin}/ready")
        queue = _request_json(f"{origin}/api/public/queue")
        running = bool(self.process and self.process.poll() is None)
        return {"arena_url": origin, "ready": ready, "queue": queue, "local_bridge_running": running, "pid": self.process.pid if running else None}


manager = BridgeManager()
