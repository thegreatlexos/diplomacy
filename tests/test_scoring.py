#!/usr/bin/env python3
"""
Test the scoring system on an existing game.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.scoring import GameScorer


def main():
    """Test scoring on bedrock_mix_press_001 game."""
    game_folder = "games/bedrock_mix_press_001"
    
    if not os.path.exists(game_folder):
        print(f"❌ Game folder not found: {game_folder}")
        return
    
    print("="*80)
    print("TESTING SCORING SYSTEM")
    print("="*80)
    print(f"Game folder: {game_folder}\n")
    
    # Create scorer
    scorer = GameScorer(game_folder)
    
    # Generate report
    print("Generating scoring report...")
    report_path = scorer.save_report()
    
    print(f"\n✓ Report saved: {report_path}")
    print("\n" + "="*80)
    print("REPORT PREVIEW")
    print("="*80)
    
    # Display report
    with open(report_path, 'r') as f:
        print(f.read())


if __name__ == "__main__":
    main()
