from typing import Dict, List, Any
from .game_state_manager import GameStateManager
from .card_system import Card, Rank

class ContextManager:
    def __init__(self, game_state_manager: GameStateManager):
        self.game_state_manager = game_state_manager
        # Track conversation history for each player
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        # Track player summaries for each player
        self.player_summaries: Dict[str, Dict[str, Any]] = {}
    
    def add_conversation_turn(self, player_id: str, system_prompt: str, user_message: str, assistant_response: str, reasoning: str = ""):
        """
        Add a conversation turn to the history for a player.
        
        Args:
            player_id: The ID of the player
            system_prompt: The system prompt used
            user_message: The user message/game state
            assistant_response: The assistant's response
            reasoning: The reasoning behind the decision
        """
        if player_id not in self.conversation_history:
            self.conversation_history[player_id] = []
        
        self.conversation_history[player_id].append({
            "turn_number": self.game_state_manager.get_turn_number(),
            "system_prompt": system_prompt,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "reasoning": reasoning,
            "timestamp": self.game_state_manager.get_turn_number()
        })
    
    def get_conversation_history(self, player_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for a player."""
        return self.conversation_history.get(player_id, [])
    
    def should_summarize_context(self, player_id: str) -> bool:
        """Check if context should be summarized (8+ turns)."""
        history = self.get_conversation_history(player_id)
        return len(history) >= 8
    
    async def summarize_and_prune_context(self, player_id: str, personality: str, play_style: str, model: str = "gpt-4o-mini"):
        """
        Summarize the first 6 turns and delete them, using agent personality for reflection.
        
        Args:
            player_id: The ID of the player
            personality: The player's personality
            play_style: The player's play style
            model: The model to use for summarization
        """
        from .openai_api_call import call_openai_api
        
        history = self.get_conversation_history(player_id)
        if len(history) < 6:
            return
        
        # Get first 6 turns to summarize
        turns_to_summarize = history[:6]
        
        # Create summarization prompt
        summarization_prompt = f"""You are {player_id} reflecting on your game experience so far. 

YOUR PERSONALITY: {personality}
YOUR PLAY STYLE: {play_style}

Based on the following game history, create a structured reflection about:
1. What you've learned about other players' personalities and play styles
2. Strategies that have worked well for you
3. Strategies that haven't worked and should be avoided
4. Key game moments and lessons learned
5. Current assessment of other players' threat levels

Game History:
"""
        
        # Add conversation history to prompt
        for turn in turns_to_summarize:
            summarization_prompt += f"\nTurn {turn['turn_number']}:\n"
            summarization_prompt += f"Game State: {turn['user_message']}\n"
            summarization_prompt += f"Your Action: {turn['assistant_response']}\n"
            if turn['reasoning']:
                summarization_prompt += f"Your Reasoning: {turn['reasoning']}\n"
            summarization_prompt += "---\n"
        
        summarization_prompt += """

Please provide a JSON response with this structure:
{
  "player_personalities": {
    "player_name": "observed personality traits and play style"
  },
  "strategies_that_work": [
    "strategy 1",
    "strategy 2"
  ],
  "strategies_to_avoid": [
    "strategy 1",
    "strategy 2"
  ],
  "key_lessons": [
    "lesson 1",
    "lesson 2"
  ],
  "threat_assessment": {
    "player_name": "threat level and reasoning"
  },
  "game_reflection": "overall thoughts on the game so far"
}

Respond only with valid JSON."""
        
        # Call OpenAI API for summarization
        try:
            response = await call_openai_api(
                prompt=summarization_prompt,
                model=model,
                max_tokens=2000,
                temperature=0.7
            )
            
            import json
            summary = json.loads(response)
            
            # Store the summary
            self.player_summaries[player_id] = {
                "summary": summary,
                "summarized_turns": len(turns_to_summarize),
                "last_updated": self.game_state_manager.get_turn_number()
            }
            
            # Remove the summarized turns from history
            self.conversation_history[player_id] = history[6:]
            
        except Exception as e:
            print(f"Error summarizing context for {player_id}: {e}")
    
    def get_player_summary(self, player_id: str) -> Dict[str, Any]:
        """Get the stored summary for a player."""
        return self.player_summaries.get(player_id, {})
    
    def get_all_player_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored player summaries."""
        return self.player_summaries.copy()

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
        
        # Add summarized context if available
        summary = self.get_player_summary(player_id)
        if summary:
            base_prompt += f"\n\nYOUR GAME EXPERIENCE SUMMARY:\n"
            if 'summary' in summary:
                s = summary['summary']
                if 'player_personalities' in s:
                    base_prompt += f"Player Personalities: {s['player_personalities']}\n"
                if 'strategies_that_work' in s:
                    base_prompt += f"Strategies That Work: {s['strategies_that_work']}\n"
                if 'strategies_to_avoid' in s:
                    base_prompt += f"Strategies to Avoid: {s['strategies_to_avoid']}\n"
                if 'key_lessons' in s:
                    base_prompt += f"Key Lessons: {s['key_lessons']}\n"
                if 'threat_assessment' in s:
                    base_prompt += f"Threat Assessment: {s['threat_assessment']}\n"
                if 'game_reflection' in s:
                    base_prompt += f"Game Reflection: {s['game_reflection']}\n"
        
        # Add turn-specific instructions
        if context['is_my_turn']:
            base_prompt += f"""

IT'S YOUR TURN TO PLAY:
- You MUST play cards and claim they are {context['expected_rank_name']}s
- You can play 1-4 cards
- Use the play_cards function with card indices from your hand
- You can tell the truth or bluff - both are valid strategies
- Consider what cards others might have and your winning chances
- IMPORTANT: You cannot pass, call BS, or do anything else - you MUST play cards"""
        else:
            next_player = self.game_state_manager.get_next_player()
            base_prompt += f"""

IT'S NOT YOUR TURN:
- {context['current_player']} just played cards claiming they were {context['expected_rank_name']}s
- Only the next player in turn order ({next_player}) can call BS
- If you are {next_player}, you can call BS if you think they were lying
- If you are not {next_player}, you must wait for your turn
- Consider: Do you have cards that make their claim unlikely?
- IMPORTANT: You don't need to "pass" - just don't call BS if you believe them or if it's not your turn to call BS"""
        
        # Add personality and play style
        if personality:
            base_prompt += f"\n\nYOUR PERSONALITY: {personality}"
        
        if play_style:
            base_prompt += f"\n\nYOUR PLAY STYLE: {play_style}"
        
        # Add comprehensive strategy considerations
        base_prompt += f"""

WINNING CONDITIONS AND STRATEGIC ANALYSIS:
- OBJECTIVE: Be the first player to get rid of all your cards
- Current threat assessment based on card counts:
  * You have {context['hand_count']} cards - {'Very close to winning!' if context['hand_count'] <= 3 else 'Close to winning' if context['hand_count'] <= 6 else 'Mid-game' if context['hand_count'] <= 10 else 'Early game'}
  * Opponents: {', '.join([f"{pid} has {count} cards" for pid, count in context['other_players_hand_counts'].items()])}
  * Center pile: {context['center_pile_count']} cards (high risk/reward for BS calls)

DECISION IMPACT ANALYSIS:
- If you make a CORRECT play (truth or successful bluff):
  * You reduce your hand size and move closer to winning
  * Opponents must decide whether to call BS (risk vs reward)
  * You maintain control of the game flow

- If you make an INCORRECT play (caught bluffing):
  * You take ALL {context['center_pile_count']} cards from center pile
  * Your hand size increases significantly, moving you away from winning
  * Other players gain strategic advantage

- If you call BS CORRECTLY:
  * The liar takes all {context['center_pile_count']} cards from center pile
  * You don't take any cards and maintain your position
  * You prevent a potentially winning move by the liar

- If you call BS INCORRECTLY:
  * YOU take all {context['center_pile_count']} cards from center pile
  * Your hand size increases by {context['center_pile_count']} cards
  * The player you called BS on gets closer to winning
  * This is a MAJOR setback - only call BS when confident!

CARD COUNT STRATEGIC IMPLICATIONS:
- Players with very few cards (1-3): IMMEDIATE WINNING THREAT
  * Be extremely suspicious of their plays
  * Consider aggressive BS calls to prevent them from winning
  * They may be more likely to bluff to get rid of remaining cards
  
- Players with moderate cards (4-8): ACTIVE COMPETITORS
  * Monitor their plays carefully
  * They balance risk vs reward in their decisions
  * Good targets for strategic BS calls if caught bluffing
  
- Players with many cards (9+): LESS IMMEDIATE THREAT
  * May play more conservatively to avoid taking more cards
  * Less likely to make risky bluffs
  * Focus on your own game vs these players

CENTER PILE RISK ASSESSMENT:
- Current center pile: {context['center_pile_count']} cards
- Risk level: {'EXTREME' if context['center_pile_count'] >= 15 else 'HIGH' if context['center_pile_count'] >= 10 else 'MODERATE' if context['center_pile_count'] >= 5 else 'LOW'}
- Taking these cards would {'devastate your position' if context['center_pile_count'] >= 15 else 'seriously hurt your chances' if context['center_pile_count'] >= 10 else 'set you back significantly' if context['center_pile_count'] >= 5 else 'slightly impact your position'}

STRATEGY CONSIDERATIONS:
- Early game: Focus on getting rid of cards efficiently, build read on opponents
- Mid game: Pay attention to what cards have been played, start tactical thinking
- Late game: Be more aggressive with BS calls when players are close to winning
- Bluffing: Mix truth and lies to keep opponents guessing, but consider the risk
- Calling BS: Consider probability based on cards you've seen and hold, and the center pile size

IMPORTANT REMINDERS:
- You can only see your own cards, not others' cards
- Cards are played face-down, so you don't know what was actually played until BS is called
- Use function calls to take your action
- Always provide reasoning for your decisions
- Consider both immediate and long-term consequences of every action
- The center pile size makes BS calls increasingly risky as the game progresses"""
        
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