import { Card, GameUIState, GameAction, Rank, Suit } from '@/types/game';

interface GameApiResponse {
  success: boolean;
  data?: any;
  error?: string;
}

class GameApi {
  private baseUrl: string;
  private eventSource?: EventSource;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  // Convert Python card format to frontend format
  private convertCard(pythonCard: any): Card {
    return {
      id: `${pythonCard.suit}_${pythonCard.rank}`,
      suit: pythonCard.suit as Suit,
      rank: pythonCard.rank as Rank
    };
  }

  // Convert rank name to Rank enum
  private convertRank(rankName: string): Rank {
    const rankMap: Record<string, Rank> = {
      'Ace': Rank.ACE,
      '2': Rank.TWO,
      '3': Rank.THREE,
      '4': Rank.FOUR,
      '5': Rank.FIVE,
      '6': Rank.SIX,
      '7': Rank.SEVEN,
      '8': Rank.EIGHT,
      '9': Rank.NINE,
      '10': Rank.TEN,
      'Jack': Rank.JACK,
      'Queen': Rank.QUEEN,
      'King': Rank.KING
    };
    return rankMap[rankName] || Rank.ACE;
  }

  // Convert Python game state to frontend format
  private convertGameState(pythonState: any): GameUIState {
    return {
      players: pythonState.players.map((p: any) => ({
        id: p.id,
        name: p.name || p.id,
        hand_count: p.hand_count,
        is_current_player: p.is_current_player
      })),
      current_expected_rank: this.convertRank(pythonState.current_expected_rank),
      center_pile_count: pythonState.center_pile_count,
      turn_number: pythonState.turn_number,
      last_action: pythonState.last_action,
      game_phase: pythonState.game_phase,
      winner: pythonState.winner
    };
  }

  async startGame(): Promise<GameApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/start_game`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async getGameState(): Promise<GameApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/game_state`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return { 
        success: true, 
        data: {
          gameState: this.convertGameState(data.game_state),
          playerHands: Object.fromEntries(
            Object.entries(data.player_hands).map(([playerId, cards]) => [
              playerId,
              (cards as any[]).map(card => this.convertCard(card))
            ])
          ),
          centerPile: data.center_pile.map((card: any) => this.convertCard(card))
        }
      };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async advanceTurn(): Promise<GameApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/advance_turn`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  // Subscribe to game events via Server-Sent Events
  subscribeToGameEvents(onEvent: (event: any) => void): void {
    this.eventSource = new EventSource(`${this.baseUrl}/game_events`);
    
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch (error) {
        console.error('Error parsing event data:', error);
      }
    };
    
    this.eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
    };
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = undefined;
    }
  }
}

export default GameApi; 