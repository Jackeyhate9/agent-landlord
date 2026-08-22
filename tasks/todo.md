# Agent Landlord Delivery Checklist

Each task is complete only when its public acceptance test and listed build command pass. Dependencies are shown inline.

## T1 Foundation (dependencies: none)

- [ ] Monorepo installs on Windows and Linux.
- [ ] `PRODUCT.md`, `DESIGN.md`, architecture, license, config, and quick start exist.
- Verification: repository inspection and config tests.

## T2 Protocol and secure join (dependencies: T1)

- [ ] Versioned observation/action schemas reject stale game/turn/session/action IDs.
- [ ] Join codes are unpredictable, expire in ten minutes, and are single use.
- Verification: protocol tests through Pydantic public models and HTTP endpoints.

## T3 Playable rules engine (dependencies: T2)

- [ ] A 54-card deck deals 17/17/17 plus three landlord cards without duplicates.
- [ ] Bidding, legal action generation, comparison, turn order, multiplier, spring, and terminal state work.
- Verification: focused rules tests plus seeded game simulation.

## T4 Three-bot engine E2E (dependencies: T3)

- [ ] Three independently invoked bot policies finish a seeded game.
- [ ] Every chosen ID was legal at the matching turn.
- Verification: `pytest tests/e2e/test_three_agents.py`.

## T5 Identity/certification/queue (dependencies: T2)

- [ ] Public-key identity grants initial AT once and certification gates queue entry.
- [ ] Heartbeat, resume, leave, POV lock, and public-field allowlist work.
- Verification: API integration tests.

## T6 Ledger/settlement/Hall (dependencies: T3, T5)

- [ ] Risk-adjusted stake prevents negative balances and settlement is zero-sum.
- [ ] Immutable ledger, statistics, eligibility, percentile score, and tie-breakers work.
- Verification: worked-example and invariant tests.

## T7 Orchestration/recovery/replay (dependencies: T3-T6)

- [ ] A queued trio plays through websocket observations/actions.
- [ ] Timeout fallback, unstable marking, House takeover, replay endpoints, and next challenger work.
- Verification: websocket integration and disconnect tests.

## T8 Broadcast delay (dependencies: T7)

- [ ] All public event types share an ordered server-side delay path.
- [ ] No result/token/queue/hall event is observable before due time.
- Verification: injected-clock delay tests.

## T9-T10 Bridge (dependencies: T2, T7)

- [ ] Go binary creates local Ed25519 identity and joins/resumes safely.
- [ ] Custom CLI/HTTP work; Ollama is detected; Codex/Claude are offered only when truthful.
- Verification: Go tests and bridge-to-server smoke.

## T11-T12 Web surfaces (dependencies: T7-T8)

- [ ] Independent Table/Queue/Hall pages consume delayed public events and support `?obs=1`.
- [ ] Join uses real workflow; Admin is authenticated/real-time/audited; Demo exercises visuals and sound.
- Verification: typecheck, production build, and browser route smoke.

## T13-T15 Operations (dependencies: core slices)

- [ ] Docker Compose, dev scripts, Cloudflare guides, health/readiness, CI and release workflows exist.
- Verification: config validation, Docker builds where the daemon is available.

## T16 Final validation (dependencies: all)

- [ ] Full E2E finishes at least one real match through the bridge/gateway path.
- [ ] Impeccable detector and independent finish review have no unresolved material findings.
- [ ] Final report marks every item PASS/PARTIAL/FAIL from observed evidence.
