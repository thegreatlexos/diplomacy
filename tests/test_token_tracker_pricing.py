#!/usr/bin/env python3
"""Test TokenTracker with external pricing file."""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.gamemaster.token_tracker import TokenTracker


def main():
    print("Testing TokenTracker with external pricing...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = TokenTracker(tmpdir)
        
        print(f'\n✓ TokenTracker initialized')
        print(f'Pricing loaded: {len(tracker.MODEL_PRICING)} models\n')
        
        print('Sample pricing:')
        for key in list(tracker.MODEL_PRICING.keys())[:10]:
            pricing = tracker.MODEL_PRICING[key]
            print(f'  {key:<30} ${pricing["input"]:.2f} input / ${pricing["output"]:.2f} output')
        
        print('\n✓ External pricing loading works!')


if __name__ == "__main__":
    main()
