# Protocol conformance fixtures

These known-good v1 JSON documents are language-neutral inputs for server, Bridge, and UI conformance tests. JSON Schema sources are in `packages/protocol/schema`; behavioral validation (game/turn binding and membership in legal actions) is intentionally tested by `bridge/protocol` because JSON Schema cannot compare two documents.

`observation-bidding-v1.json` covers the pre-role `seat_0..2` contract; `observation-v1.json` covers role-based playing state.
