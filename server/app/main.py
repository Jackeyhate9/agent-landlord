import asyncio
import base64
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .config import Settings, get_settings
from .schemas import (
    AdminLogin,
    AgentConfigure,
    BridgeActivation,
    BridgeJoin,
    BridgeJoinV1,
    CertificationResult,
    HealthView,
    JoinCodeView,
    JoinStatusView,
    TokenAdjustment,
)
from .security import require_admin, require_agent, sign_token, verify_token
from .services import ArenaService, BroadcastService, JoinService, TokenService
from .store import Store
from .matches import MatchService


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = Store(settings.sqlite_path, settings.postgres_url)
        self.join = JoinService(self.store, settings)
        self.arena = ArenaService(self.store, settings)
        self.tokens = TokenService(self.store, settings)
        self.broadcast = BroadcastService(self.store, settings)
        self.matches = MatchService(self.store, settings, self.arena, self.tokens, self.broadcast)
        self.paused = False


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    config.validate_production_secrets()

    async def supervise(arena: AppState) -> None:
        while True:
            await asyncio.sleep(0.25)
            if arena.paused:
                continue
            try:
                if arena.matches.turn_expired():
                    await arena.matches.fallback_current_turn()
                elif config.auto_start_matches and arena.matches.can_start():
                    await arena.matches.start_next()
            except (HTTPException, ValueError):
                # Queue contents can change between the readiness check and transition.
                continue

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.arena = AppState(config)
        supervisor = asyncio.create_task(supervise(app.state.arena))
        try:
            yield
        finally:
            supervisor.cancel()
            with suppress(asyncio.CancelledError):
                await supervisor

    allowed_origins = [o.strip() for o in config.public_api_url.split(",") if o.strip()] if config.public_api_url else ["*"]
    app = FastAPI(title="Agent Landlord API", version="0.1.7", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    requests: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def limits(request: Request, call_next):
        # Read actual body size to handle chunked encoding; fall back to header.
        body = b""
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            if len(body) > config.max_payload_bytes:
                return __import__("fastapi").responses.JSONResponse({"detail": "payload too large"}, status_code=413)
            # Re-inject body so downstream handlers can read it again
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request._receive = receive  # type: ignore[attr-defined]
        elif int(request.headers.get("content-length", "0") or 0) > config.max_payload_bytes:
            return __import__("fastapi").responses.JSONResponse({"detail": "payload too large"}, status_code=413)
        # Prefer X-Forwarded-For when behind Cloudflare/proxy, else client host
        forwarded = request.headers.get("x-forwarded-for", "")
        client = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        bucket = requests[client]
        cutoff = time.monotonic() - 60
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= config.rate_limit_per_minute:
            return __import__("fastapi").responses.JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        bucket.append(time.monotonic())
        return await call_next(request)

    def state(request: Request) -> AppState:
        return request.app.state.arena

    @app.get("/health", response_model=HealthView)
    def health() -> HealthView:
        return HealthView(status="ok", checks={"api": "ok", "game_engine": "ok"})

    @app.get("/ready", response_model=HealthView)
    def ready(arena: Annotated[AppState, Depends(state)]) -> HealthView:
        arena.store.one("SELECT 1 AS ok")
        return HealthView(status="ok", checks={"database": "ok", "broadcast": "ok", "game_engine": "ok"})

    @app.post("/api/join-codes", response_model=JoinCodeView)
    def create_join_code(arena: Annotated[AppState, Depends(state)]) -> JoinCodeView:
        code, expires = arena.join.create_code()
        return JoinCodeView(code=code, expires_at=expires)

    @app.get("/api/join-codes/{code}", response_model=JoinStatusView)
    def join_status(code: str, arena: Annotated[AppState, Depends(state)]) -> JoinStatusView:
        return JoinStatusView(**arena.join.pairing_status(code))

    @app.post("/api/bridge/join")
    async def bridge_join(body: BridgeJoin, arena: Annotated[AppState, Depends(state)]):
        result = arena.join.redeem(body.code, body.owner_public_key)
        await arena.broadcast.append("AGENT_JOIN", {"agent_id": result["agent_id"]})
        return result

    @app.post("/api/agent/join")
    async def bridge_join_v1(body: BridgeJoinV1, request: Request,
                             arena: Annotated[AppState, Depends(state)]):
        def decode(value: str) -> bytes:
            return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

        try:
            public_key = decode(body.public_key)
            signature = decode(body.signature)
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, body.join_code.encode())
        except (ValueError, InvalidSignature) as exc:
            raise HTTPException(status_code=401, detail="invalid Ed25519 join signature") from exc
        result = arena.join.redeem(body.join_code, body.public_key,
                                   detected_runtime=body.detected_runtime,
                                   detected_model=body.detected_model)
        scheme = "wss" if request.url.scheme == "https" else "ws"
        websocket_url = f"{scheme}://{request.url.netloc}/ws/agent"
        await arena.broadcast.append("AGENT_JOIN", {"agent_id": result["agent_id"], "adapter": body.adapter})
        return {"agent_id": result["agent_id"], "session_token": result["session_token"],
                "resume_id": result["session_id"], "websocket_url": websocket_url}

    @app.post("/api/agents/me/configure")
    def configure(body: AgentConfigure, agent_id: Annotated[str, Depends(require_agent)],
                  arena: Annotated[AppState, Depends(state)]):
        values = body.model_dump(mode="json")
        return arena.arena.configure(agent_id, values)

    @app.post("/api/agents/me/activate")
    async def activate(body: BridgeActivation, agent_id: Annotated[str, Depends(require_agent)],
                       arena: Annotated[AppState, Depends(state)]):
        already_queued = arena.store.one(
            "SELECT agent_id FROM queue_entries WHERE agent_id=?", (agent_id,)
        )
        agent = arena.arena.activate(agent_id, body.model_dump(mode="json"))
        if body.auto_queue and not already_queued:
            await arena.broadcast.append("QUEUE_ENTER", {
                "agent_id": agent_id,
                "agent_name": agent.get("agent_name", "Agent"),
                "model_label": agent.get("model_label", "Custom"),
                "current_at": agent.get("balance", 0),
                "pov_allowed": bool(agent.get("pov_allowed")),
                "online": bool(agent.get("online")),
                "is_house": bool(agent.get("is_house")),
            })
        return {"activated": True, "certified": True, "queued": bool(body.auto_queue)}

    @app.post("/api/agents/me/certify")
    def certify(body: CertificationResult, agent_id: Annotated[str, Depends(require_agent)],
                arena: Annotated[AppState, Depends(state)]):
        arena.arena.certify(agent_id, body.passed_tests)
        return {"certified": True, "label": "AGENT CERTIFIED"}

    @app.post("/api/agents/me/heartbeat")
    def agent_heartbeat(agent_id: Annotated[str, Depends(require_agent)],
                        arena: Annotated[AppState, Depends(state)]):
        arena.arena.heartbeat(agent_id)
        return {"online": True}

    @app.post("/api/queue")
    async def join_queue(agent_id: Annotated[str, Depends(require_agent)],
                         arena: Annotated[AppState, Depends(state)]):
        arena.arena.join_queue(agent_id)
        agent = arena.store.one("SELECT * FROM agents WHERE id=?", (agent_id,)) or {}
        await arena.broadcast.append("QUEUE_ENTER", {
            "agent_id": agent_id, "agent_name": agent.get("agent_name", "Agent"),
            "model_label": agent.get("model_label", "Custom"), "current_at": agent.get("balance", 0),
            "pov_allowed": bool(agent.get("pov_allowed")), "online": bool(agent.get("online")),
            "is_house": bool(agent.get("is_house")),
        })
        return {"queued": True, "auto_play": True}

    @app.delete("/api/queue")
    async def leave_queue(agent_id: Annotated[str, Depends(require_agent)],
                          arena: Annotated[AppState, Depends(state)]):
        arena.arena.leave_queue(agent_id)
        await arena.broadcast.append("QUEUE_EXIT", {"agent_id": agent_id})
        return {"queued": False}

    @app.get("/api/public/queue")
    def public_queue(arena: Annotated[AppState, Depends(state)]):
        return arena.broadcast.queue_projection()

    @app.get("/api/public/hall")
    def public_hall(arena: Annotated[AppState, Depends(state)]):
        return arena.broadcast.hall_projection()

    @app.get("/api/public/events")
    def public_events(arena: Annotated[AppState, Depends(state)], after: int = 0):
        return arena.broadcast.due(after)

    @app.get("/api/public/table")
    def public_table(arena: Annotated[AppState, Depends(state)]):
        return arena.broadcast.table_projection()

    @app.get("/api/agents/me/observation")
    def agent_observation(agent_id: Annotated[str, Depends(require_agent)],
                          arena: Annotated[AppState, Depends(state)]):
        return arena.matches.observation(agent_id)

    @app.post("/api/agents/me/action")
    async def agent_action(body: dict, agent_id: Annotated[str, Depends(require_agent)],
                           arena: Annotated[AppState, Depends(state)]):
        required = {"protocol_version", "game_id", "turn_id", "action_id"}
        if not required.issubset(body) or body.get("protocol_version") != 1:
            raise HTTPException(status_code=422, detail="invalid protocol response")
        comment = body.get("public_comment")
        if comment is not None and (not isinstance(comment, str) or len(comment) > 160):
            raise HTTPException(status_code=422, detail="public_comment must be at most 160 characters")
        return await arena.matches.act(agent_id, body["game_id"], body["turn_id"], body["action_id"], comment)

    @app.get("/api/games/{game_id}")
    def game(game_id: str, arena: Annotated[AppState, Depends(state)]):
        found = arena.store.one("SELECT * FROM games WHERE id=?", (game_id,))
        if not found:
            raise HTTPException(status_code=404, detail="game not found")
        found["players"] = arena.store.all("SELECT * FROM game_players WHERE game_id=?", (game_id,))
        return found

    @app.get("/api/games/{game_id}/events")
    def game_events(game_id: str, arena: Annotated[AppState, Depends(state)]):
        return arena.store.all("SELECT * FROM game_events WHERE game_id=? ORDER BY sequence", (game_id,))

    @app.post("/api/admin/login")
    def admin_login(body: AdminLogin):
        if not secrets.compare_digest(body.password, config.admin_password):
            raise HTTPException(status_code=401, detail="invalid admin password")
        return {"token": sign_token("local-admin", "admin", ttl_seconds=8 * 3600)}

    @app.post("/api/admin/tokens")
    async def adjust_tokens(body: TokenAdjustment, admin: Annotated[str, Depends(require_admin)],
                            arena: Annotated[AppState, Depends(state)]):
        result = arena.tokens.adjust(admin, body.agent_id, body.operation, body.amount, body.reason)
        await arena.broadcast.append("TOKEN_CHANGE", {"agent_id": body.agent_id, **result})
        return result

    @app.post("/api/admin/{operation}")
    async def admin_operation(operation: str, request: Request,
                              admin: Annotated[str, Depends(require_admin)],
                              arena: Annotated[AppState, Depends(state)]):
        allowed = {"pause", "resume", "force-next-turn", "restart-hand", "start-next-match",
                   "house-in", "house-out", "set-live-pov", "disqualify-agent", "remove-from-queue"}
        if operation not in allowed:
            raise HTTPException(status_code=404, detail="unknown operation")
        try:
            body = await request.json()
        except Exception:
            body = {}
        agent_id = body.get("agent_id") if isinstance(body, dict) else None
        if operation == "pause":
            arena.paused = True
        elif operation == "resume":
            arena.paused = False
        elif operation == "start-next-match":
            return await arena.matches.start_next()
        elif operation == "force-next-turn":
            return await arena.matches.fallback_current_turn("ADMIN_FORCE_NEXT_TURN")
        elif operation == "restart-hand":
            return await arena.matches.restart_active()
        elif operation == "set-live-pov":
            if not agent_id:
                raise HTTPException(status_code=422, detail="agent_id required")
            arena.store.execute("UPDATE agents SET pov_allowed=0")
            arena.store.execute("UPDATE agents SET pov_allowed=1 WHERE id=?", (agent_id,))
        elif operation == "disqualify-agent":
            if not agent_id:
                raise HTTPException(status_code=422, detail="agent_id required")
            arena.arena.leave_queue(agent_id)
            arena.store.execute("UPDATE agents SET certified=0,online=0 WHERE id=?", (agent_id,))
        elif operation == "remove-from-queue":
            if not agent_id:
                raise HTTPException(status_code=422, detail="agent_id required")
            arena.arena.leave_queue(agent_id)
        elif operation in {"house-in", "house-out"}:
            if not agent_id:
                raise HTTPException(status_code=422, detail="agent_id required")
            arena.store.execute(
                "UPDATE agents SET is_house=? WHERE id=?",
                (int(operation == "house-in"), agent_id),
            )
        arena.store.execute("INSERT INTO admin_audit_logs VALUES(?,?,?,?,?,?,?)",
                            (__import__("server.app.security", fromlist=["opaque_id"]).opaque_id("audit"), admin,
                             agent_id or "system", 0, 0, operation,
                             __import__("server.app.services", fromlist=["iso"]).iso()))
        await arena.broadcast.append(
            operation.replace("-", "_").upper(), {"admin": admin, "agent_id": agent_id}
        )
        return {"ok": True, "paused": arena.paused}

    @app.post("/api/admin/sound/{sound}")
    async def sound(sound: str, admin: Annotated[str, Depends(require_admin)],
                    arena: Annotated[AppState, Depends(state)]):
        allowed = {"deal", "bomb", "rocket", "victory", "elimination", "challenger", "suspense", "hall_of_fame"}
        if sound not in allowed:
            raise HTTPException(status_code=422, detail="unsupported sound")
        await arena.broadcast.append("SOUND", {"sound": sound}, actor=admin)
        return {"triggered": sound}

    @app.websocket("/ws/public")
    async def public_ws(websocket: WebSocket):
        await websocket.accept()
        sequence = int(websocket.query_params.get("after", "0"))
        try:
            while True:
                events = await websocket.app.state.arena.broadcast.wait_for_due(sequence)
                for event in events:
                    await websocket.send_json(event.model_dump(mode="json"))
                    sequence = event.sequence
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                    if message == "ping":
                        await websocket.send_text("pong")
                except TimeoutError:
                    pass
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/agent")
    async def agent_ws(websocket: WebSocket):
        authorization = websocket.headers.get("authorization", "")
        token = authorization[7:] if authorization.startswith("Bearer ") else websocket.query_params.get("token", "")
        try:
            agent_id = str(verify_token(token, "agent")["sub"])
        except HTTPException:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        arena: AppState = websocket.app.state.arena
        arena.arena.heartbeat(agent_id)
        try:
            hello = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        except (TimeoutError, WebSocketDisconnect):
            await websocket.close(code=4408)
            return
        if hello.get("type") not in {"hello", "resume"} or hello.get("protocol_version") not in {None, 1}:
            await websocket.send_json({"type": "error", "message": "invalid hello envelope"})
            await websocket.close(code=4400)
            return
        await websocket.send_json({"type": "session", "protocol_version": 1,
                                   "resume_id": hello.get("resume_id") or f"resume_{agent_id}"})
        sent_turn: str | None = None
        try:
            while True:
                try:
                    observation = arena.matches.observation(agent_id)
                    if observation.get("legal_actions") and observation["turn_id"] != sent_turn:
                        await websocket.send_json({"type": "observation", "protocol_version": 1,
                                                   "observation": observation})
                        sent_turn = observation["turn_id"]
                except HTTPException:
                    pass
                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                except TimeoutError:
                    continue
                if message.get("type") in {"heartbeat", "ping"}:
                    arena.arena.heartbeat(agent_id)
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "action" and isinstance(message.get("action"), dict):
                    action = message["action"]
                    try:
                        await arena.matches.act(agent_id, action.get("game_id", ""), action.get("turn_id", ""),
                                                action.get("action_id"), action.get("public_comment"))
                    except HTTPException as exc:
                        await websocket.send_json({"type": "error", "message": str(exc.detail)})
                else:
                    await websocket.send_json({"type": "error", "message": "unsupported envelope"})
        except WebSocketDisconnect:
            arena.store.execute("UPDATE agents SET online=0 WHERE id=?", (agent_id,))
            arena.arena.leave_queue(agent_id)
            await arena.broadcast.append("QUEUE_EXIT", {"agent_id": agent_id})

    web_root = Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"
    if web_root.is_dir():
        resolved_web_root = web_root.resolve()

        @app.get("/{full_path:path}", include_in_schema=False)
        def web_app(full_path: str):
            candidate = (resolved_web_root / full_path).resolve()
            if candidate.is_relative_to(resolved_web_root) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(resolved_web_root / "index.html")

    return app


app = create_app()
