export enum Suit {
  HEARTS = "hearts",
  DIAMONDS = "diamonds", 
  CLUBS = "clubs",
  SPADES = "spades"
}

export enum Rank {
  ACE = 1,
  TWO = 2,
  THREE = 3,
  FOUR = 4,
  FIVE = 5,
  SIX = 6,
  SEVEN = 7,
  EIGHT = 8,
  NINE = 9,
  TEN = 10,
  JACK = 11,
  QUEEN = 12,
  KING = 13
}

export interface Card {
  suit: Suit;
  rank: Rank;
  id: string; // Unique identifier for tracking
}

export interface PlayedCards {
  cards: Card[];
  claimed_rank: Rank;
  claimed_count: number;
  player_id: string;
  turn_number: number;
}

export enum GamePhase {
  WAITING = "waiting",
  SETUP = "setup",
  PLAYING = "playing",
  GAME_OVER = "game_over"
}

export interface GameState {
  player_hands: Record<string, Card[]>;
  center_pile: PlayedCards[];
  current_player_index: number;
  player_order: string[];
  current_expected_rank: Rank;
  turn_number: number;
  game_phase: GamePhase;
  winner?: string;
  last_action?: string;
}

export interface GameAction {
  type: 'play_cards' | 'call_bs';
  player_id: string;
  cards?: Card[];
  claimed_count?: number;
  claimed_rank?: Rank;
  reasoning?: string;
  was_bs?: boolean;
  actual_cards?: Card[];
}

export interface PlayerInfo {
  id: string;
  name: string;
  hand_count: number;
  is_current_player: boolean;
  model: string;
}

export interface GameUIState {
  players: PlayerInfo[];
  current_expected_rank: Rank;
  center_pile_count: number;
  turn_number: number;
  last_action: string;
  game_phase: GamePhase;
  winner?: string;
} 