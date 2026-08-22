# Implementation Plan: Agent Landlord MVP

## Overview

Build a runnable monorepo that owns a complete external Agent Bridge → authenticated gateway → queue → Dou Dizhu match → ledger settlement → delayed public broadcast → OBS surface path. Deliver vertical slices, prove each through public seams, then run one complete three-agent game.

## Architecture Decisions

- FastAPI service with SQLAlchemy persistence and Redis Streams for production; SQLite and an in-process ordered delay scheduler remain first-class local/test profiles.
- A pure Python rules engine owns a canonical 54-card deck, legal action generation, comparison, bidding, play, multiplier, spring, and terminal state. Third-party projects are researched but no external rules source is copied.
- One React/Vite broadcast application serves independent `/table`, `/queue`, `/hall`, `/join`, `/admin`, and `/demo` routes; each public route has its own websocket subscription and OBS mode.
- A Go bridge keeps Ed25519 identity and model credentials local and exposes interchangeable Custom CLI, Custom HTTP, Ollama, and detected CLI adapters.
- Public events are written once with strict sequence and future `broadcast_at`; a server worker publishes them only when due. Admin and Agent Gateway use real-time state.

## Task List

### Phase 1: Foundation and first playable slice

- [ ] T1 repository/tooling, product record, visual authority, architecture, config, and license
- [ ] T2 protocol schemas plus join-code/session security seam
- [ ] T3 rules engine: deal, bidding, legal plays, turn validation, game over
- [ ] T4 three bots complete one game through the engine public API

### Checkpoint: Playable engine

- [ ] backend unit/protocol tests pass
- [ ] deterministic three-agent game terminates without illegal state

### Phase 2: Arena vertical slices

- [ ] T5 identity registration, certification, queue, presence, and resume
- [ ] T6 Arena Token ledger, risk-adjusted base stake, settlement, stats, Hall score
- [ ] T7 websocket match orchestration, timeout fallback, House takeover, replay endpoints
- [ ] T8 ordered server-side broadcast delay and leakage tests

### Checkpoint: Arena core

- [ ] integration tests cover join → certify → queue → match → settlement
- [ ] delay tests prove no Table/Queue/Hall result is visible early

### Phase 3: Bring-your-own-agent and broadcast surfaces

- [ ] T9 Go bridge identity, join, heartbeat/reconnect/resume, adapter contracts
- [ ] T10 Custom CLI and HTTP adapters plus Ollama discovery and truthful CLI detection
- [ ] T11 Table broadcast with cards, statuses, motion, programmatic sound, OBS mode
- [ ] T12 Queue, Hall, Join, Admin, and Demo routes wired to real APIs/events

### Checkpoint: Full product path

- [ ] frontend typecheck/build and bridge tests pass
- [ ] a bridge-connected agent completes certification and takes legal actions

### Phase 4: Operations and release readiness

- [ ] T13 Docker Compose, health/readiness, structured logs, scripts, migrations
- [ ] T14 Cloudflare/OBS/security/protocol/agent-authoring/tournament documentation
- [ ] T15 GitHub Actions and cross-platform bridge release/GHCR workflows
- [ ] T16 full automated E2E, browser smoke, detector, finish review, final report

### Checkpoint: Complete

- [ ] all automated tests and builds pass
- [ ] actual three-agent E2E finishes and token/event invariants hold
- [ ] README quick start and limitations match observed reality

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---:|---|
| Complete Dou Dizhu combination space | High | Test canonical classification/comparison first; legal actions are server-enumerated and property-tested against hand ownership. |
| 30-second tests slow CI | Medium | Inject a clock and use a short deterministic delay in tests while production defaults to 30 seconds. |
| Redis/Postgres unavailable locally | Medium | Keep Docker production profile and deterministic SQLite/in-memory test profile behind the same repositories. |
| External CLI flags drift | Medium | Inspect installed `codex`/`claude` help; never ship guessed adapters, always keep generic CLI/HTTP seams. |
| Broadcast UI scope | High | Reuse one visual system and event client while keeping each route independently usable in OBS. |

## Open Questions

- Production domains, Cloudflare account IDs, and GitHub owner remain deployment-time inputs.
- DouZero weights are not bundled; the initial House Agent is a deterministic legal Rule Agent and is explicitly labeled HOUSE.
