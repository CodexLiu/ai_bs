from typing import List, Dict, Any, Tuple, Optional
from .card_system import Card, Rank, Suit
from .game_state_manager import GameStateManager

def validate_card_play(cards: List[Card], claimed_rank: Rank, expected_rank: Rank) -> Tuple[bool, str]:
    """
    Validate if a card play is legal according to BS rules.
    
    Args:
        cards: List of cards being played
        claimed_rank: Rank claimed by the player
        expected_rank: Rank expected for this turn
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not cards:
        return False, "Must play at least one card"
    
    if len(cards) > 4:
        return False, "Cannot play more than 4 cards at once"
    
    if claimed_rank != expected_rank:
        return False, f"Must claim {expected_rank.name} cards, not {claimed_rank.name}"
    
    return True, ""

def is_bluffing(cards: List[Card], claimed_rank: Rank) -> bool:
    """
    Check if a player is bluffing based on their actual cards vs claimed rank.
    
    Args:
        cards: Actual cards played
        claimed_rank: Rank claimed by the player
        
    Returns:
        True if player is bluffing, False if telling the truth
    """
    return not all(card.rank == claimed_rank for card in cards)

def calculate_bluff_probability(player_hand: List[Card], claimed_rank: Rank, claimed_count: int) -> float:
    """
    Calculate the probability that a player is bluffing based on cards in hand.
    
    Args:
        player_hand: Cards in the observer's hand
        claimed_rank: Rank claimed by the other player
        claimed_count: Number of cards claimed
        
    Returns:
        Probability (0.0 to 1.0) that the player is bluffing
    """
    # Count how many of the claimed rank the observer has
    observer_count = sum(1 for card in player_hand if card.rank == claimed_rank)
    
    # Total possible cards of that rank
    total_possible = 4
    
    # Cards of that rank not in observer's hand
    remaining_possible = total_possible - observer_count
    
    # If the claimed count exceeds what's possible, it's definitely a bluff
    if claimed_count > remaining_possible:
        return 1.0
    
    # Simple probability calculation
    # More cards in observer's hand = higher chance opponent is bluffing
    if remaining_possible == 0:
        return 1.0
    
    # Basic probability: higher claim against fewer available cards = more likely bluff
    probability = min(0.9, (claimed_count / remaining_possible) * 0.7)
    
    return probability

def get_next_rank(current_rank: Rank) -> Rank:
    """
    Get the next rank in the sequence (Ace -> 2 -> 3 -> ... -> King -> Ace).
    
    Args:
        current_rank: Current rank
        
    Returns:
        Next rank in sequence
    """
    next_value = current_rank.value + 1
    if next_value > 13:
        next_value = 1
    return Rank(next_value)

def get_previous_rank(current_rank: Rank) -> Rank:
    """
    Get the previous rank in the sequence.
    
    Args:
        current_rank: Current rank
        
    Returns:
        Previous rank in sequence
    """
    prev_value = current_rank.value - 1
    if prev_value < 1:
        prev_value = 13
    return Rank(prev_value)

def count_cards_by_rank(cards: List[Card]) -> Dict[Rank, int]:
    """
    Count cards by rank.
    
    Args:
        cards: List of cards
        
    Returns:
        Dictionary mapping ranks to counts
    """
    counts = {}
    for card in cards:
        counts[card.rank] = counts.get(card.rank, 0) + 1
    return counts

def format_cards_for_display(cards: List[Card]) -> str:
    """
    Format cards for display in a readable way.
    
    Args:
        cards: List of cards
        
    Returns:
        Formatted string representation
    """
    if not cards:
        return "No cards"
    
    # Group by rank
    rank_counts = count_cards_by_rank(cards)
    
    # Format as "2 Aces, 1 King, 3 Sevens"
    parts = []
    for rank, count in sorted(rank_counts.items(), key=lambda x: x[0].value):
        rank_name = get_rank_display_name(rank)
        if count == 1:
            parts.append(f"1 {rank_name}")
        else:
            parts.append(f"{count} {rank_name}s")
    
    return ", ".join(parts)

def get_rank_display_name(rank: Rank) -> str:
    """
    Get the display name for a rank.
    
    Args:
        rank: The rank
        
    Returns:
        Display name (e.g., "Ace", "King", "7")
    """
    display_names = {
        Rank.ACE: "Ace",
        Rank.TWO: "2",
        Rank.THREE: "3",
        Rank.FOUR: "4",
        Rank.FIVE: "5",
        Rank.SIX: "6",
        Rank.SEVEN: "7",
        Rank.EIGHT: "8",
        Rank.NINE: "9",
        Rank.TEN: "10",
        Rank.JACK: "Jack",
        Rank.QUEEN: "Queen",
        Rank.KING: "King"
    }
    return display_names.get(rank, str(rank.value))

def get_optimal_play_suggestion(hand: List[Card], expected_rank: Rank) -> Dict[str, Any]:
    """
    Suggest an optimal play based on the current hand and expected rank.
    
    Args:
        hand: Player's current hand
        expected_rank: The rank expected for this turn
        
    Returns:
        Dictionary with play suggestion
    """
    # Count cards of the expected rank
    expected_cards = [card for card in hand if card.rank == expected_rank]
    
    if expected_cards:
        # Have the expected rank - suggest playing truthfully
        return {
            "strategy": "truthful",
            "cards_to_play": len(expected_cards),
            "confidence": 0.9,
            "reasoning": f"Have {len(expected_cards)} {get_rank_display_name(expected_rank)}(s) - play truthfully"
        }
    else:
        # Don't have the expected rank - suggest bluffing
        # Find cards that are close in value or least useful
        candidates = sorted(hand, key=lambda x: abs(x.rank.value - expected_rank.value))
        
        return {
            "strategy": "bluff",
            "cards_to_play": 1,  # Start with 1 card bluff
            "confidence": 0.6,
            "reasoning": f"Don't have {get_rank_display_name(expected_rank)}s - bluff with 1 card"
        }

def analyze_game_state(game_state: GameStateManager, player_id: str) -> Dict[str, Any]:
    """
    Analyze the current game state from a player's perspective.
    
    Args:
        game_state: Current game state
        player_id: ID of the player
        
    Returns:
        Dictionary with game analysis
    """
    context = game_state.get_game_context_for_player(player_id)
    
    # Analyze hand composition
    hand = context["hand"]
    hand_analysis = {
        "total_cards": len(hand),
        "rank_distribution": count_cards_by_rank(hand),
        "has_expected_rank": any(card.rank == context["expected_rank"] for card in hand),
        "expected_rank_count": sum(1 for card in hand if card.rank == context["expected_rank"])
    }
    
    # Analyze game position
    position_analysis = {
        "is_winning": len(hand) <= 3,  # Close to winning
        "is_losing": len(hand) > 15,   # Far from winning
        "turn_position": context["turn_number"],
        "players_ahead": sum(1 for count in context["other_players_hand_counts"].values() if count < len(hand)),
        "players_behind": sum(1 for count in context["other_players_hand_counts"].values() if count > len(hand))
    }
    
    # Risk assessment
    risk_analysis = {
        "center_pile_risk": context["center_pile_count"],  # More cards = higher risk if caught
        "bluff_risk": "low" if hand_analysis["has_expected_rank"] else "high",
        "call_bs_risk": "medium"  # Default medium risk for calling BS
    }
    
    return {
        "hand_analysis": hand_analysis,
        "position_analysis": position_analysis,
        "risk_analysis": risk_analysis,
        "recommendations": _get_strategy_recommendations(hand_analysis, position_analysis, risk_analysis)
    }

def _get_strategy_recommendations(hand_analysis: Dict, position_analysis: Dict, risk_analysis: Dict) -> List[str]:
    """Generate strategy recommendations based on analysis"""
    recommendations = []
    
    if hand_analysis["has_expected_rank"]:
        recommendations.append("Play truthfully - you have the expected rank")
    
    if position_analysis["is_winning"]:
        recommendations.append("Play aggressively - you're close to winning")
    
    if risk_analysis["center_pile_risk"] > 10:
        recommendations.append("Be cautious - large center pile means high penalty if caught")
    
    if position_analysis["players_ahead"] > 2:
        recommendations.append("Take more risks - you're falling behind")
    
    return recommendations

def simulate_bs_call_outcome(cards_played: List[Card], claimed_rank: Rank) -> Dict[str, Any]:
    """
    Simulate the outcome of a BS call.
    
    Args:
        cards_played: The actual cards that were played
        claimed_rank: The rank that was claimed
        
    Returns:
        Dictionary with simulation results
    """
    was_bluff = is_bluffing(cards_played, claimed_rank)
    
    return {
        "was_bluff": was_bluff,
        "cards_revealed": [str(card) for card in cards_played],
        "actual_ranks": [card.rank for card in cards_played],
        "claimed_rank": claimed_rank,
        "outcome": "BS call correct" if was_bluff else "BS call incorrect"
    } 