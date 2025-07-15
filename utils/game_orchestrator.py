import time
from typing import Dict, List, Any, Optional
from .game_state_manager import GameStateManager
from .context_manager import ContextManager
from .ai_player import AIPlayer
from .game_logger import GameLogger, LogLevel

class GameOrchestrator:
    def __init__(self, 
                 player_configs: List[Dict[str, str]], 
                 log_mode: LogLevel = LogLevel.PLAY):
        """
        Initialize the game orchestrator.
        
        Args:
            player_configs: List of player configurations with id, personality, play_style
            log_mode: Logging mode (DEBUG or PLAY)
        """
        self.player_configs = player_configs
        self.player_ids = [config["id"] for config in player_configs]
        
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
                play_style=config.get("play_style", "")
            )
        
        # Game flow control
        self.max_turns = 1000  # Prevent infinite games
        self.turn_delay = 0.5  # Delay between turns for readability
        
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
        
        # Get action from current player
        action_result = current_player.get_action(debug_mode=(self.logger.mode == LogLevel.DEBUG))
        
        # Log the action
        self.logger.log_ai_action(current_player_id, action_result)
        
        # Execute the action
        success, message = current_player.execute_action(action_result)
        
        # Log the result
        self.logger.log_action_result(current_player_id, success, message)
        
        # Handle special cases
        if action_result.get("action") == "call_bs":
            self._handle_bs_call(current_player_id, action_result)
        
        # Allow other players to call BS if current player played cards
        if action_result.get("action") == "play_cards" and success:
            self._handle_potential_bs_calls(current_player_id)
    
    def _handle_bs_call(self, caller_id: str, action_result: Dict[str, Any]):
        """Handle the result of a BS call"""
        if not self.game_state.center_pile:
            return
        
        last_play = self.game_state.center_pile[-1]
        target_player = last_play.player_id
        
        # Get the actual cards that were played
        actual_cards = last_play.cards
        claimed_rank = last_play.claimed_rank
        
        # Check if it was actually BS
        was_bs = not all(card.rank == claimed_rank for card in actual_cards)
        
        # Format cards for logging
        cards_revealed = [str(card) for card in actual_cards]
        
        # Log BS call result
        self.logger.log_bs_call_result(caller_id, target_player, was_bs, cards_revealed)
    
    def _handle_potential_bs_calls(self, current_player_id: str):
        """Allow other players to call BS on the current player's move"""
        if not self.game_state.center_pile:
            return
        
        # Give other players a chance to call BS
        for player_id in self.player_ids:
            if player_id == current_player_id:
                continue
            
            player = self.players[player_id]
            
            # Get action from player (they can call BS or pass)
            action_result = player.get_action(debug_mode=(self.logger.mode == LogLevel.DEBUG))
            
            # Log the action
            self.logger.log_ai_action(player_id, action_result)
            
            # If player calls BS, execute it and break
            if action_result.get("action") == "call_bs":
                success, message = player.execute_action(action_result)
                self.logger.log_action_result(player_id, success, message)
                
                if success:
                    # Handle BS call result
                    self._handle_bs_call(player_id, action_result)
                    break
            else:
                # Player passed or had an error
                if action_result.get("action") == "pass_turn":
                    self.logger.log_action_result(player_id, True, f"{player_id} passed")
                elif action_result.get("action") == "error":
                    error_msg = action_result.get("error", "Unknown error")
                    self.logger.log_action_result(player_id, False, f"{player_id} error: {error_msg}")
    
    def _handle_game_end(self, turn_count: int) -> Dict[str, Any]:
        """Handle the end of the game"""
        winner = self.game_state.get_winner()
        
        # Get final game state
        final_state = {
            "winner": winner,
            "turn_count": turn_count,
            "final_hand_counts": self.game_state.get_all_hand_counts(),
            "center_pile_count": self.game_state.get_center_pile_count(),
            "game_phase": self.game_state.game_phase.value
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
            "turn_number": self.game_state.turn_number,
            "hand_counts": self.game_state.get_all_hand_counts(),
            "center_pile_count": self.game_state.get_center_pile_count(),
            "game_phase": self.game_state.game_phase.value,
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