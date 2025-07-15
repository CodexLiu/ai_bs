#!/usr/bin/env python3
"""
Simple test to verify the BS game system is working correctly
"""

from utils.card_system import Deck, Card, Rank, Suit
from utils.game_state_manager import GameStateManager
from utils.context_manager import ContextManager
from utils.game_logger import GameLogger, LogLevel
from main import create_player_configs

def test_card_system():
    """Test the card system"""
    print("Testing card system...")
    
    deck = Deck()
    assert deck.remaining_cards() == 52, "Deck should have 52 cards"
    
    deck.shuffle()
    card = deck.deal_card()
    assert card is not None, "Should be able to deal a card"
    assert deck.remaining_cards() == 51, "Deck should have 51 cards after dealing one"
    
    print("✅ Card system works!")

def test_game_state_manager():
    """Test the game state manager"""
    print("Testing game state manager...")
    
    player_ids = ["alice", "marcus", "randall", "susan"]
    game_state = GameStateManager(player_ids)
    
    assert len(game_state.get_all_hand_counts()) == 4, "Should have 4 players"
    assert sum(game_state.get_all_hand_counts().values()) == 52, "All cards should be dealt"
    
    current_player = game_state.get_current_player()
    assert current_player in player_ids, "Current player should be valid"
    
    print("✅ Game state manager works!")

def test_context_manager():
    """Test the context manager"""
    print("Testing context manager...")
    
    player_ids = ["alice", "marcus", "randall", "susan"]
    game_state = GameStateManager(player_ids)
    context_manager = ContextManager(game_state)
    
    # Test system prompt generation
    system_prompt = context_manager.generate_system_prompt(
        "alice", 
        "Test personality", 
        "Test play style"
    )
    
    assert "alice" in system_prompt, "System prompt should contain player name"
    assert "Test personality" in system_prompt, "System prompt should contain personality"
    assert "Test play style" in system_prompt, "System prompt should contain play style"
    
    print("✅ Context manager works!")

def test_player_configs():
    """Test the player configurations"""
    print("Testing player configurations...")
    
    configs = create_player_configs()
    
    assert len(configs) == 4, "Should have 4 player configurations"
    
    for config in configs:
        assert "id" in config, "Config should have id"
        assert "personality" in config, "Config should have personality"
        assert "play_style" in config, "Config should have play_style"
        
        # Check that personality and play_style are not empty
        assert config["personality"].strip(), "Personality should not be empty"
        assert config["play_style"].strip(), "Play style should not be empty"
    
    print("✅ Player configurations work!")

def test_game_logger():
    """Test the game logger"""
    print("Testing game logger...")
    
    logger = GameLogger(LogLevel.PLAY)
    
    # Test basic logging
    logger.log_game_start(["alice", "marcus"])
    logger.log_turn_start(1, "alice", {"expected_rank": "Ace"})
    
    # Should not crash
    summary = logger.get_game_summary()
    assert "total_turns" in summary, "Summary should contain total_turns"
    
    print("✅ Game logger works!")

def main():
    """Run all tests"""
    print("Running BS Game System Tests...")
    print("=" * 50)
    
    try:
        test_card_system()
        test_game_state_manager()
        test_context_manager()
        test_player_configs()
        test_game_logger()
        
        print("\n🎉 All tests passed! The BS game system is ready to run.")
        print("\nTo run the game, use:")
        print("  python main.py                  # Run one game in play mode")
        print("  python main.py --mode debug     # Run one game in debug mode")
        print("  python main.py --games 5        # Run 5 games")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 