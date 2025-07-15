from typing import Dict, List, Any
from .game_state_manager import GameStateManager
from .card_system import Card, Rank

class ContextManager:
    def __init__(self, game_state_manager: GameStateManager):
        self.game_state_manager = game_state_manager
    
    def generate_system_prompt(self, player_id: str, personality: str = "", play_style: str = "") -> str:
        """
        Generate a comprehensive system prompt for an AI player with current game state.
        
        Args:
            player_id: The ID of the player
            personality: Player's personality traits
            play_style: Player's preferred play style
            
        Returns:
            Complete system prompt string
        """
        context = self.game_state_manager.get_game_context_for_player(player_id)
        
        # Base game rules and context
        base_prompt = f"""You are playing the card game BS (also known as Bullshit or Cheat). 

GAME RULES:
- Players take turns playing cards face-down, claiming they are of the expected rank
- You can tell the truth OR bluff about what cards you're playing
- After someone plays, any player can call "BS" if they think the person was lying
- If BS is called correctly, the liar takes all cards from the center pile
- If BS is called incorrectly, the caller takes all cards from the center pile
- First player to get rid of all their cards wins

CURRENT GAME STATE:
- You are: {player_id}
- Turn number: {context['turn_number']}
- Current player: {context['current_player']}
- Expected rank for this turn: {context['expected_rank_name']}
- Cards in center pile: {context['center_pile_count']}
- Your hand size: {context['hand_count']}"""

        # Add hand information
        hand_info = self._format_hand_info(context['hand'])
        base_prompt += f"\n- Your cards: {hand_info}"
        
        # Add other players' information
        other_players_info = []
        for pid, count in context['other_players_hand_counts'].items():
            other_players_info.append(f"{pid}: {count} cards")
        base_prompt += f"\n- Other players: {', '.join(other_players_info)}"
        
        # Add recent action if available
        if context['last_action']:
            base_prompt += f"\n- Last action: {context['last_action']}"
        
        # Add turn-specific instructions
        if context['is_my_turn']:
            base_prompt += f"""

IT'S YOUR TURN TO PLAY:
- You must play cards and claim they are {context['expected_rank_name']}s
- You can play 1-4 cards
- Use the play_cards function with card indices from your hand
- You can tell the truth or bluff - both are valid strategies
- Consider what cards others might have and your winning chances"""
        else:
            base_prompt += f"""

IT'S NOT YOUR TURN:
- {context['current_player']} just played cards claiming they were {context['expected_rank_name']}s
- You can call BS if you think they were lying
- You can pass if you believe them or don't want to risk it
- Consider: Do you have cards that make their claim unlikely?"""
        
        # Add personality and play style
        if personality:
            base_prompt += f"\n\nYOUR PERSONALITY: {personality}"
        
        if play_style:
            base_prompt += f"\n\nYOUR PLAY STYLE: {play_style}"
        
        # Add strategy considerations
        base_prompt += """

STRATEGY CONSIDERATIONS:
- Early game: Focus on getting rid of cards efficiently
- Mid game: Pay attention to what cards have been played
- Late game: Be more aggressive with BS calls when players are close to winning
- Bluffing: Mix truth and lies to keep opponents guessing
- Calling BS: Consider probability based on cards you've seen and hold

IMPORTANT REMINDERS:
- You can only see your own cards, not others' cards
- Cards are played face-down, so you don't know what was actually played until BS is called
- Use function calls to take your action
- Always provide reasoning for your decisions"""
        
        return base_prompt
    
    def _format_hand_info(self, hand: List[Card]) -> str:
        """Format hand information for the prompt"""
        if not hand:
            return "No cards"
        
        # Group cards by rank for easier reading
        rank_groups = {}
        for i, card in enumerate(hand):
            rank_name = self._get_rank_name(card.rank)
            if rank_name not in rank_groups:
                rank_groups[rank_name] = []
            rank_groups[rank_name].append(f"{i}:{card}")
        
        # Format as: "Aces: [0:Ace of Spades], 2s: [1:2 of Hearts, 3:2 of Clubs], ..."
        formatted_groups = []
        for rank_name in sorted(rank_groups.keys(), key=lambda x: self._rank_sort_key(x)):
            cards_str = ", ".join(rank_groups[rank_name])
            formatted_groups.append(f"{rank_name}: [{cards_str}]")
        
        return "; ".join(formatted_groups)
    
    def _get_rank_name(self, rank: Rank) -> str:
        """Get the display name for a rank"""
        rank_names = {
            1: "Aces", 2: "2s", 3: "3s", 4: "4s", 5: "5s", 6: "6s", 7: "7s",
            8: "8s", 9: "9s", 10: "10s", 11: "Jacks", 12: "Queens", 13: "Kings"
        }
        return rank_names[rank.value]
    
    def _rank_sort_key(self, rank_name: str) -> int:
        """Get sort key for rank names"""
        rank_order = {
            "Aces": 1, "2s": 2, "3s": 3, "4s": 4, "5s": 5, "6s": 6, "7s": 7,
            "8s": 8, "9s": 9, "10s": 10, "Jacks": 11, "Queens": 12, "Kings": 13
        }
        return rank_order.get(rank_name, 0)
    
    def generate_conversation_context(self, player_id: str) -> List[Dict[str, Any]]:
        """
        Generate conversation context in OpenAI format for the player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            List of conversation messages in OpenAI format
        """
        context = self.game_state_manager.get_game_context_for_player(player_id)
        
        # Create a conversation history based on recent game actions
        messages = []
        
        # Add game state summary as user message
        game_summary = f"""Game Status Update:
- Turn {context['turn_number']}
- Expected rank: {context['expected_rank_name']}
- Center pile: {context['center_pile_count']} cards
- Your hand: {context['hand_count']} cards"""
        
        if context['last_action']:
            game_summary += f"\n- Last action: {context['last_action']}"
        
        messages.append({
            "role": "user",
            "content": [{"type": "input_text", "text": game_summary}]
        })
        
        return messages
    
    def get_game_state_summary(self, player_id: str) -> Dict[str, Any]:
        """
        Get a summary of the current game state for the player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            Dictionary containing game state summary
        """
        context = self.game_state_manager.get_game_context_for_player(player_id)
        
        return {
            "player_id": player_id,
            "turn_number": context['turn_number'],
            "is_my_turn": context['is_my_turn'],
            "current_player": context['current_player'],
            "expected_rank": context['expected_rank_name'],
            "hand_size": context['hand_count'],
            "center_pile_size": context['center_pile_count'],
            "other_players": context['other_players_hand_counts'],
            "last_action": context['last_action'],
            "game_phase": context['game_phase'].value,
            "winner": context['winner']
        } 