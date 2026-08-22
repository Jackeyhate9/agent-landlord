import type { JoinSession } from './types';

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '/api';
export const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/public`;

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
  configureAgent: (token: string, body: Record<string, unknown>) => json<{ configured: boolean }>('/agents/me/configure', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) }),
  certifyAgent: (token: string) => json<{ certified: boolean; label: string }>('/agents/me/certify', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ passed_tests: ['connection', 'heartbeat', 'observation_parse', 'valid_action', 'timeout_behavior', 'three_turns'] }) }),
  joinQueue: (token: string) => json<{ queued: boolean; auto_play: boolean }>('/queue', { method: 'POST', headers: { Authorization: `Bearer ${token}` } }),
  adminLogin: (password: string) => json<{ token: string }>('/admin/login', { method: 'POST', body: JSON.stringify({ password }) }),
  adminCommand: (token: string, command: string, payload: Record<string, unknown> = {}) => json<{ ok: boolean }>(`/admin/${command}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }),
  adjustTokens: (token: string, payload: Record<string, unknown>) => json<{ before: number; after: number }>('/admin/tokens', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }),
  triggerSound: (token: string, sound: string) => json<{ triggered: string }>(`/admin/sound/${encodeURIComponent(sound)}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } }),
};
