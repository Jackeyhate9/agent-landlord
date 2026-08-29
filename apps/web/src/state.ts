import { MAX_MULTIPLIER, MULTIPLIER_FACTOR, TABLE_EVENTS } from '../../../packages/protocol/src/constants.js';

import type { BroadcastEvent, BroadcastState, HallEntry, PlayedAction, QueueEntry, TableState } from './types';

export type BroadcastAction =
  | { type: 'snapshot'; state: BroadcastState }
  | { type: 'table'; table: TableState; sequence?: number }
  | { type: 'queue'; queue: QueueEntry[]; onlineCount?: number; sequence?: number }
  | { type: 'hall'; hall: HallEntry[]; sequence?: number }
  | { type: 'event'; event: BroadcastEvent };

function queueEntry(payload: Record<string, unknown>): QueueEntry {
  return {
    id: String(payload.agent_id ?? ''),
    position: 0,
    name: String(payload.agent_name ?? 'Agent'),
    model: String(payload.model_label ?? 'Custom'),
    balance: Number(payload.current_at ?? 0),
    povReady: Boolean(payload.pov_allowed),
    online: Boolean(payload.online),
    isHouse: Boolean(payload.is_house),
  };
}

export function broadcastReducer(state: BroadcastState, action: BroadcastAction): BroadcastState {
  if (action.type === 'snapshot') return action.state.lastSequence >= state.lastSequence ? action.state : state;
  const sequence = action.type === 'event' ? action.event.sequence : action.sequence ?? state.lastSequence + 1;
  if (sequence <= state.lastSequence) return state;
  if (action.type === 'table') return { ...state, table: action.table, lastSequence: sequence };
  if (action.type === 'queue') return { ...state, queue: action.queue, onlineCount: action.onlineCount ?? state.onlineCount, lastSequence: sequence };
  if (action.type === 'hall') return { ...state, hall: action.hall, lastSequence: sequence };

  const event = action.event;
  const payload = event.payload ?? {};
  let table = (TABLE_EVENTS as Set<string>).has(event.type) ? { ...state.table, event } : state.table;
  let queue = state.queue;
  if (event.type === 'QUEUE_ENTER' && payload.agent_id) {
    queue = [...queue.filter((entry) => entry.id !== payload.agent_id), queueEntry(payload)]
      .map((entry, index) => ({ ...entry, position: index + 1 }));
  }
  if (event.type === 'QUEUE_EXIT' && payload.agent_id) {
    queue = queue.filter((entry) => entry.id !== payload.agent_id)
      .map((entry, index) => ({ ...entry, position: index + 1 }));
  }
  if (event.type === 'TOKEN_CHANGE' && payload.agent_id) {
    queue = queue.map((entry) => entry.id === payload.agent_id
      ? { ...entry, balance: Number(payload.after ?? entry.balance + Number(payload.delta ?? 0)) }
      : entry);
  }
  if (event.type === 'PASS' || event.type === 'PLAY') {
    const cards = Array.isArray(event.payload?.cards) ? (event.payload.cards as string[]) : [];
    const historyType = event.type as PlayedAction['type'];
    table = {
      ...table,
      history: [...table.history, { id: event.event_id, actor: event.actor ?? '未知', type: historyType, cards, sequence: event.sequence }].slice(-12),
    };
  }
  if (event.type === 'BOMB') table = { ...table, multiplier: Math.min(table.multiplier * MULTIPLIER_FACTOR, MAX_MULTIPLIER) };
  if (event.type === 'ROCKET') table = { ...table, multiplier: Math.min(table.multiplier * MULTIPLIER_FACTOR, MAX_MULTIPLIER) };
  return { ...state, table, queue, onlineCount: queue.length, lastSequence: sequence };
}
