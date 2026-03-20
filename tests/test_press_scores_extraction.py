#!/usr/bin/env python3
"""
Test press scores extraction to debug the KeyError issue.
"""

import sys
import os
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.scoring import GameScorer


def test_press_scores_extraction():
    """Test that press scores can be extracted from a summary."""
    
    # Create a temporary game folder
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create necessary subdirectories
        summaries_dir = os.path.join(temp_dir, "summaries")
        os.makedirs(summaries_dir)
        
        # Create a mock summary with PRESS_SCORES
        summary_content = """# Spring 1901 Summary

Some narrative text here...

PRESS_SCORES:
- England: Truthfulness=8, Cooperation=7, Deception=3
- France: Truthfulness=6, Cooperation=8, Deception=5
- Germany: Truthfulness=9, Cooperation=6, Deception=2
- Italy: Truthfulness=7, Cooperation=5, Deception=4
- Austria-Hungary: Truthfulness=8, Cooperation=7, Deception=3
- Russia: Truthfulness=6, Cooperation=6, Deception=4
- Turkey: Truthfulness=7, Cooperation=8, Deception=2
"""
        
        summary_path = os.path.join(summaries_dir, "1901_spring_summary.md")
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        # Create a mock model_assignments.json
        assignments = {
            "game_id": "test_game",
            "platform": "bedrock",
            "randomized": False,
            "assignments": {
                "England": "test-model",
                "France": "test-model",
                "Germany": "test-model",
                "Italy": "test-model",
                "Austria-Hungary": "test-model",
                "Russia": "test-model",
                "Turkey": "test-model"
            }
        }
        
        with open(os.path.join(temp_dir, "model_assignments.json"), 'w') as f:
            json.dump(assignments, f)
        
        # Create scorer and try to extract press scores
        print("Creating GameScorer...")
        scorer = GameScorer(temp_dir)
        
        print("Extracting press scores...")
        try:
            press_scores = scorer.extract_press_scores()
            
            print("\n✓ Press scores extracted successfully!")
            print("\nExtracted scores:")
            for power, scores in press_scores.items():
                if scores:
                    print(f"  {power}: {scores}")
            
            return True
            
        except KeyError as e:
            print(f"\n✗ KeyError occurred: {e}")
            print(f"\npress_scores state: {scorer.press_scores}")
            return False


if __name__ == "__main__":
    success = test_press_scores_extraction()
    sys.exit(0 if success else 1)
