import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    PLAY = "play"

class GameLogger:
    def __init__(self, mode: LogLevel = LogLevel.PLAY):
        self.mode = mode
        self.game_log = []
        self.start_time = datetime.now()
        self.turn_log = []
        
    def log_game_start(self, player_ids: List[str], game_settings: Dict[str, Any] = None):
        """Log the start of a new game"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "game_start",
            "players": player_ids,
            "settings": game_settings or {},
            "mode": self.mode.value
        }
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            print(f"🎮 Game started with players: {', '.join(player_ids)}")
        elif self.mode == LogLevel.DEBUG:
            print(f"DEBUG: Game started - {json.dumps(log_entry, indent=2)}")
    
    def log_turn_start(self, turn_number: int, player_id: str, game_state: Dict[str, Any]):
        """Log the start of a player's turn"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "turn_start",
            "turn_number": turn_number,
            "player": player_id,
            "game_state": game_state
        }
        self.turn_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            print(f"\n🎯 Turn {turn_number}: {player_id}'s turn")
            print(f"   Expected rank: {game_state.get('expected_rank', 'Unknown')}")
            print(f"   Cards in center: {game_state.get('center_pile_size', 0)}")
        elif self.mode == LogLevel.DEBUG:
            print(f"DEBUG: Turn start - {json.dumps(log_entry, indent=2)}")
    
    def log_ai_action(self, player_id: str, action_result: Dict[str, Any]):
        """Log an AI player's action and reasoning"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "ai_action",
            "player": player_id,
            "action": action_result.get("action"),
            "parameters": action_result.get("parameters", {}),
            "reasoning": action_result.get("reasoning", ""),
            "validation": action_result.get("validation", {})
        }
        
        if self.mode == LogLevel.DEBUG:
            log_entry["debug_info"] = action_result.get("debug_info", {})
        
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            self._print_play_action(player_id, action_result)
        elif self.mode == LogLevel.DEBUG:
            self._print_debug_action(player_id, action_result)
    
    def _print_play_action(self, player_id: str, action_result: Dict[str, Any]):
        """Print action in play mode"""
        action = action_result.get("action")
        parameters = action_result.get("parameters", {})
        reasoning = action_result.get("reasoning", "")
        
        if action == "play_cards":
            count = parameters.get("claimed_count", 0)
            print(f"   🃏 {player_id} plays {count} cards")
            if reasoning:
                print(f"      Reasoning: {reasoning}")
        elif action == "call_bs":
            print(f"   🚨 {player_id} calls BS!")
            if reasoning:
                print(f"      Reasoning: {reasoning}")
        elif action == "pass_turn":
            print(f"   ⏭️ {player_id} passes")
            if reasoning:
                print(f"      Reasoning: {reasoning}")
        elif action == "error":
            print(f"   ❌ {player_id} error: {action_result.get('error', 'Unknown error')}")
    
    def _print_debug_action(self, player_id: str, action_result: Dict[str, Any]):
        """Print action in debug mode"""
        print(f"DEBUG: AI Action for {player_id}")
        print(f"  Action: {action_result.get('action')}")
        print(f"  Parameters: {json.dumps(action_result.get('parameters', {}), indent=4)}")
        print(f"  Reasoning: {action_result.get('reasoning', '')}")
        print(f"  Validation: {json.dumps(action_result.get('validation', {}), indent=4)}")
        
        if "debug_info" in action_result:
            print(f"  Debug Info: {json.dumps(action_result['debug_info'], indent=4)}")
    
    def log_action_result(self, player_id: str, success: bool, message: str):
        """Log the result of an action execution"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "action_result",
            "player": player_id,
            "success": success,
            "message": message
        }
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            if success:
                print(f"   ✅ {message}")
            else:
                print(f"   ❌ {message}")
        elif self.mode == LogLevel.DEBUG:
            print(f"DEBUG: Action result - {json.dumps(log_entry, indent=2)}")
    
    def log_bs_call_result(self, caller: str, target: str, was_bs: bool, cards_revealed: List[str]):
        """Log the result of a BS call"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "bs_call_result",
            "caller": caller,
            "target": target,
            "was_bs": was_bs,
            "cards_revealed": cards_revealed
        }
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            if was_bs:
                print(f"   🎯 Correct! {target} was bluffing")
                print(f"   📄 Cards revealed: {', '.join(cards_revealed)}")
                print(f"   📚 {target} takes all center pile cards")
            else:
                print(f"   💥 Wrong! {target} was telling the truth")
                print(f"   📄 Cards revealed: {', '.join(cards_revealed)}")
                print(f"   📚 {caller} takes all center pile cards")
        elif self.mode == LogLevel.DEBUG:
            print(f"DEBUG: BS call result - {json.dumps(log_entry, indent=2)}")
    
    def log_game_state_change(self, event: str, details: Dict[str, Any]):
        """Log a general game state change"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details
        }
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.DEBUG:
            print(f"DEBUG: Game state change - {json.dumps(log_entry, indent=2)}")
    
    def log_game_end(self, winner: str, final_state: Dict[str, Any]):
        """Log the end of the game"""
        game_duration = datetime.now() - self.start_time
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "game_end",
            "winner": winner,
            "duration_seconds": game_duration.total_seconds(),
            "final_state": final_state
        }
        self.game_log.append(log_entry)
        
        if self.mode == LogLevel.PLAY:
            print(f"\n🏆 Game Over! {winner} wins!")
            print(f"⏱️ Game duration: {game_duration.total_seconds():.1f} seconds")
        elif self.mode == LogLevel.DEBUG:
            print(f"DEBUG: Game end - {json.dumps(log_entry, indent=2)}")
    
    def log_error(self, error_type: str, message: str, details: Dict[str, Any] = None):
        """Log an error"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "error_type": error_type,
            "message": message,
            "details": details or {}
        }
        self.game_log.append(log_entry)
        
        print(f"❌ ERROR ({error_type}): {message}")
        if self.mode == LogLevel.DEBUG and details:
            print(f"    Details: {json.dumps(details, indent=4)}")
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get a summary of the game"""
        turns = len([log for log in self.game_log if log["event"] == "turn_start"])
        actions = len([log for log in self.game_log if log["event"] == "ai_action"])
        bs_calls = len([log for log in self.game_log if log["event"] == "bs_call_result"])
        errors = len([log for log in self.game_log if log["event"] == "error"])
        
        return {
            "total_turns": turns,
            "total_actions": actions,
            "bs_calls": bs_calls,
            "errors": errors,
            "game_duration": (datetime.now() - self.start_time).total_seconds()
        }
    
    def export_log(self, filename: str):
        """Export the game log to a file"""
        with open(filename, 'w') as f:
            json.dump({
                "game_log": self.game_log,
                "summary": self.get_game_summary()
            }, f, indent=2)
        
        print(f"📄 Game log exported to {filename}")
    
    def print_game_summary(self):
        """Print a summary of the game"""
        summary = self.get_game_summary()
        print(f"\n📊 Game Summary:")
        print(f"   Total turns: {summary['total_turns']}")
        print(f"   Total actions: {summary['total_actions']}")
        print(f"   BS calls: {summary['bs_calls']}")
        print(f"   Errors: {summary['errors']}")
        print(f"   Duration: {summary['game_duration']:.1f} seconds") 