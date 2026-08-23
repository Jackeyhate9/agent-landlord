import type { BroadcastState } from './types';

// 初始空状态：不展示任何虚拟数据。真实对局数据由 useBroadcast 连接后
// 通过 REST 快照 (/api/public/table|queue|hall) 填充，再叠加 WebSocket 增量事件。
export const initialBroadcastState: BroadcastState = {
  lastSequence: 0,
  onlineCount: 0,
  table: {
    gameId: '',
    handNo: 0,
    status: 'WAITING',
    turnAgentId: '',
    baseStake: 0,
    multiplier: 1,
    delaySeconds: 30,
    landlordCards: [],
    povHand: [],
    agents: [],
    history: [],
  },
  queue: [],
  hall: [],
};