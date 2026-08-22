# OBS Guide

Add three independent Browser Sources. Recommended canvas is 1920×1080:

- Table (about 74%): `http://localhost:5173/table?obs=1`
- Queue (about 15%): `http://localhost:5173/queue?obs=1`
- Hall (about 11%): `http://localhost:5173/hall?obs=1`

Use 1920×1080 for Table and crop it in the OBS scene; use 480×600 for Queue and 480×420 for Hall. Enable “Control audio via OBS” on Table. The page synthesizes its own event sounds with Web Audio and contains no music or externally licensed sound files.

All three public pages consume the same server-delayed event stream. Do not add a separate OBS render delay: it would stack on top of the configured server delay. `?obs=1` removes navigation and margins, disables scrollbars, connects automatically, and applies reconnect/backoff.

Before a stream, use `/demo` and the Admin soundboard to test Deal, Bomb, Rocket, Victory, Elimination, Challenger, Suspense and Hall of Fame cues. Browser autoplay policy may require one click in OBS Interact before sound begins.

