import time
from typing import Dict, List, Any, Optional, Callable
from .game_state_manager import GameStateManager
from .context_manager import ContextManager
from .ai_player import AIPlayer
from .game_logger import GameLogger, LogLevel

class GameOrchestrator:
    def __init__(self, 
                 player_configs: List[Dict[str, str]], 
                 log_mode: LogLevel = LogLevel.PLAY,
                 action_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the game orchestrator.
        
        Args:
            player_configs: List of player configurations with id, personality, play_style
            log_mode: Logging mode (DEBUG or PLAY)
            action_callback: Optional callback function for game actions
        """
        self.player_configs = player_configs
        self.player_ids = [config["id"] for config in player_configs]
        self.action_callback = action_callback
        
        # Initialize game components
        self.game_state = GameStateManager(self.player_ids)
        self.context_manager = ContextManager(self.game_state)
        self.logger = GameLogger(log_mode)
        
        # Initialize AI players
        self.players = {}
        for config in player_configs:
            self.players[config["id"]] = AIPlayer(
                player_id=config["id"],
                context_manager=self.context_manager,
                personality=config.get("personality", ""),
                play_style=config.get("play_style", ""),
                model=config.get("model", "gpt-4o-mini")
            )
        
        # Game flow control
        self.max_turns = 1000  # Prevent infinite games
        self.turn_delay = 5.0  # 5 second delay between turns for animations
        
        # Web interface support
        self.current_action = None
        self.last_bs_call = None
        
    def _notify_action(self, action_type: str, data: Dict[str, Any]):
        """Notify web interface of game action"""
        if self.action_callback:
            action_data = {
                "type": action_type,
                "data": data,
                "timestamp": time.time(),
                "turn_number": self.game_state.game_state.turn_number
            }
            self.action_callback(action_data)
        
    def run_game(self) -> Dict[str, Any]:
        """
        Run the complete game from start to finish.
        
        Returns:
            Dictionary containing game results
        """
        # Log game start
        self.logger.log_game_start(
            self.player_ids,
            {
                "max_turns": self.max_turns,
                "turn_delay": self.turn_delay
            }
        )
        
        # Game loop
        turn_count = 0
        while not self.game_state.is_game_over() and turn_count < self.max_turns:
            turn_count += 1
            
            # Process turn
            self._process_turn(turn_count)
            
            # Add delay for readability
            if self.turn_delay > 0:
                time.sleep(self.turn_delay)
        
        # Handle game end
        return self._handle_game_end(turn_count)
    
    def _process_turn(self, turn_number: int):
        """Process a single turn"""
        current_player_id = self.game_state.get_current_player()
        current_player = self.players[current_player_id]
        
        # Log turn start
        game_state_summary = self.context_manager.get_game_state_summary(current_player_id)
        self.logger.log_turn_start(turn_number, current_player_id, game_state_summary)
        
        # Notify web interface
        self._notify_action("turn_start", {
            "player_id": current_player_id,
            "turn_number": turn_number,
            "expected_rank": self.game_state.get_expected_rank_name()
        })
        
        # In debug mode, show all player hands
        if self.logger.mode == LogLevel.DEBUG:
            self.logger.log_player_hands(self.game_state.game_state.player_hands)
        
        # Current player MUST play cards - no other actions allowed
        max_attempts = 3
        for attempt in range(max_attempts):
            # Get action from current player
            action_result = current_player.get_action(debug_mode=(self.logger.mode == LogLevel.DEBUG))
            
            # Log the action
            self.logger.log_ai_action(current_player_id, action_result)
            
            # Enforce that current player can only play cards
            if action_result.get("action") != "play_cards":
                error_msg = f"When it's your turn, you MUST play cards. Cannot {action_result.get('action', 'perform unknown action')}"
                self.logger.log_action_result(current_player_id, False, error_msg)
                if attempt == max_attempts - 1:
                    # Force a default play after max attempts
                    self.logger.log_action_result(current_player_id, False, "Max attempts reached, forcing default play")
                    break
                continue
            
            # Store current action for web interface
            self.current_action = action_result
            
            # Execute the play_cards action
            success, message = current_player.execute_action(action_result)
            
            # Log the result
            self.logger.log_action_result(current_player_id, success, message)
            
            if success:
                # Notify web interface of card play
                claimed_count = action_result.get("parameters", {}).get("claimed_count", 0)
                reasoning = action_result.get("parameters", {}).get("reasoning", "")
                
                # Determine if this was truthful or a bluff
                card_indices = action_result.get("parameters", {}).get("card_indices", [])
                player_hand = self.game_state.game_state.player_hands[current_player_id]
                expected_rank = self.game_state.get_expected_rank()
                
                if card_indices:
                    # Get the actual cards played (before they were removed from hand)
                    # We need to reconstruct this from the center pile
                    last_play = self.game_state.game_state.center_pile[-1] if self.game_state.game_state.center_pile else None
                    actual_cards = last_play.cards if last_play else []
                    
                    is_truthful = all(card.rank == expected_rank for card in actual_cards)
                    
                    action_message = f"{current_player_id} played {claimed_count} card{'s' if claimed_count != 1 else ''}"
                    if is_truthful:
                        action_message += f" truthfully ({self.game_state.get_expected_rank_name()}{'s' if claimed_count != 1 else ''})"
                    else:
                        actual_cards_str = ", ".join([f"{card.rank.value}" for card in actual_cards])
                        action_message += f" bluffed ({actual_cards_str} as {self.game_state.get_expected_rank_name()}{'s' if claimed_count != 1 else ''})"
                    
                    self._notify_action("card_play", {
                        "player_id": current_player_id,
                        "claimed_count": claimed_count,
                        "claimed_rank": self.game_state.get_expected_rank_name(),
                        "is_truthful": is_truthful,
                        "actual_cards": [{"rank": card.rank.value, "suit": card.suit.value} for card in actual_cards],
                        "reasoning": reasoning,
                        "action_message": action_message
                    })
                
                # Add delay to let users see the card play result before BS call opportunity
                print(f"🔍 DEBUG: Adding {self.turn_delay}s delay before BS call opportunity")
                time.sleep(self.turn_delay)
                
                # Allow other players to call BS on this play
                bs_was_called = self._handle_potential_bs_calls(current_player_id)
                
                # Only advance turn if no BS was called (BS calls handle their own turn advancement)
                if not bs_was_called:
                    self.game_state.advance_turn()
                    
                # Add delay between turns for animations
                time.sleep(self.turn_delay)
                break
            else:
                # Play failed, try again
                if attempt == max_attempts - 1:
                    self.logger.log_action_result(current_player_id, False, "Failed to play cards after max attempts")
                    # Force game to continue by advancing turn
                    self.game_state.advance_turn()
    
    def _handle_bs_call(self, caller_id: str, action_result: Dict[str, Any], center_pile_data: Dict[str, Any]):
        """Handle the result of a BS call"""
        print(f"🔍 DEBUG: Entering _handle_bs_call with caller_id: {caller_id}")
        print(f"🔍 DEBUG: BS call action_result: {action_result}")
        print(f"🔍 DEBUG: Using captured center pile data: {len(center_pile_data['all_center_cards'])} cards")
        
        last_play = center_pile_data["last_play"]
        target_player = last_play.player_id
        
        print(f"🔍 DEBUG: Last play by {target_player}, cards: {last_play.cards}")
        
        # Get the actual cards that were played
        actual_cards = last_play.cards
        claimed_rank = last_play.claimed_rank
        
        # Check if it was actually BS
        was_bs = not all(card.rank == claimed_rank for card in actual_cards)
        
        print(f"🔍 DEBUG: Was BS? {was_bs}")
        
        # Use the captured center pile cards
        center_pile_cards = center_pile_data["all_center_cards"]
        
        # Format cards for logging
        cards_revealed = [str(card) for card in actual_cards]
        
        # Log BS call result
        self.logger.log_bs_call_result(caller_id, target_player, was_bs, cards_revealed)
        
        # Extract reasoning with debug logging - check both locations
        reasoning_from_params = action_result.get("parameters", {}).get("reasoning", "")
        reasoning_from_root = action_result.get("reasoning", "")
        
        print(f"🔍 DEBUG: Reasoning from parameters: '{reasoning_from_params}'")
        print(f"🔍 DEBUG: Reasoning from root: '{reasoning_from_root}'")
        
        # Use the first non-empty reasoning found
        reasoning = reasoning_from_params or reasoning_from_root
        
        print(f"🔍 DEBUG: Final reasoning for BS call: '{reasoning}'")
        
        # Store BS call info
        self.last_bs_call = {
            "caller": caller_id,
            "target": target_player,
            "was_bs": was_bs,
            "cards_revealed": cards_revealed,
            "reasoning": reasoning
        }
        
        # Notify web interface BEFORE updating game state
        if was_bs:
            action_message = f"{caller_id} correctly called BS on {target_player} - {target_player} takes all center pile cards"
        else:
            action_message = f"{caller_id} incorrectly called BS on {target_player} - {caller_id} takes all center pile cards"
        
        print(f"🔍 DEBUG: Sending BS call notification with reasoning: '{reasoning}'")
        
        notification_data = {
            "caller": caller_id,
            "target": target_player,
            "was_bs": was_bs,
            "cards_revealed": cards_revealed,
            "center_pile_cards": [{"suit": card.suit.value, "rank": card.rank.value} for card in center_pile_cards],
            "reasoning": reasoning,
            "action_message": action_message
        }
        
        print(f"🔍 DEBUG: Notification data: {notification_data}")
        
        self._notify_action("bs_call", notification_data)
        
        print(f"🔍 DEBUG: BS call notification sent successfully")
        
        # Add a small delay to allow frontend to set up animations
        time.sleep(0.5)
    
    def _handle_potential_bs_calls(self, current_player_id: str) -> bool:
        """Allow only the next player in turn order to call BS on the current player's move"""
        if not self.game_state.game_state.center_pile:
            return False
        
        # Only the next player in turn order can call BS
        next_player_id = self.game_state.get_next_player()
        next_player = self.players[next_player_id]
        
        # Ask the next player if they want to call BS
        action_result = next_player.get_action(debug_mode=(self.logger.mode == LogLevel.DEBUG))
        
        print(f"🔍 DEBUG: Next player ({next_player_id}) action result: {action_result}")
        
        # Only proceed if the next player wants to call BS
        if action_result.get("action") == "call_bs":
            # Log the action
            self.logger.log_ai_action(next_player_id, action_result)
            
            print(f"🔍 DEBUG: Processing BS call from {next_player_id}")
            
            # CAPTURE CENTER PILE DATA BEFORE IT GETS CLEARED BY execute_action
            center_pile_data = {
                "last_play": self.game_state.game_state.center_pile[-1],
                "all_center_cards": []
            }
            
            # Store all center pile cards for animation
            for played_cards in self.game_state.game_state.center_pile:
                center_pile_data["all_center_cards"].extend(played_cards.cards)
            
            print(f"🔍 DEBUG: Captured center pile data before execute_action")
            
            success, message = next_player.execute_action(action_result)
            self.logger.log_action_result(next_player_id, success, message)
            
            if success:
                print(f"🔍 DEBUG: BS call successful, handling result")
                # Handle BS call result with captured data
                self._handle_bs_call(next_player_id, action_result, center_pile_data)
                return True  # BS was called
            else:
                print(f"🔍 DEBUG: BS call failed: {message}")
        else:
            print(f"🔍 DEBUG: Next player ({next_player_id}) chose not to call BS, action: {action_result.get('action')}")
        
        # If next player didn't call BS or had an error, continue
        return False  # No BS was called
    
    def _handle_game_end(self, turn_count: int) -> Dict[str, Any]:
        """Handle the end of the game"""
        winner = self.game_state.get_winner()
        
        # Get final game state
        final_state = {
            "winner": winner,
            "turn_count": turn_count,
            "final_hand_counts": self.game_state.get_all_hand_counts(),
            "center_pile_count": self.game_state.get_center_pile_count(),
            "game_phase": self.game_state.game_state.game_phase.value
        }
        
        # Log game end
        self.logger.log_game_end(winner or "No winner", final_state)
        
        # Print game summary
        self.logger.print_game_summary()
        
        # Prepare results
        results = {
            "winner": winner,
            "turn_count": turn_count,
            "final_state": final_state,
            "game_log": self.logger.game_log,
            "summary": self.logger.get_game_summary()
        }
        
        return results
    
    def get_game_state_info(self) -> Dict[str, Any]:
        """Get current game state information"""
        return {
            "current_player": self.game_state.get_current_player(),
            "expected_rank": self.game_state.get_expected_rank_name(),
            "turn_number": self.game_state.get_turn_number(),
            "hand_counts": self.game_state.get_all_hand_counts(),
            "center_pile_count": self.game_state.get_center_pile_count(),
            "game_phase": self.game_state.game_state.game_phase.value,
            "winner": self.game_state.get_winner()
        }
    
    def export_game_log(self, filename: str):
        """Export the game log to a file"""
        self.logger.export_log(filename)
    
    def pause_game(self):
        """Pause the game (for debugging)"""
        input("Press Enter to continue...")
    
    def set_turn_delay(self, delay: float):
        """Set the delay between turns"""
        self.turn_delay = delay
    
    def get_player_info(self, player_id: str) -> Dict[str, Any]:
        """Get information about a specific player"""
        if player_id not in self.players:
            return {"error": f"Player {player_id} not found"}
        
        return self.players[player_id].get_player_info() 

    def get_current_action_details(self) -> Dict[str, Any]:
        """Get detailed information about the current action"""
        return {
            "current_action": self.current_action,
            "last_bs_call": self.last_bs_call,
            "game_state": self.get_game_state_info()
        }

    def set_action_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for game actions"""
        self.action_callback = callback 