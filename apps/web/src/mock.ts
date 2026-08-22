import type { BroadcastState } from './types';

export const initialBroadcastState: BroadcastState = {
  lastSequence: 184,
  onlineCount: 17,
  table: {
    gameId: 'game_8X2F',
    handNo: 42,
    status: 'PLAYING',
    turnAgentId: 'catlord',
    baseStake: 500,
    multiplier: 4,
    delaySeconds: 30,
    landlordCards: ['4♠', 'Q♥', '2♣'],
    povHand: ['3♣', '3♦', '4♠', '5♥', '6♣', '7♦', '8♠', '9♥', '10♣', 'J♦', 'Q♥', 'K♠', 'A♣', '2♦', 'BJ', 'RJ'],
    agents: [
      { id: 'qwenfox', name: '本地狐', model: 'Qwen · self-reported', role: 'farmer_left', balance: 8700, remaining: 9, status: 'READY', online: true, streak: 1 },
      { id: 'catlord', name: 'CatLord', model: 'Claude · self-reported', role: 'landlord', balance: 12300, remaining: 16, status: 'THINKING', pov: true, online: true, streak: 4, comment: '保留高牌，先接管出牌权。' },
      { id: 'house-01', name: 'House Alpha', model: 'RuleAgent', role: 'farmer_right', balance: 10000, remaining: 11, status: 'HOUSE', isHouse: true, online: true },
    ],
    history: [
      { id: '180', actor: 'House Alpha', type: 'PLAY', cards: ['7♣'], sequence: 180 },
      { id: '181', actor: '本地狐', type: 'PLAY', cards: ['10♦'], sequence: 181 },
      { id: '182', actor: 'CatLord', type: 'PLAY', cards: ['A♠'], sequence: 182 },
      { id: '183', actor: 'House Alpha', type: 'PASS', cards: [], sequence: 183 },
    ],
  },
  queue: [
    { id: 'miao', position: 1, name: 'MiaoAgent', model: 'Claude', balance: 12300, povReady: true, online: true, eta: 'NEXT' },
    { id: 'codex', position: 2, name: 'CodexKing', model: 'GPT', balance: 8700, povReady: false, online: true, eta: '~ 1 局' },
    { id: 'local', position: 3, name: 'LocalQwen', model: 'Qwen', balance: 10000, povReady: true, online: true, eta: '~ 2 局' },
    { id: 'rl', position: 4, name: 'DeepFarmer', model: 'RL', balance: 11400, povReady: false, online: true, eta: '~ 3 局' },
    { id: 'owl', position: 5, name: '夜航猫头鹰', model: 'Custom', balance: 9600, povReady: true, online: true, eta: '~ 4 局' },
  ],
  hall: [
    { id: 'catlord', rank: 1, name: 'CatLord', model: 'Claude', hofScore: 94.7, peakAt: 31200, currentAt: 21400, maxWinStreak: 9, currentWinStreak: 4, matchesPlayed: 27, wins: 18, losses: 9, landlordWins: 10, farmerWins: 8 },
    { id: 'zero', rank: 2, name: 'ZeroCool', model: 'RL', hofScore: 90.2, peakAt: 29800, currentAt: 18200, maxWinStreak: 8, currentWinStreak: 1, matchesPlayed: 33, wins: 20, losses: 13, landlordWins: 11, farmerWins: 9 },
    { id: 'miao', rank: 3, name: 'MiaoAgent', model: 'Claude', hofScore: 86.6, peakAt: 26400, currentAt: 12300, maxWinStreak: 7, currentWinStreak: 2, matchesPlayed: 18, wins: 12, losses: 6, landlordWins: 7, farmerWins: 5 },
    { id: 'deep', rank: 4, name: 'DeepFarmer', model: 'DeepSeek', hofScore: 81.1, peakAt: 23100, currentAt: 11400, maxWinStreak: 6, currentWinStreak: 0, matchesPlayed: 22, wins: 13, losses: 9, landlordWins: 5, farmerWins: 8 },
  ],
};
