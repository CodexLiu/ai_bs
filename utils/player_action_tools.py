from typing import Dict, List, Any

def get_player_action_tools() -> List[Dict[str, Any]]:
    """
    Returns the OpenAI function calling tools for BS card game player actions.
    These tools define the available actions a player can take during the game.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "play_cards",
                "description": "Play cards from your hand, claiming they are of the expected rank. You can tell the truth or bluff.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of 0-based indices of cards in your hand to play (e.g., [0, 2, 5] to play the 1st, 3rd, and 6th cards)"
                        },
                        "claimed_count": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 4,
                            "description": "Number of cards you claim to be playing (must match the actual number of cards)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of your strategy for this play (e.g., 'Playing truthfully' or 'Bluffing to get rid of cards')"
                        }
                    },
                    "required": ["card_indices", "claimed_count", "reasoning"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "call_bs",
                "description": "Call BS on the previous player's claim if you think they were lying about their cards. You can only call BS if you are the next player in the turn order. You cannot call BS on yourself or when it's your turn to play.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why you think the previous player was bluffing (e.g., 'They claimed 4 Aces but I have 3 Aces' or 'Suspicious behavior')"
                        }
                    },
                    "required": ["reasoning"]
                }
            }
        }
    ]

def create_tool_mapping() -> Dict[str, str]:
    """
    Creates a mapping of tool names to their descriptions for easy reference.
    """
    return {
        "play_cards": "Play cards from hand with a claim about their rank",
        "call_bs": "Challenge the previous player's claim"
    }

def validate_play_cards_action(card_indices: List[int], claimed_count: int, hand_size: int) -> tuple[bool, str]:
    """
    Validates a play_cards action before execution.
    
    Args:
        card_indices: List of card indices to play
        claimed_count: Number of cards claimed
        hand_size: Size of player's hand
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not card_indices:
        return False, "Must specify at least one card to play"
    
    if len(card_indices) != claimed_count:
        return False, f"Card indices count ({len(card_indices)}) must match claimed count ({claimed_count})"
    
    if any(idx < 0 or idx >= hand_size for idx in card_indices):
        return False, f"Card indices must be between 0 and {hand_size - 1}"
    
    if len(set(card_indices)) != len(card_indices):
        return False, "Cannot play the same card twice"
    
    if claimed_count < 1 or claimed_count > 4:
        return False, "Must claim between 1 and 4 cards"
    
    return True, ""

def validate_call_bs_action(current_player: str, caller_id: str, center_pile_count: int, next_player: str) -> tuple[bool, str]:
    """
    Validates a call_bs action before execution.
    
    Args:
        current_player: ID of the current player
        caller_id: ID of the player calling BS
        center_pile_count: Number of cards in center pile
        next_player: ID of the next player in turn order
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if center_pile_count == 0:
        return False, "Cannot call BS when no cards have been played"
    
    if current_player == caller_id:
        return False, "Cannot call BS on yourself"
    
    if caller_id != next_player:
        return False, "Only the next player in turn order can call BS"
    
    return True, "" 