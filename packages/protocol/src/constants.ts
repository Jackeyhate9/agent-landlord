/** Single source of truth for game constants. Keep in sync with server/protocol_constants.py */
export const PROTOCOL_VERSION = 1 as const;
export const MAX_MULTIPLIER = 8 as const;
export const MULTIPLIER_FACTOR = 2 as const;
export const STAKE_TIERS = [100, 200, 500, 1000] as const;
export const INITIAL_ARENA_TOKENS = 10000 as const;
export const MAX_TABLE_WIN_STREAK = 10 as const;
export const BROADCAST_DELAY_SECONDS = 30 as const;
export const AGENT_DECISION_TIMEOUT_MS = 8000 as const;

export const TABLE_EVENTS = new Set([
  'DEAL',
  'PLAY',
  'PASS',
  'BOMB',
  'ROCKET',
  'SPRING',
  'WIN',
  'LOSE',
  'ELIMINATION',
  'NEXT_CHALLENGER',
  'WIN_STREAK',
  'HALL_OF_FAME',
  'LANDLORD',
] as const);

export type TableEventType = typeof TABLE_EVENTS extends Set<infer T> ? T : never;
