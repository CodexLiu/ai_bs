import json
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
import os
from .context_manager import ContextManager
from .player_action_tools import get_player_action_tools, validate_play_cards_action, validate_call_bs_action
from .card_system import Card, Rank

class AIPlayer:
    def __init__(self, 
                 player_id: str, 
                 context_manager: ContextManager, 
                 personality: str = "",
                 play_style: str = "",
                 openai_client: Optional[OpenAI] = None):
        self.player_id = player_id
        self.context_manager = context_manager
        self.personality = personality
        self.play_style = play_style
        self.client = openai_client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tools = get_player_action_tools()
        
        # Track conversation history for this player
        self.conversation_history = []
        
    def get_action(self, debug_mode: bool = False) -> Dict[str, Any]:
        """
        Get the AI player's action for the current turn.
        
        Args:
            debug_mode: Whether to include debug information in the response
            
        Returns:
            Dictionary containing action type, parameters, and metadata
        """
        try:
            # Generate system prompt with current game state
            system_prompt = self.context_manager.generate_system_prompt(
                self.player_id, 
                self.personality, 
                self.play_style
            )
            
            # Create conversation input
            conversation_input = [{
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}]
            }]
            
            # Add game state update
            game_context = self.context_manager.generate_conversation_context(self.player_id)
            conversation_input.extend(game_context)
            
            # Make API call with function calling
            response = self.client.responses.create(
                model="gpt-4o",  # Using gpt-4o as specified in user rules
                input=conversation_input,
                tools=self.tools,
                temperature=0.8,  # Some randomness for varied play
                max_output_tokens=1000
            )
            
            # Process response
            action_result = self._process_ai_response(response, debug_mode)
            
            return action_result
            
        except Exception as e:
            return {
                "action": "error",
                "error": str(e),
                "player_id": self.player_id
            }
    
    def _process_ai_response(self, response, debug_mode: bool) -> Dict[str, Any]:
        """
        Process the AI response and extract the action.
        
        Args:
            response: OpenAI API response
            debug_mode: Whether to include debug information
            
        Returns:
            Dictionary containing the processed action
        """
        result = {
            "player_id": self.player_id,
            "action": None,
            "parameters": {},
            "reasoning": "",
            "raw_response": None
        }
        
        if debug_mode:
            result["debug_info"] = {
                "response_output": [item.model_dump() for item in response.output],
                "token_usage": response.usage.model_dump() if hasattr(response, 'usage') else None
            }
        
        # Look for function calls in response
        function_calls = [item for item in response.output if item.type == 'function_call']
        
        if function_calls:
            # Process the first function call
            function_call = function_calls[0]
            
            try:
                arguments = json.loads(function_call.arguments)
                result["action"] = function_call.name
                result["parameters"] = arguments
                result["reasoning"] = arguments.get("reasoning", "")
                
                # Validate the action
                validation_result = self._validate_action(result["action"], result["parameters"])
                result["validation"] = validation_result
                
            except json.JSONDecodeError as e:
                result["action"] = "error"
                result["error"] = f"Failed to parse function arguments: {e}"
        
        else:
            # No function call - look for text response
            text_outputs = [item for item in response.output if item.type == 'message']
            if text_outputs:
                result["action"] = "text_response"
                result["text"] = text_outputs[0].content[0].text
            else:
                result["action"] = "error"
                result["error"] = "No valid action found in AI response"
        
        return result
    
    def _validate_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the AI's chosen action.
        
        Args:
            action: The action name
            parameters: The action parameters
            
        Returns:
            Dictionary containing validation results
        """
        validation = {"is_valid": False, "error": ""}
        
        game_context = self.context_manager.get_game_state_summary(self.player_id)
        
        if action == "play_cards":
            if not game_context["is_my_turn"]:
                validation["error"] = "Not your turn to play cards"
                return validation
            
            card_indices = parameters.get("card_indices", [])
            claimed_count = parameters.get("claimed_count", 0)
            hand_size = game_context["hand_size"]
            
            is_valid, error = validate_play_cards_action(card_indices, claimed_count, hand_size)
            validation["is_valid"] = is_valid
            validation["error"] = error
            
        elif action == "call_bs":
            if game_context["is_my_turn"]:
                validation["error"] = "Cannot call BS on your own turn"
                return validation
            
            current_player = game_context["current_player"]
            center_pile_size = game_context["center_pile_size"]
            
            is_valid, error = validate_call_bs_action(current_player, self.player_id, center_pile_size)
            validation["is_valid"] = is_valid
            validation["error"] = error
            
        elif action == "pass_turn":
            if game_context["is_my_turn"]:
                validation["error"] = "Cannot pass when it's your turn to play"
                return validation
            
            validation["is_valid"] = True
            
        else:
            validation["error"] = f"Unknown action: {action}"
        
        return validation
    
    def execute_action(self, action_result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Execute the validated action through the game state manager.
        
        Args:
            action_result: The action result from get_action()
            
        Returns:
            Tuple of (success, message)
        """
        if action_result["action"] == "error":
            return False, action_result.get("error", "Unknown error")
        
        if not action_result.get("validation", {}).get("is_valid", False):
            return False, action_result.get("validation", {}).get("error", "Invalid action")
        
        action = action_result["action"]
        parameters = action_result["parameters"]
        
        if action == "play_cards":
            return self._execute_play_cards(parameters)
        elif action == "call_bs":
            return self._execute_call_bs(parameters)
        elif action == "pass_turn":
            return True, f"{self.player_id} passed their turn"
        else:
            return False, f"Cannot execute action: {action}"
    
    def _execute_play_cards(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute play_cards action"""
        card_indices = parameters["card_indices"]
        claimed_count = parameters["claimed_count"]
        
        # Get player's hand
        game_context = self.context_manager.game_state_manager.get_game_context_for_player(self.player_id)
        hand = game_context["hand"]
        
        # Get cards to play
        cards_to_play = [hand[i] for i in card_indices]
        
        # Get expected rank
        expected_rank = self.context_manager.game_state_manager.get_expected_rank()
        
        # Execute through game state manager
        success = self.context_manager.game_state_manager.play_cards(
            self.player_id, 
            cards_to_play, 
            expected_rank, 
            claimed_count
        )
        
        if success:
            return True, f"{self.player_id} played {claimed_count} cards"
        else:
            return False, "Failed to play cards"
    
    def _execute_call_bs(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute call_bs action"""
        success, message = self.context_manager.game_state_manager.call_bs(self.player_id)
        return success, message
    
    def get_player_info(self) -> Dict[str, Any]:
        """Get information about this AI player"""
        return {
            "player_id": self.player_id,
            "personality": self.personality,
            "play_style": self.play_style,
            "game_state": self.context_manager.get_game_state_summary(self.player_id)
        } 