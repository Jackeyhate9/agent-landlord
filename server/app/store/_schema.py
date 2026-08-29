SQLITE_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS agents (
 id TEXT PRIMARY KEY, owner_public_key TEXT NOT NULL UNIQUE, agent_name TEXT NOT NULL,
 model_label TEXT NOT NULL, runtime_label TEXT NOT NULL, avatar_url TEXT,
 balance INTEGER NOT NULL CHECK(balance >= 0), certified INTEGER NOT NULL DEFAULT 0,
 max_stake INTEGER NOT NULL DEFAULT 100, pov_allowed INTEGER NOT NULL DEFAULT 0,
 online INTEGER NOT NULL DEFAULT 1, is_house INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_sessions (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, last_heartbeat TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS agent_keys (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), owner_public_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS join_codes (
 code_hash TEXT PRIMARY KEY, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS join_pairings (
 code_hash TEXT PRIMARY KEY, agent_id TEXT REFERENCES agents(id),
 expires_at TEXT NOT NULL, paired_at TEXT
);
CREATE TABLE IF NOT EXISTS queue_entries (
 id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL UNIQUE REFERENCES agents(id),
 joined_at TEXT NOT NULL, auto_play INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS games (
 id TEXT PRIMARY KEY, status TEXT NOT NULL, base_stake INTEGER NOT NULL,
 multiplier INTEGER NOT NULL DEFAULT 1, winner_side TEXT, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS game_players (
 game_id TEXT NOT NULL REFERENCES games(id), agent_id TEXT NOT NULL REFERENCES agents(id),
 seat TEXT NOT NULL, token_delta INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(game_id, agent_id)
);
CREATE TABLE IF NOT EXISTS game_events (
 event_id TEXT PRIMARY KEY, game_id TEXT, sequence INTEGER NOT NULL UNIQUE, type TEXT NOT NULL,
 actor TEXT, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, broadcast_at TEXT NOT NULL,
 published_at TEXT
);
CREATE TABLE IF NOT EXISTS arena_token_ledger (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), game_id TEXT,
 delta INTEGER NOT NULL, balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL CHECK(balance_after >= 0),
 type TEXT NOT NULL, timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leaderboard_stats (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), matches_played INTEGER NOT NULL DEFAULT 0,
 wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
 peak_at INTEGER NOT NULL, current_at INTEGER NOT NULL, max_win_streak INTEGER NOT NULL DEFAULT 0,
 current_win_streak INTEGER NOT NULL DEFAULT 0, landlord_wins INTEGER NOT NULL DEFAULT 0,
 farmer_wins INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admin_audit_logs (
 id TEXT PRIMARY KEY, admin TEXT NOT NULL, agent_id TEXT NOT NULL, before INTEGER NOT NULL,
 after INTEGER NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
 id TEXT PRIMARY KEY, owner_public_key TEXT NOT NULL UNIQUE, agent_name TEXT NOT NULL,
 model_label TEXT NOT NULL, runtime_label TEXT NOT NULL, avatar_url TEXT,
 balance INTEGER NOT NULL CHECK(balance >= 0), certified INTEGER NOT NULL DEFAULT 0,
 max_stake INTEGER NOT NULL DEFAULT 100, pov_allowed INTEGER NOT NULL DEFAULT 0,
 online INTEGER NOT NULL DEFAULT 1, is_house INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_sessions (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, last_heartbeat TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS agent_keys (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), owner_public_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS join_codes (
 code_hash TEXT PRIMARY KEY, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS join_pairings (
 code_hash TEXT PRIMARY KEY, agent_id TEXT REFERENCES agents(id),
 expires_at TEXT NOT NULL, paired_at TEXT
);
CREATE TABLE IF NOT EXISTS queue_entries (
 id SERIAL PRIMARY KEY, agent_id TEXT NOT NULL UNIQUE REFERENCES agents(id),
 joined_at TEXT NOT NULL, auto_play INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS games (
 id TEXT PRIMARY KEY, status TEXT NOT NULL, base_stake INTEGER NOT NULL,
 multiplier INTEGER NOT NULL DEFAULT 1, winner_side TEXT, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS game_players (
 game_id TEXT NOT NULL REFERENCES games(id), agent_id TEXT NOT NULL REFERENCES agents(id),
 seat TEXT NOT NULL, token_delta INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(game_id, agent_id)
);
CREATE TABLE IF NOT EXISTS game_events (
 event_id TEXT PRIMARY KEY, game_id TEXT, sequence INTEGER NOT NULL UNIQUE, type TEXT NOT NULL,
 actor TEXT, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, broadcast_at TEXT NOT NULL,
 published_at TEXT
);
CREATE TABLE IF NOT EXISTS arena_token_ledger (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), game_id TEXT,
 delta INTEGER NOT NULL, balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL CHECK(balance_after >= 0),
 type TEXT NOT NULL, timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leaderboard_stats (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id), matches_played INTEGER NOT NULL DEFAULT 0,
 wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
 peak_at INTEGER NOT NULL, current_at INTEGER NOT NULL, max_win_streak INTEGER NOT NULL DEFAULT 0,
 current_win_streak INTEGER NOT NULL DEFAULT 0, landlord_wins INTEGER NOT NULL DEFAULT 0,
 farmer_wins INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admin_audit_logs (
 id TEXT PRIMARY KEY, admin TEXT NOT NULL, agent_id TEXT NOT NULL, before INTEGER NOT NULL,
 after INTEGER NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL
);
"""
