import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { WS_URL } from './api';
import { initialBroadcastState } from './mock';
import { broadcastReducer, type BroadcastAction } from './state';
import type { BroadcastState, HallEntry, QueueEntry, SocketState, TableState } from './types';
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

const PUBLIC_SOUNDS = new Set<SoundName>(['deal', 'bomb', 'rocket', 'victory', 'elimination', 'challenger_enter', 'suspense', 'hall_of_fame']);

export function useBroadcast(enableAudio = false) {
  const [state, dispatch] = useReducer(broadcastReducer, initialBroadcastState);
  const [socketState, setSocketState] = useState<SocketState>('connecting');
  const lastSequence = useRef(state.lastSequence);
  const retry = useRef(0);

  useEffect(() => { lastSequence.current = state.lastSequence; }, [state.lastSequence]);

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
