#!/usr/bin/env python3
"""
Test script specifically for GPT-5-mini reasoning model.
Tests if the enhanced prompt successfully extracts orders from reasoning field.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from diplomacy_game_engine.core.map import Power
from diplomacy_game_engine.gamemaster.gamemaster import Gamemaster

load_dotenv()

def test_gpt5_mini():
    """Test GPT-5-mini with all powers to verify reasoning model fix."""

    # Create temporary game folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    game_id = f"test_gpt5_mini_{timestamp}"
    game_folder = os.path.join("games", game_id)

    print("Testing GPT-5-mini reasoning model...")
    print(f"Game ID: {game_id}")
    print(f"Game folder: {game_folder}")
    print()

    # Configure all powers to use GPT-5-mini
    player_models = {
        Power.ENGLAND: "openai/gpt-5-mini",
        Power.FRANCE: "openai/gpt-5-mini",
        Power.GERMANY: "openai/gpt-5-mini",
        Power.ITALY: "openai/gpt-5-mini",
        Power.AUSTRIA: "openai/gpt-5-mini",
        Power.RUSSIA: "openai/gpt-5-mini",
        Power.TURKEY: "openai/gpt-5-mini",
    }

    # Get OpenRouter API key
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment")
        return False

    try:
        # Initialize Gamemaster
        gamemaster = Gamemaster(
            game_id=game_id,
            game_folder=game_folder,
            player_models=player_models,
            model_platform="openrouter",
            aws_region=None,
            aws_profile=None,
            openrouter_api_key=openrouter_api_key,
            max_years=1,
            enable_visualization=False,
            gunboat_mode=True,  # No press to simplify test
            summarizer_model=None,  # No summaries for test
            press_rounds_spring_1901=0,
            press_rounds_default=0
        )

        print("=" * 60)
        print("RUNNING GPT-5-MINI TEST - SPRING 1901 ONLY")
        print("=" * 60)

        # Run just Spring 1901
        winner = gamemaster.run_spring_phase()

        print()
        print("=" * 60)
        print("GPT-5-MINI TEST RESULTS")
        print("=" * 60)

        # Check if all powers successfully submitted orders
        success_count = 0
        total_powers = len(Power)

        # Read the orders file to verify orders were parsed
        orders_file = os.path.join(game_folder, "orders", "1901_01_spring.yaml")
        if os.path.exists(orders_file):
            with open(orders_file, 'r') as f:
                orders_content = f.read()
                print(f"Orders file created: {orders_file}")
                print("Order parsing results:")

                for power in Power:
                    power_name = power.value.lower().replace("-", "_")
                    if power_name in orders_content:
                        success_count += 1
                        print(f"  ✓ {power.value}: Orders found")
                    else:
                        print(f"  ✗ {power.value}: No orders found")
        else:
            print("ERROR: No orders file created")
            return False

        print()
        print(f"Success rate: {success_count}/{total_powers} ({100*success_count/total_powers:.1f}%)")

        # Check error log for any reasoning model specific issues
        error_log = os.path.join(game_folder, "error.log")
        if os.path.exists(error_log) and os.path.getsize(error_log) > 0:
            print()
            print("ERRORS DETECTED:")
            with open(error_log, 'r') as f:
                print(f.read())
            return False

        # Check game log for reasoning field usage
        game_log = os.path.join(game_folder, "llm_game.log")
        if os.path.exists(game_log):
            reasoning_field_used = False
            with open(game_log, 'r') as f:
                log_content = f.read()
                if "Using reasoning field as content" in log_content:
                    reasoning_field_used = True
                    print("✓ Reasoning field fallback successfully used")

        if success_count == total_powers:
            print()
            print("🎉 GPT-5-MINI TEST PASSED")
            print("All powers successfully submitted orders using reasoning model")
            return True
        else:
            print()
            print("❌ GPT-5-MINI TEST FAILED")
            print(f"Only {success_count}/{total_powers} powers submitted valid orders")
            return False

    except Exception as e:
        print(f"TEST FAILED WITH EXCEPTION: {e}")

        # Check error logs
        error_log = os.path.join(game_folder, "error.log")
        if os.path.exists(error_log):
            print("\nError log contents:")
            with open(error_log, 'r') as f:
                print(f.read())
        return False

if __name__ == "__main__":
    success = test_gpt5_mini()
    sys.exit(0 if success else 1)