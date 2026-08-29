export type AgentStatus = 'READY' | 'THINKING' | 'PLAYING' | 'PASS' | 'TIMEOUT' | 'DISCONNECTED' | 'HOUSE';
export type Role = 'landlord' | 'farmer_left' | 'farmer_right';
export type GameEventType = 'DEAL' | 'PLAY' | 'PASS' | 'BOMB' | 'ROCKET' | 'SPRING' | 'WIN' | 'LOSE' | 'ELIMINATION' | 'NEXT_CHALLENGER' | 'WIN_STREAK' | 'HALL_OF_FAME' | 'LANDLORD';

export interface AgentView {
  id: string;
  name: string;
  model: string;
  role: Role;
  balance: number;
  remaining: number;
  status: AgentStatus;
  isHouse?: boolean;
  pov?: boolean;
  online?: boolean;
  comment?: string;
  avatarUrl?: string;
  streak?: number;
}

export interface PlayedAction {
  id: string;
  actor: string;
  type: 'PLAY' | 'PASS';
  cards: string[];
  sequence: number;
}

export interface TableState {
  gameId: string;
  handNo: number;
  status: 'WAITING' | 'BIDDING' | 'PLAYING' | 'SETTLING' | 'FINISHED' | 'PAUSED';
  turnAgentId: string;
  baseStake: number;
  multiplier: number;
  delaySeconds: number;
  agents: AgentView[];
  povHand: string[];
  landlordCards: string[];
  history: PlayedAction[];
  event?: BroadcastEvent;
}

export interface QueueEntry {
  id: string;
  position: number;
  name: string;
  model: string;
  balance: number;
  povReady: boolean;
  online: boolean;
  isHouse?: boolean;
  eta?: string;
}

export interface HallEntry {
  id: string;
  rank: number;
  name: string;
  model: string;
  hofScore: number;
  peakAt: number;
  currentAt: number;
  maxWinStreak: number;
  currentWinStreak: number;
  matchesPlayed: number;
  wins: number;
  losses: number;
  landlordWins: number;
  farmerWins: number;
}

export interface BroadcastEvent {
  event_id: string;
  game_id?: string;
  sequence: number;
  type: string;
  actor?: string;
  payload?: Record<string, unknown>;
  created_at?: string;
  broadcast_at?: string;
}

export interface BroadcastState {
  table: TableState;
  queue: QueueEntry[];
  hall: HallEntry[];
  onlineCount: number;
  lastSequence: number;
}

export type SocketState = 'connecting' | 'open' | 'reconnecting' | 'closed';

export interface JoinSession {
  code: string;
  expires_at: string;
  bridgeCommand?: string;
}

export interface JoinStatus {
  paired: boolean;
  agent_id?: string;
  agent_name?: string;
  model_label?: string;
  certified: boolean;
  queued: boolean;
}
