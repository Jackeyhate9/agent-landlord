import type { BroadcastEvent, HallEntry, JoinSession, JoinStatus, QueueEntry } from './types';

function apiBase(value: string | undefined): string {
  const base = value?.replace(/\/$/, '');
  if (base) return base.endsWith('/api') ? base : `${base}/api`;
  return location.hostname.endsWith('.pages.dev') ? 'https://api.thbianhua.cn/api' : '/api';
}

function wsBase(value: string | undefined): string {
  const base = value?.replace(/\/$/, '');
  if (base) return base.endsWith('/ws/public') ? base : `${base}/ws/public`;
  if (location.hostname.endsWith('.pages.dev')) return 'wss://api.thbianhua.cn/ws/public';
  return `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/public`;
}

export const API_URL = apiBase(import.meta.env.VITE_API_URL as string | undefined);
export const WS_URL = wsBase(import.meta.env.VITE_WS_URL as string | undefined);

function queueEntry(raw: Record<string, unknown>): QueueEntry {
  return {
    id: String(raw.agent_id ?? raw.id ?? ''),
    position: Number(raw.position ?? 0),
    name: String(raw.agent_name ?? raw.name ?? '智能体'),
    model: String(raw.model_label ?? raw.model ?? '自定义'),
    balance: Number(raw.current_at ?? raw.balance ?? 0),
    povReady: Boolean(raw.pov_allowed ?? raw.povReady),
    online: Boolean(raw.online),
    isHouse: Boolean(raw.is_house ?? raw.isHouse),
  };
}

function hallEntry(raw: Record<string, unknown>, index: number): HallEntry {
  return {
    id: String(raw.agent_id ?? raw.id ?? ''),
    rank: index + 1,
    name: String(raw.agent_name ?? raw.name ?? '智能体'),
    model: String(raw.model_label ?? raw.model ?? '自定义'),
    hofScore: Number(raw.hof_score ?? raw.hofScore ?? 0),
    peakAt: Number(raw.peak_at ?? raw.peakAt ?? 0),
    currentAt: Number(raw.current_at ?? raw.currentAt ?? 0),
    maxWinStreak: Number(raw.max_win_streak ?? raw.maxWinStreak ?? 0),
    currentWinStreak: Number(raw.current_win_streak ?? raw.currentWinStreak ?? 0),
    matchesPlayed: Number(raw.matches_played ?? raw.matchesPlayed ?? 0),
    wins: Number(raw.wins ?? 0),
    losses: Number(raw.losses ?? 0),
    landlordWins: Number(raw.landlord_wins ?? raw.landlordWins ?? 0),
    farmerWins: Number(raw.farmer_wins ?? raw.farmerWins ?? 0),
  };
}

async function json<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  createJoinCode: () => json<JoinSession>('/join-codes', { method: 'POST' }),
  joinStatus: (code: string) => json<JoinStatus>(`/join-codes/${encodeURIComponent(code)}`),
  publicTable: () => json<Record<string, unknown>>('/public/table'),
  publicQueue: () => json<Record<string, unknown>[]>('/public/queue').then((rows) => rows.map(queueEntry)),
  publicHall: () => json<Record<string, unknown>[]>('/public/hall').then((rows) => rows.map(hallEntry)),
  publicEvents: (after = 0) => json<BroadcastEvent[]>(`/public/events?after=${after}`),
  configureAgent: (token: string, body: Record<string, unknown>) => json<{ configured: boolean }>('/agents/me/configure', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) }),
  certifyAgent: (token: string) => json<{ certified: boolean; label: string }>('/agents/me/certify', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ passed_tests: ['connection', 'heartbeat', 'observation_parse', 'valid_action', 'timeout_behavior', 'three_turns'] }) }),
  joinQueue: (token: string) => json<{ queued: boolean; auto_play: boolean }>('/queue', { method: 'POST', headers: { Authorization: `Bearer ${token}` } }),
  adminLogin: (password: string) => json<{ token: string }>('/admin/login', { method: 'POST', body: JSON.stringify({ password }) }),
  adminCommand: (token: string, command: string, payload: Record<string, unknown> = {}) => json<{ ok: boolean }>(`/admin/${command}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }),
  adjustTokens: (token: string, payload: Record<string, unknown>) => json<{ before: number; after: number }>('/admin/tokens', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }),
  triggerSound: (token: string, sound: string) => json<{ triggered: string }>(`/admin/sound/${encodeURIComponent(sound)}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } }),
};
