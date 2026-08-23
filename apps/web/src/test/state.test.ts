import { describe, expect, it } from 'vitest';
import { initialBroadcastState } from '../mock';
import { broadcastReducer } from '../state';

describe('broadcastReducer', () => {
  it('rejects duplicate or out-of-order events', () => {
    const first = broadcastReducer(initialBroadcastState, { type: 'event', event: { event_id: '3', sequence: 3, type: 'PLAY', actor: 'CatLord', payload: { cards: ['2♦'] } } });
    const duplicate = broadcastReducer(first, { type: 'event', event: { event_id: '3', sequence: 3, type: 'PLAY', actor: 'CatLord', payload: { cards: ['2♦'] } } });
    expect(duplicate).toBe(first);
    const stale = broadcastReducer(first, { type: 'event', event: { event_id: '2', sequence: 2, type: 'PASS' } });
    expect(stale).toBe(first);
  });

  it('appends a public play and preserves strict sequence', () => {
    const next = broadcastReducer(initialBroadcastState, { type: 'event', event: { event_id: '3', sequence: 3, type: 'PLAY', actor: 'CatLord', payload: { cards: ['2♦'] } } });
    expect(next.lastSequence).toBe(3);
    expect(next.table.history.at(-1)).toMatchObject({ actor: 'CatLord', cards: ['2♦'] });
  });

  it('caps event-driven multiplier at the tournament maximum', () => {
    const state = { ...initialBroadcastState, table: { ...initialBroadcastState.table, multiplier: 8 } };
    const next = broadcastReducer(state, { type: 'event', event: { event_id: 'bomb', sequence: 3, type: 'BOMB' } });
    expect(next.table.multiplier).toBe(8);
  });

  it('starts empty with no virtual data', () => {
    expect(initialBroadcastState.lastSequence).toBe(0);
    expect(initialBroadcastState.table.agents).toHaveLength(0);
    expect(initialBroadcastState.queue).toHaveLength(0);
    expect(initialBroadcastState.hall).toHaveLength(0);
  });
});