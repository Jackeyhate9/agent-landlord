export { PROTOCOL_VERSION } from "./constants.js";
export type RoleSeat = "landlord" | "farmer_left" | "farmer_right";
export type BiddingSeat = "seat_0" | "seat_1" | "seat_2";
export type Seat = RoleSeat | BiddingSeat;
export type Phase = "bidding" | "playing" | "finished";
export interface LegalAction { id: number; cards: string[]; type?: string; bid?: 0 | 1 | 2 | 3 }
export interface ActionRecord { actor?: Seat; action_id: number; cards?: string[]; type?: string; bid?: 0 | 1 | 2 | 3 }
export interface ObservationV1 {
  protocol_version: 1; game_id: string; turn_id: string; phase?: Phase; seat: Seat; seat_index?: 0 | 1 | 2; hand: string[];
  landlord_cards_public: string[]; last_action?: ActionRecord; action_history: ActionRecord[];
  remaining_card_counts: Record<RoleSeat, number> | Record<BiddingSeat, number>; legal_actions: LegalAction[]; base_stake: number;
  current_multiplier: number; arena_token_balance: number; decision_timeout_ms: number;
}
export interface ActionV1 { protocol_version: 1; game_id: string; turn_id: string; action_id: number; public_comment?: string }

export function validateAction(observation: ObservationV1, action: ActionV1): string[] {
  const errors: string[] = [];
  if (action.protocol_version !== PROTOCOL_VERSION) errors.push("unsupported protocol_version");
  if (action.game_id !== observation.game_id) errors.push("game_id mismatch");
  if (action.turn_id !== observation.turn_id) errors.push("turn_id mismatch");
  if (!Number.isInteger(action.action_id)) errors.push("action_id must be an integer");
  if (!observation.legal_actions.some((candidate) => candidate.id === action.action_id)) errors.push("unknown action_id");
  if (action.public_comment && [...action.public_comment].length > 280) errors.push("public_comment exceeds 280 characters");
  return errors;
}
