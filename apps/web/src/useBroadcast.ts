import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { api, WS_URL } from './api';
import { initialBroadcastState } from './mock';
import { broadcastReducer, type BroadcastAction } from './state';
import type { AgentView, BroadcastState, HallEntry, QueueEntry, SocketState, TableState } from './types';
import { playSound, type SoundName } from './audio';

function decodeMessage(value: unknown): BroadcastAction | null {
  if (!value || typeof value !== 'object') return null;
  const message = value as Record<string, unknown>;
  if (message.kind === 'snapshot' && message.state) return { type: 'snapshot', state: message.state as BroadcastState };
  if (message.kind === 'table' && message.table) return { type: 'table', table: message.table as TableState, sequence: Number(message.sequence ?? 0) };
  if (message.kind === 'queue' && message.queue) return { type: 'queue', queue: message.queue as QueueEntry[], onlineCount: Number(message.online_count ?? 0), sequence: Number(message.sequence ?? 0) };
  if (message.kind === 'hall' && message.hall) return { type: 'hall', hall: message.hall as HallEntry[], sequence: Number(message.sequence ?? 0) };
  if (message.event_id && message.type) return { type: 'event', event: message as never };
  return null;
}

// 把后端 /api/public/table 投影转换成前端 TableState。
// 后端返回的是 { status, game_id, players[], base_stake, current_multiplier,
//   live_pov:{seat,hand}, remaining_card_counts, last_action, delay_seconds }。
function toTableState(raw: Record<string, unknown>): TableState {
  const players = Array.isArray(raw.players) ? raw.players : [];
  const counts = (raw.remaining_card_counts && typeof raw.remaining_card_counts === 'object')
    ? raw.remaining_card_counts as Record<string, unknown>
    : {};
  const roles = Object.keys(counts); // landlord, farmer_left, farmer_right (按座位序)
  const pov = raw.live_pov && typeof raw.live_pov === 'object'
    ? (raw.live_pov as Record<string, unknown>) : null;
  const agents: AgentView[] = players.map((p, idx) => {
    const pl = p as Record<string, unknown>;
    const role = (roles[idx] as AgentView['role']) || 'farmer_left';
    return {
      id: String(pl.id ?? `seat-${idx}`),
      name: String(pl.agent_name ?? '智能体'),
      model: String(pl.model_label ?? 'Custom'),
      role,
      balance: Number(pl.balance ?? 0),
      remaining: Number(counts[role] ?? 0),
      status: 'READY',
      isHouse: Boolean(pl.is_house),
      pov: Boolean(pl.pov_allowed),
      online: Boolean(pl.online),
    };
  });
  return {
    gameId: String(raw.game_id ?? ''),
    handNo: 0,
    status: ((String(raw.status ?? 'WAITING') === 'IDLE' ? 'WAITING' : String(raw.status ?? 'WAITING'))) as TableState['status'],
    turnAgentId: agents[Number(raw.current_seat ?? 0)]?.id ?? '',
    baseStake: Number(raw.base_stake ?? 0),
    multiplier: Number(raw.current_multiplier ?? 1),
    delaySeconds: Number(raw.delay_seconds ?? 30),
    landlordCards: [],
    povHand: pov ? (Array.isArray(pov.hand) ? pov.hand as string[] : []) : [],
    agents,
    history: [],
  };
}

const PUBLIC_SOUNDS = new Set<SoundName>(['deal', 'bomb', 'rocket', 'victory', 'elimination', 'challenger_enter', 'suspense', 'hall_of_fame']);

export function useBroadcast(enableAudio = false) {
  const [state, dispatch] = useReducer(broadcastReducer, initialBroadcastState);
  const [socketState, setSocketState] = useState<SocketState>('connecting');
  const lastSequence = useRef(state.lastSequence);
  const retry = useRef(0);

  useEffect(() => { lastSequence.current = state.lastSequence; }, [state.lastSequence]);

  // 首屏：先拉 REST 快照（真实数据），避免展示任何虚拟内容。
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tableRaw, queue, hall, events] = await Promise.all([
          api.publicTable().catch(() => null),
          api.publicQueue().catch(() => [] as QueueEntry[]),
          api.publicHall().catch(() => [] as HallEntry[]),
          api.publicEvents(0).catch(() => [] as never[]),
        ]);
        if (cancelled) return;
        // 先以快照填充，再把已到期事件按序叠加（保持严格 sequence）
        dispatch({
          type: 'snapshot',
          state: {
            lastSequence: 0,
            onlineCount: queue.length,
            table: tableRaw ? toTableState(tableRaw as Record<string, unknown>) : initialBroadcastState.table,
            queue,
            hall,
          },
        });
        for (const ev of events as never[]) {
          const action = decodeMessage(ev);
          if (action) dispatch(action);
        }
      } catch { /* REST 快照失败时依赖 WS */ }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let disposed = false;
    let ws: WebSocket | undefined;
    let reconnectTimer: number | undefined;
    let heartbeatTimer: number | undefined;

    const connect = () => {
      if (disposed) return;
      setSocketState(retry.current ? 'reconnecting' : 'connecting');
      // Always read latest sequence from ref to avoid stale closure after reconnect
      const resume = `${WS_URL}${WS_URL.includes('?') ? '&' : '?'}after=${lastSequence.current}`;
      try { ws = new WebSocket(resume); } catch { scheduleReconnect(); return; }
      ws.addEventListener('open', () => {
        retry.current = 0;
        setSocketState('open');
        heartbeatTimer = window.setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) ws.send('ping');
        }, 15000);
      });
      ws.addEventListener('message', (event) => {
        try {
          if (event.data === 'pong') return;
          const parsed = JSON.parse(String(event.data)) as Record<string, unknown>;
          if (enableAudio && parsed.type === 'SOUND' && parsed.payload && typeof parsed.payload === 'object') {
            const raw = String((parsed.payload as Record<string, unknown>).sound ?? '');
            const name = raw === 'challenger' ? 'challenger_enter' : raw as SoundName;
            if (PUBLIC_SOUNDS.has(name)) playSound(name);
          }
          const action = decodeMessage(parsed);
          if (action) dispatch(action);
        } catch { /* malformed public messages are ignored */ }
      });
      ws.addEventListener('close', scheduleReconnect);
      ws.addEventListener('error', () => ws?.close());
    };

    function scheduleReconnect() {
      if (disposed || reconnectTimer) return;
      window.clearInterval(heartbeatTimer);
      setSocketState('reconnecting');
      const delay = Math.min(1000 * 2 ** retry.current, 30000) + Math.random() * 400;
      retry.current += 1;
      reconnectTimer = window.setTimeout(() => { reconnectTimer = undefined; connect(); }, delay);
    }

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      window.clearInterval(heartbeatTimer);
      ws?.close();
      setSocketState('closed');
    };
  }, [enableAudio]);

  const injectEvent = useCallback((event: BroadcastAction) => dispatch(event), []);
  return { state, socketState, injectEvent };
}