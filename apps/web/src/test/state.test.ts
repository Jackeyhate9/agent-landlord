import { describe, expect, it } from 'vitest';
import { initialBroadcastState } from '../mock';
import { broadcastReducer } from '../state';

describe('broadcastReducer', () => {
  it('rejects duplicate or out-of-order events', () => {
    const next = broadcastReducer(initialBroadcastState, { type: 'event', event: { event_id: 'old', sequence: 10, type: 'PASS' } });
    expect(next).toBe(initialBroadcastState);
  });

  it('appends a public play and preserves strict sequence', () => {
    const next = broadcastReducer(initialBroadcastState, { type: 'event', event: { event_id: '185', sequence: 185, type: 'PLAY', actor: 'CatLord', payload: { cards: ['2♦'] } } });
    expect(next.lastSequence).toBe(185);
    expect(next.table.history.at(-1)).toMatchObject({ actor: 'CatLord', cards: ['2♦'] });
  });

  it('caps event-driven multiplier at the tournament maximum', () => {
    const state = { ...initialBroadcastState, table: { ...initialBroadcastState.table, multiplier: 8 } };
    const next = broadcastReducer(state, { type: 'event', event: { event_id: 'bomb', sequence: 185, type: 'BOMB' } });
    expect(next.table.multiplier).toBe(8);
  });
});
