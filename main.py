#!/usr/bin/env python3
"""
BS Card Game with AI Players
Main entry point for running the game
"""

import sys
import argparse
from typing import List, Dict, Any
from utils.game_orchestrator import GameOrchestrator
from utils.game_logger import LogLevel
from characters import alice, marcus, randall, susan

def create_player_configs() -> List[Dict[str, str]]:
    """Create player configurations with character personalities"""
    
    player_configs = [
        {
            "id": "alice",
            "personality": alice.personality,
            "play_style": alice.talking_style + "\n\n" + alice.play_style
        },
        {
            "id": "marcus", 
            "personality": marcus.personality,
            "play_style": marcus.talking_style + "\n\n" + marcus.play_style
        },
        {
            "id": "randall",
            "personality": randall.personality,
            "play_style": randall.talking_style + "\n\n" + randall.play_style
        },
        {
            "id": "susan",
            "personality": susan.personality,
            "play_style": susan.talking_style + "\n\n" + susan.play_style
        }
    ]
    
    return player_configs

def run_single_game(mode: str = "play") -> Dict[str, Any]:
    """
    Run a single game of BS.
    
    Args:
        mode: "play" or "debug" logging mode
        
    Returns:
        Dictionary with game results
    """
    # Set up logging mode
    log_mode = LogLevel.DEBUG if mode == "debug" else LogLevel.PLAY
    
    # Create player configurations
    player_configs = create_player_configs()
    
    # Create and run game
    orchestrator = GameOrchestrator(player_configs, log_mode)
    
    print(f"Starting BS Card Game in {mode.upper()} mode...")
    print("=" * 50)
    
    # Run the game
    results = orchestrator.run_game()
    
    # Export log if in debug mode
    if mode == "debug":
        log_filename = f"bs_game_log_{results['turn_count']}_turns.json"
        orchestrator.export_game_log(log_filename)
    
    return results

def run_multiple_games(num_games: int, mode: str = "play") -> Dict[str, Any]:
    """
    Run multiple games and collect statistics.
    
    Args:
        num_games: Number of games to run
        mode: "play" or "debug" logging mode
        
    Returns:
        Dictionary with aggregate statistics
    """
    all_results = []
    winner_stats = {}
    
    print(f"Running {num_games} games in {mode.upper()} mode...")
    print("=" * 50)
    
    for game_num in range(1, num_games + 1):
        print(f"\n🎮 Game {game_num}/{num_games}")
        print("-" * 30)
        
        results = run_single_game(mode)
        all_results.append(results)
        
        # Track winner statistics
        winner = results.get("winner", "No winner")
        winner_stats[winner] = winner_stats.get(winner, 0) + 1
        
        print(f"Game {game_num} complete: {winner} won in {results['turn_count']} turns")
    
    # Calculate aggregate statistics
    total_turns = sum(r["turn_count"] for r in all_results)
    avg_turns = total_turns / len(all_results)
    
    aggregate_stats = {
        "total_games": num_games,
        "winner_statistics": winner_stats,
        "average_turns": avg_turns,
        "total_turns": total_turns,
        "all_results": all_results
    }
    
    print("\n🏆 Final Statistics:")
    print("=" * 50)
    print(f"Total games: {num_games}")
    print(f"Average turns per game: {avg_turns:.1f}")
    print("\nWinner Statistics:")
    for winner, count in sorted(winner_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / num_games) * 100
        print(f"  {winner}: {count} wins ({percentage:.1f}%)")
    
    return aggregate_stats

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run BS Card Game with AI Players")
    parser.add_argument("--mode", choices=["play", "debug"], default="play",
                        help="Logging mode: 'play' for normal output, 'debug' for detailed output")
    parser.add_argument("--games", type=int, default=1,
                        help="Number of games to run (default: 1)")
    parser.add_argument("--export-log", action="store_true",
                        help="Export game log to file (automatically enabled in debug mode)")
    
    args = parser.parse_args()
    
    try:
        if args.games == 1:
            # Run single game
            results = run_single_game(args.mode)
            
            if args.export_log:
                from datetime import datetime
                log_filename = f"bs_game_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                # Note: This would require access to the orchestrator instance
                print(f"Game log would be exported to: {log_filename}")
                
        else:
            # Run multiple games
            stats = run_multiple_games(args.games, args.mode)
            
            if args.export_log:
                import json
                from datetime import datetime
                stats_filename = f"bs_game_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(stats_filename, 'w') as f:
                    json.dump(stats, f, indent=2, default=str)
                print(f"Statistics exported to: {stats_filename}")
    
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running game: {e}")
        if args.mode == "debug":
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 