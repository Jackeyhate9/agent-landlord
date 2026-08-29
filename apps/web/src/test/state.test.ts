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

  it('projects live queue enter, token and exit events', () => {
    const entered = broadcastReducer(initialBroadcastState, {
      type: 'event',
      event: {
        event_id: 'join',
        sequence: 1,
        type: 'QUEUE_ENTER',
        payload: {
          agent_id: 'agent-1',
          agent_name: 'StreamBot',
          model_label: 'Codex',
          current_at: 10000,
          pov_allowed: true,
          online: true,
        },
      },
    });
    expect(entered.queue[0]).toMatchObject({ id: 'agent-1', name: 'StreamBot', balance: 10000 });
    const changed = broadcastReducer(entered, {
      type: 'event',
      event: { event_id: 'token', sequence: 2, type: 'TOKEN_CHANGE', payload: { agent_id: 'agent-1', delta: -100 } },
    });
    expect(changed.queue[0].balance).toBe(9900);
    const exited = broadcastReducer(changed, {
      type: 'event',
      event: { event_id: 'exit', sequence: 3, type: 'QUEUE_EXIT', payload: { agent_id: 'agent-1' } },
    });
    expect(exited.queue).toHaveLength(0);
  });

  it('starts empty with no virtual data', () => {
    expect(initialBroadcastState.lastSequence).toBe(0);
    expect(initialBroadcastState.table.agents).toHaveLength(0);
    expect(initialBroadcastState.queue).toHaveLength(0);
    expect(initialBroadcastState.hall).toHaveLength(0);
  });
});
