"""Single source of truth for game constants. Keep in sync with packages/protocol/src/constants.ts"""

PROTOCOL_VERSION = 1
MAX_MULTIPLIER = 8
MULTIPLIER_FACTOR = 2
STAKE_TIERS = (100, 200, 500, 1000)
INITIAL_ARENA_TOKENS = 10000
MAX_TABLE_WIN_STREAK = 10
BROADCAST_DELAY_SECONDS = 30
AGENT_DECISION_TIMEOUT_MS = 8000

TABLE_EVENTS = frozenset({
    "DEAL",
    "PLAY",
    "PASS",
    "BOMB",
    "ROCKET",
    "SPRING",
    "WIN",
    "LOSE",
    "ELIMINATION",
    "NEXT_CHALLENGER",
    "WIN_STREAK",
    "HALL_OF_FAME",
    "LANDLORD",
})
