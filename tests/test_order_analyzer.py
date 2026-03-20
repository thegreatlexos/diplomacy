#!/usr/bin/env python3
"""
Test order analyzer for precision scoring.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.scoring.order_analyzer import OrderAnalyzer


def main():
    """Test order analyzer on bedrock_mix_press_score_000 game."""
    game_folder = "games/bedrock_mix_press_score_000"
    
    if not os.path.exists(game_folder):
        print(f"❌ Game folder not found: {game_folder}")
        return
    
    print("="*80)
    print("TESTING ORDER ANALYZER")
    print("="*80)
    print(f"Game folder: {game_folder}\n")
    
    # Create analyzer
    analyzer = OrderAnalyzer(game_folder)
    
    # Analyze orders
    print("Analyzing orders...")
    counts = analyzer.analyze_all_orders()
    
    print("\n" + "="*80)
    print("PRECISION COUNTS")
    print("="*80)
    
    # Display results
    print(f"\n{'Power':<20} {'Invalid':<10} {'Convoys':<10} {'Supp Own':<10} {'Supp Other':<12} {'Bounces':<10}")
    print("-" * 80)
    
    for power, metrics in sorted(counts.items()):
        print(f"{power:<20} {metrics['invalid_orders']:<10} {metrics['convoys']:<10} "
              f"{metrics['support_own']:<10} {metrics['support_other']:<12} {metrics['bounces']:<10}")
    
    print("\n" + "="*80)
    print("EXPECTED RESULTS (from summary)")
    print("="*80)
    print("Invalid Orders:")
    print("  - England: 1 (illegal convoy)")
    print("  - Russia: 1 (province code error)")
    print("  - Italy: 1 (province code error)")
    print("  - Turkey: 1 (province code error)")
    print("\nConvoys:")
    print("  - England: 1 (attempted convoy)")


if __name__ == "__main__":
    main()
