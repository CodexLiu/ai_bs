from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .card_system import Deck, Card, Rank, Suit

class GamePhase(Enum):
    SETUP = "setup"
    PLAYING = "playing"
    GAME_OVER = "game_over"

@dataclass
class PlayedCards:
    cards: List[Card]
    claimed_rank: Rank
    claimed_count: int
    player_id: str
    turn_number: int

@dataclass
class GameState:
    player_hands: Dict[str, List[Card]]
    center_pile: List[PlayedCards]
    current_player_index: int
    player_order: List[str]
    current_expected_rank: Rank
    turn_number: int
    game_phase: GamePhase
    winner: Optional[str] = None
    last_action: Optional[str] = None

class GameStateManager:
    def __init__(self, player_ids: List[str]):
        self.player_ids = player_ids
        self.game_state = GameState(
            player_hands={},
            center_pile=[],
            current_player_index=0,
            player_order=player_ids.copy(),
            current_expected_rank=Rank.ACE,
            turn_number=1,
            game_phase=GamePhase.SETUP,
            winner=None,
            last_action=None
        )
        self.deck = Deck()
        self.context_manager = None  # Will be set by the context manager
        self._setup_game()
    
    def set_context_manager(self, context_manager):
        """Set the context manager reference for tracking actions"""
        self.context_manager = context_manager
    
    def _setup_game(self):
        """Initialize the game by dealing cards to all players"""
        self.deck.shuffle()
        
        # Deal all cards evenly to players
        cards_per_player = 52 // len(self.player_ids)
        remaining_cards = 52 % len(self.player_ids)
        
        for i, player_id in enumerate(self.player_ids):
            cards_to_deal = cards_per_player
            if i < remaining_cards:
                cards_to_deal += 1
            
            self.game_state.player_hands[player_id] = self.deck.deal_cards(cards_to_deal)
        
        # Find player with Ace of Spades to start
        ace_of_spades_player = None
        for player_id, hand in self.game_state.player_hands.items():
            for card in hand:
                if card.rank == Rank.ACE and card.suit.value == "spades":
                    ace_of_spades_player = player_id
                    break
            if ace_of_spades_player:
                break
        
        # Set starting player
        if ace_of_spades_player:
            self.game_state.current_player_index = self.player_ids.index(ace_of_spades_player)
        
        self.game_state.game_phase = GamePhase.PLAYING
    
    def get_current_player(self) -> str:
        """Get the current player's ID"""
        return self.game_state.player_order[self.game_state.current_player_index]
    
    def get_next_player(self) -> str:
        """Get the next player's ID in the turn order"""
        next_index = (self.game_state.current_player_index + 1) % len(self.game_state.player_order)
        return self.game_state.player_order[next_index]
    
    def get_player_hand_count(self, player_id: str) -> int:
        """Get the number of cards in a player's hand"""
        return len(self.game_state.player_hands.get(player_id, []))
    
    def get_all_hand_counts(self) -> Dict[str, int]:
        """Get card counts for all players"""
        return {player_id: len(hand) for player_id, hand in self.game_state.player_hands.items()}
    
    def get_center_pile_count(self) -> int:
        """Get the number of cards in the center pile"""
        total_cards = 0
        for played_cards in self.game_state.center_pile:
            total_cards += len(played_cards.cards)
        return total_cards
    
    def get_expected_rank(self) -> Rank:
        """Get the currently expected rank for plays"""
        return self.game_state.current_expected_rank
    
    def get_expected_rank_name(self) -> str:
        """Get the name of the expected rank"""
        rank_names = {
            1: "Ace", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
            8: "8", 9: "9", 10: "10", 11: "Jack", 12: "Queen", 13: "King"
        }
        return rank_names[self.game_state.current_expected_rank.value]
    
    def play_cards(self, player_id: str, cards: List[Card], claimed_rank: Rank, claimed_count: int) -> bool:
        """Player plays cards with claims about what they are"""
        if player_id != self.get_current_player():
            return False
        
        if claimed_rank != self.game_state.current_expected_rank:
            return False
        
        if claimed_count != len(cards):
            return False
        
        # Remove cards from player's hand
        player_hand = self.game_state.player_hands[player_id]
        for card in cards:
            if card in player_hand:
                player_hand.remove(card)
            else:
                return False
        
        # Determine if this was a truthful play
        was_truthful = all(card.rank == claimed_rank for card in cards)
        
        # Add to center pile
        played_cards = PlayedCards(
            cards=cards,
            claimed_rank=claimed_rank,
            claimed_count=claimed_count,
            player_id=player_id,
            turn_number=self.game_state.turn_number
        )
        self.game_state.center_pile.append(played_cards)
        
        # Track this action in context manager
        if self.context_manager:
            self.context_manager.add_game_action("play_cards", player_id, {
                "claimed_count": claimed_count,
                "claimed_rank": self.get_expected_rank_name(),
                "was_truthful": was_truthful,
                "actual_cards": [f"{card.rank.value} of {card.suit.value}" for card in cards]
            })
        
        # Check if player won
        if len(self.game_state.player_hands[player_id]) == 0:
            self.game_state.winner = player_id
            self.game_state.game_phase = GamePhase.GAME_OVER
            return True
        
        # Don't advance turn here - let orchestrator handle it after BS calls
        self.game_state.last_action = f"{player_id} played {claimed_count} cards"
        
        return True
    
    def call_bs(self, caller_id: str) -> Tuple[bool, str]:
        """Player calls BS on the last play"""
        if not self.game_state.center_pile:
            return False, "No cards have been played yet"
        
        if caller_id == self.get_current_player():
            return False, "Cannot call BS on yourself"
        
        last_play = self.game_state.center_pile[-1]
        target_player = last_play.player_id
        
        # Track the BS call in context manager
        if self.context_manager:
            self.context_manager.add_game_action("call_bs", caller_id, {
                "target_player": target_player
            })
        
        # Check if the last play was actually BS
        actual_ranks = [card.rank for card in last_play.cards]
        claimed_rank = last_play.claimed_rank
        
        was_bs = not all(rank == claimed_rank for rank in actual_ranks)
        penalty_cards = self.get_center_pile_count()
        
        if was_bs:
            # BS was called correctly - last player takes all cards
            self._player_takes_center_pile(last_play.player_id)
            result_msg = f"{caller_id} correctly called BS on {last_play.player_id}"
            self.game_state.last_action = result_msg
            
            # Track the BS result
            if self.context_manager:
                self.context_manager.add_game_action("bs_result", caller_id, {
                    "was_correct": True,
                    "caller": caller_id,
                    "target_player": target_player,
                    "penalty_cards": penalty_cards,
                    "was_bluffing": True,
                    "caught_player": target_player
                })
            
            # Person who called BS gets to play next with the next rank
            old_index = self.game_state.current_player_index
            old_player = self.game_state.player_order[old_index]
            self.game_state.current_player_index = self.game_state.player_order.index(caller_id)
            self.game_state.turn_number += 1
            self._advance_rank()
            print(f"   🔄 DEBUG: BS correct - turn set from {old_player} (index {old_index}) to {caller_id} (index {self.game_state.current_player_index})")
        else:
            # BS was called incorrectly - caller takes all cards
            self._player_takes_center_pile(caller_id)
            result_msg = f"{caller_id} incorrectly called BS on {last_play.player_id}"
            self.game_state.last_action = result_msg
            
            # Track the BS result
            if self.context_manager:
                self.context_manager.add_game_action("bs_result", caller_id, {
                    "was_correct": False,
                    "caller": caller_id,
                    "target_player": target_player,
                    "penalty_cards": penalty_cards,
                    "was_bluffing": False,
                    "caught_player": caller_id
                })
            
            # Turn advances to next player in sequence after incorrect BS call
            old_index = self.game_state.current_player_index
            old_player = self.game_state.player_order[old_index]
            self._advance_turn()
            new_player = self.game_state.player_order[self.game_state.current_player_index]
            print(f"   🔄 DEBUG: BS incorrect - turn advances from {old_player} (index {old_index}) to {new_player} (index {self.game_state.current_player_index})")
        
        return True, result_msg
    
    def _player_takes_center_pile(self, player_id: str):
        """Player takes all cards from center pile"""
        all_cards = []
        for played_cards in self.game_state.center_pile:
            all_cards.extend(played_cards.cards)
        
        self.game_state.player_hands[player_id].extend(all_cards)
        self.game_state.center_pile = []
    
    def _advance_turn(self):
        """Move to the next player and next expected rank"""
        old_index = self.game_state.current_player_index
        old_player = self.game_state.player_order[old_index]
        
        self.game_state.current_player_index = (self.game_state.current_player_index + 1) % len(self.game_state.player_order)
        self.game_state.turn_number += 1
        self._advance_rank()
        
        new_index = self.game_state.current_player_index
        new_player = self.game_state.player_order[new_index]
        
        # Debug logging
        print(f"   🔄 DEBUG: Turn advanced from {old_player} (index {old_index}) to {new_player} (index {new_index})")
    
    def _advance_rank(self):
        """Advance to the next expected rank"""
        next_rank_value = self.game_state.current_expected_rank.value + 1
        if next_rank_value > 13:
            next_rank_value = 1
        self.game_state.current_expected_rank = Rank(next_rank_value)
    
    def advance_turn(self):
        """Public method to advance the turn"""
        self._advance_turn()
    
    def get_game_context_for_player(self, player_id: str) -> Dict:
        """Get all visible game context for a specific player"""
        return {
            "player_id": player_id,
            "hand": self.game_state.player_hands[player_id],
            "hand_count": len(self.game_state.player_hands[player_id]),
            "other_players_hand_counts": {
                pid: len(hand) for pid, hand in self.game_state.player_hands.items() if pid != player_id
            },
            "current_player": self.get_current_player(),
            "is_my_turn": self.get_current_player() == player_id,
            "expected_rank": self.game_state.current_expected_rank,
            "expected_rank_name": self.get_expected_rank_name(),
            "center_pile_count": self.get_center_pile_count(),
            "turn_number": self.game_state.turn_number,
            "last_action": self.game_state.last_action,
            "game_phase": self.game_state.game_phase,
            "winner": self.game_state.winner
        }
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.game_state.game_phase == GamePhase.GAME_OVER
    
    def get_winner(self) -> Optional[str]:
        """Get the winner of the game"""
        return self.game_state.winner
    
    def get_turn_number(self) -> int:
        """Get the current turn number"""
        return self.game_state.turn_number 