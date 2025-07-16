from typing import Dict, List, Any
import json
from .game_state_manager import GameStateManager
from .card_system import Card, Rank

class ContextManager:
    def __init__(self, game_state_manager: GameStateManager):
        self.game_state_manager = game_state_manager
        # Set the context manager reference in the game state manager
        self.game_state_manager.set_context_manager(self)
        # Track conversation history for each player
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        # Track player summaries for each player
        self.player_summaries: Dict[str, Dict[str, Any]] = {}
        # Track global game action history that all players can see
        self.global_game_history: List[Dict[str, Any]] = []
        # Track player behavior patterns
        self.player_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Clean up any existing invalid data
        self.clean_invalid_player_data()
    
    def add_game_action(self, action_type: str, player_id: str, details: Dict[str, Any]):
        """
        Add a game action to the global history that all players can see.
        
        Args:
            action_type: Type of action (play_cards, call_bs, bs_result)
            player_id: ID of the player who performed the action
            details: Additional details about the action
        """
        # Validate player_id
        if not player_id or player_id.strip() == "":
            print(f"❌ ERROR: Invalid player_id '{player_id}' in add_game_action")
            return
        
        # Validate that player_id is in the game
        if player_id not in self.game_state_manager.player_ids:
            print(f"❌ ERROR: Player ID '{player_id}' not found in game player list: {self.game_state_manager.player_ids}")
            return
        
        # Validate details for specific action types
        if action_type == "call_bs":
            target_player = details.get("target_player")
            if not target_player or target_player not in self.game_state_manager.player_ids:
                print(f"❌ ERROR: Invalid target_player '{target_player}' in call_bs action")
                return
        
        if action_type == "bs_result":
            caller = details.get("caller")
            target_player = details.get("target_player")
            if not caller or caller not in self.game_state_manager.player_ids:
                print(f"❌ ERROR: Invalid caller '{caller}' in bs_result action")
                return
            if not target_player or target_player not in self.game_state_manager.player_ids:
                print(f"❌ ERROR: Invalid target_player '{target_player}' in bs_result action")
                return
        
        action_entry = {
            "turn_number": self.game_state_manager.get_turn_number(),
            "action_type": action_type,
            "player_id": player_id,
            "details": details,
            "timestamp": self.game_state_manager.get_turn_number()
        }
        
        self.global_game_history.append(action_entry)
        
        # Update player patterns
        if player_id not in self.player_patterns:
            self.player_patterns[player_id] = {
                "cards_played": 0,
                "bs_calls_made": 0,
                "bs_calls_correct": 0,
                "times_caught_bluffing": 0,
                "times_played_truthfully": 0,
                "recent_actions": []
            }
        
        patterns = self.player_patterns[player_id]
        patterns["recent_actions"].append(action_entry)
        
        # Keep only last 10 actions per player
        if len(patterns["recent_actions"]) > 10:
            patterns["recent_actions"] = patterns["recent_actions"][-10:]
        
        # Update specific pattern counters
        if action_type == "play_cards":
            patterns["cards_played"] += details.get("claimed_count", 0)
            if details.get("was_truthful", False):
                patterns["times_played_truthfully"] += 1
        elif action_type == "call_bs":
            patterns["bs_calls_made"] += 1
        elif action_type == "bs_result":
            # Update BS call success for the caller
            caller = details.get("caller")
            if caller == player_id and details.get("was_correct", False):
                patterns["bs_calls_correct"] += 1
            # Update bluffing counts
            if details.get("was_bluffing", False) and details.get("caught_player") == player_id:
                patterns["times_caught_bluffing"] += 1
    
    def clean_invalid_player_data(self):
        """
        Clean up any invalid player data that might have been stored.
        This includes removing entries with None, empty strings, or "unknown" player IDs.
        """
        print("🧹 Cleaning up invalid player data from context manager...")
        
        # Clean up conversation history
        invalid_conversation_keys = []
        for player_id in self.conversation_history.keys():
            if not player_id or player_id.strip() == "" or player_id == "unknown" or player_id not in self.game_state_manager.player_ids:
                invalid_conversation_keys.append(player_id)
        
        for key in invalid_conversation_keys:
            print(f"🧹 Removing invalid conversation history for player: '{key}'")
            del self.conversation_history[key]
        
        # Clean up player summaries
        invalid_summary_keys = []
        for player_id in self.player_summaries.keys():
            if not player_id or player_id.strip() == "" or player_id == "unknown" or player_id not in self.game_state_manager.player_ids:
                invalid_summary_keys.append(player_id)
        
        for key in invalid_summary_keys:
            print(f"🧹 Removing invalid player summary for player: '{key}'")
            del self.player_summaries[key]
        
        # Clean up player patterns
        invalid_pattern_keys = []
        for player_id in self.player_patterns.keys():
            if not player_id or player_id.strip() == "" or player_id == "unknown" or player_id not in self.game_state_manager.player_ids:
                invalid_pattern_keys.append(player_id)
        
        for key in invalid_pattern_keys:
            print(f"🧹 Removing invalid player pattern for player: '{key}'")
            del self.player_patterns[key]
        
        # Clean up global game history - remove actions with invalid player IDs
        valid_history = []
        for action in self.global_game_history:
            player_id = action.get("player_id")
            if player_id and player_id.strip() != "" and player_id != "unknown" and player_id in self.game_state_manager.player_ids:
                # Also validate details in the action
                details = action.get("details", {})
                action_type = action.get("action_type")
                
                is_valid = True
                if action_type == "call_bs":
                    target_player = details.get("target_player")
                    if not target_player or target_player not in self.game_state_manager.player_ids:
                        is_valid = False
                elif action_type == "bs_result":
                    caller = details.get("caller")
                    target_player = details.get("target_player")
                    if not caller or caller not in self.game_state_manager.player_ids:
                        is_valid = False
                    if not target_player or target_player not in self.game_state_manager.player_ids:
                        is_valid = False
                
                if is_valid:
                    valid_history.append(action)
                else:
                    print(f"🧹 Removing invalid action from history: {action}")
            else:
                print(f"🧹 Removing action with invalid player_id '{player_id}' from history")
        
        self.global_game_history = valid_history
        
        print(f"✅ Cleanup complete. Valid players: {self.game_state_manager.player_ids}")
    
    def get_game_history_summary(self, max_actions: int = 15) -> str:
        """
        Get a formatted summary of recent game actions that all players can see.
        
        Args:
            max_actions: Maximum number of recent actions to include
            
        Returns:
            Formatted string of recent game history
        """
        if not self.global_game_history:
            return "No actions yet this game."
        
        # Get the most recent actions
        recent_actions = self.global_game_history[-max_actions:]
        
        history_lines = []
        for action in recent_actions:
            turn = action["turn_number"]
            action_type = action["action_type"]
            player = action["player_id"]
            details = action["details"]
            
            if action_type == "play_cards":
                claimed_count = details.get("claimed_count", 0)
                claimed_rank = details.get("claimed_rank", "Unknown")
                was_truthful = details.get("was_truthful")
                if was_truthful is not None:
                    truth_indicator = " (truthful)" if was_truthful else " (bluffing)"
                else:
                    truth_indicator = ""
                history_lines.append(f"Turn {turn}: {player} played {claimed_count} {claimed_rank}{'s' if claimed_count != 1 else ''}{truth_indicator}")
            
            elif action_type == "call_bs":
                target = details.get("target_player")
                if target and target in self.game_state_manager.player_ids:
                    history_lines.append(f"Turn {turn}: {player} called BS on {target}")
                else:
                    print(f"❌ WARNING: Invalid target_player in call_bs history: {target}")
                    history_lines.append(f"Turn {turn}: {player} called BS on [invalid player]")
            
            elif action_type == "bs_result":
                was_correct = details.get("was_correct", False)
                caller = details.get("caller")
                target = details.get("target_player")
                penalty_cards = details.get("penalty_cards", 0)
                
                # Validate caller and target
                if not caller or caller not in self.game_state_manager.player_ids:
                    print(f"❌ WARNING: Invalid caller in bs_result history: {caller}")
                    caller = "[invalid player]"
                if not target or target not in self.game_state_manager.player_ids:
                    print(f"❌ WARNING: Invalid target_player in bs_result history: {target}")
                    target = "[invalid player]"
                
                if was_correct:
                    history_lines.append(f"Turn {turn}: BS call CORRECT - {target} takes {penalty_cards} cards")
                else:
                    history_lines.append(f"Turn {turn}: BS call WRONG - {caller} takes {penalty_cards} cards")
        
        return "\n".join(history_lines)
    
    def get_player_behavior_summary(self) -> str:
        """
        Get a summary of player behavior patterns that all players can observe.
        
        Returns:
            Formatted string of player behavior patterns
        """
        if not self.player_patterns:
            return "No player patterns established yet."
        
        behavior_lines = []
        for player_id, patterns in self.player_patterns.items():
            # Validate player_id
            if not player_id or player_id not in self.game_state_manager.player_ids:
                print(f"❌ WARNING: Invalid player_id '{player_id}' in player patterns, skipping")
                continue
                
            cards_played = patterns["cards_played"]
            bs_calls = patterns["bs_calls_made"]
            bs_accuracy = patterns["bs_calls_correct"]
            times_caught = patterns["times_caught_bluffing"]
            times_truthful = patterns["times_played_truthfully"]
            
            # Calculate percentages
            bs_success_rate = (bs_accuracy / bs_calls * 100) if bs_calls > 0 else 0
            total_plays = times_caught + times_truthful
            truthful_rate = (times_truthful / total_plays * 100) if total_plays > 0 else 0
            
            behavior_summary = f"{player_id}: {cards_played} cards played"
            if bs_calls > 0:
                behavior_summary += f", {bs_calls} BS calls ({bs_success_rate:.0f}% success)"
            if total_plays > 0:
                behavior_summary += f", {truthful_rate:.0f}% truthful plays"
            
            behavior_lines.append(behavior_summary)
        
        return "\n".join(behavior_lines)

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
        """Check if context should be summarized (every 2 turns)."""
        history = self.get_conversation_history(player_id)
        should_summarize = len(history) >= 2 and len(history) % 2 == 0
        print(f"🔍 DEBUG: Player {player_id} history length: {len(history)}, should_summarize: {should_summarize}")
        return should_summarize

    async def summarize_and_prune_context(self, player_id: str, personality: str, play_style: str, model: str = "gpt-4o-mini"):
        """
        Summarize the first 2 turns and delete them, using agent personality for reflection.
        
        Args:
            player_id: The ID of the player
            personality: The player's personality
            play_style: The player's play style
            model: The model to use for summarization
        """
        from .openai_api_call import call_openai_api
        
        history = self.get_conversation_history(player_id)
        if len(history) < 2:
            return
        
        # Get first 2 turns to summarize
        turns_to_summarize = history[:2]
        
        # Get existing summary if it exists
        existing_summary = self.get_player_summary(player_id)
        
        # Create summarization prompt
        summarization_prompt = f"""You are {player_id} reflecting on your game experience so far. 

YOUR PERSONALITY: {personality}
YOUR PLAY STYLE: {play_style}

"""
        
        # Include previous summary if it exists
        if existing_summary and 'summary' in existing_summary:
            print(f"🔍 DEBUG: Including previous summary for {player_id} in new summarization")
            summarization_prompt += f"""PREVIOUS INSIGHTS (build upon these):
{json.dumps(existing_summary['summary'], indent=2)}

"""
        
        summarization_prompt += """Based on the following game history, create a structured reflection that BUILDS UPON your previous insights (if any) about:
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

IMPORTANT: If you have previous insights, UPDATE and INTEGRATE them with new observations. Don't just repeat old information - refine, expand, and correct your understanding based on new evidence.

Respond only with valid JSON."""
        
        # Call OpenAI API for summarization
        try:
            response = await call_openai_api(
                prompt=summarization_prompt,
                model=model,
                max_tokens=2000,
                temperature=0.7
            )
            
            summary = json.loads(response)
            
            # Store the summary
            self.player_summaries[player_id] = {
                "summary": summary,
                "summarized_turns": len(turns_to_summarize),
                "last_updated": self.game_state_manager.get_turn_number()
            }
            
            # Remove the summarized turns from history
            self.conversation_history[player_id] = history[2:]
            
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

THE GOAL: Get rid of all your cards before other players do.

GAME RULES:
- Players take turns playing cards face-down, claiming they are of the expected rank
- You can tell the truth OR bluff about what cards you're playing
- After someone plays, any player can call "BS" if they think the person was lying
- If BS is called correctly, the liar takes all cards from the center pile
- If BS is called incorrectly, the caller takes all cards from the center pile
- First player to get rid of all their cards wins

🎯 STRATEGIC ADVANTAGE OF CALLING BS:
- Calling BS is a powerful offensive weapon that can dramatically shift the game
- When you call BS correctly, your opponent takes ALL {context['center_pile_count']} cards from the center pile
- This eliminates competition and puts you closer to victory
- Players who never call BS are predictable and easy to exploit
- Bold BS calls create psychological pressure and force opponents to play more honestly
- The best players call BS frequently to maintain table control and intimidate opponents
- Don't let bluffers get away with obvious lies - challenge them aggressively!

CURRENT GAME STATE:
- You are: {player_id}
- Turn number: {context['turn_number']}
- Current player: {context['current_player']}
- Expected rank for this turn: {context['expected_rank_name']}
- Cards in center pile: {context['center_pile_count']} (THIS IS HOW MANY CARDS YOUR OPPONENT WILL TAKE IF YOU CATCH THEM LYING!)
- Your hand size: {context['hand_count']}"""

        # Add hand information
        hand_info = self._format_hand_info(context['hand'])
        base_prompt += f"\n- Your cards: {hand_info}"
        
        # Add other players' information
        other_players_info = []
        for pid, count in context['other_players_hand_counts'].items():
            other_players_info.append(f"{pid}: {count} cards")
        base_prompt += f"\n- Other players: {', '.join(other_players_info)}"
        
        # Add comprehensive game history
        game_history = self.get_game_history_summary()
        base_prompt += f"\n\nGAME HISTORY (what everyone can observe):\n{game_history}"
        
        # Add player behavior patterns
        behavior_summary = self.get_player_behavior_summary()
        base_prompt += f"\n\nPLAYER BEHAVIOR PATTERNS:\n{behavior_summary}"
        
        # Add recent action if available
        if context['last_action']:
            base_prompt += f"\n\nMOST RECENT ACTION: {context['last_action']}"
        
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
- You can tell the truth or bluff - both are valid strategies"""
        else:
            next_player = self.game_state_manager.get_next_player()
            base_prompt += f"""

IT'S NOT YOUR TURN:
- {context['current_player']} just played cards claiming they were {context['expected_rank_name']}s
- Only the next player in turn order ({next_player}) can call BS
- If you are {next_player}, you can call BS if you think they were lying
- If you are not {next_player}, you must wait for your turn

🔥 TIME TO CALL BS - STRIKE WHILE THE IRON IS HOT:
- Trust your instincts! If something feels off about their claim, call BS immediately
- Every hesitation gives your opponents confidence to keep bluffing
- The risk of taking {context['center_pile_count']} cards is worth the reward of catching a liar
- Aggressive BS calling builds your reputation as someone not to mess with
- Most players are bluffing more than they're telling the truth - exploit this weakness!
- Don't overthink it - if you suspect BS, call it out and take control of the game!"""
        
        # Add personality and play style
        if personality:
            base_prompt += f"\n\nYOUR PERSONALITY: {personality}"
        
        if play_style:
            base_prompt += f"\n\nYOUR PLAY STYLE: {play_style}"
        
        # Simple reminders without strategic guidance
        base_prompt += f"""

REMEMBER:
- Play according to your personality and instincts
- Use function calls to take your action
- Always provide reasoning for your decisions
- CALLING BS SUCCESSFULLY ELIMINATES COMPETITION AND ADVANCES YOUR POSITION!
- Catching liars is just as important as getting rid of your own cards
- When in doubt about calling BS, TRUST YOUR GUT and make the aggressive play!"""
        
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
            "hand_size": context["hand_count"],
            "other_players_hand_counts": context["other_players_hand_counts"],
            "center_pile_size": context["center_pile_count"],
            "current_player": context["current_player"],
            "is_my_turn": context["is_my_turn"],
            "expected_rank": context["expected_rank_name"],
            "turn_number": context["turn_number"],
            "last_action": context["last_action"],
            "game_phase": context["game_phase"],
            "winner": context["winner"]
        } 