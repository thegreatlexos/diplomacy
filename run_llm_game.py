"""
Script to run a complete LLM-powered Diplomacy game.
"""

import logging
import sys
import os
import json
import random
import argparse
from datetime import datetime
from dotenv import load_dotenv
from diplomacy_game_engine.core.map import Power
from diplomacy_game_engine.gamemaster.gamemaster import Gamemaster

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_game.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def randomize_model_assignments(player_models: Dict[Power, str]) -> Dict[Power, str]:
    """
    Randomly shuffle model assignments across powers.
    
    Args:
        player_models: Original power->model mapping
        
    Returns:
        New mapping with models randomly assigned to powers
    """
    # Get list of models and powers
    models = list(player_models.values())
    powers = list(player_models.keys())
    
    # Shuffle the models
    random.shuffle(models)
    
    # Create new mapping
    randomized = {power: model for power, model in zip(powers, models)}
    
    # Log the assignments
    logger.info("")
    logger.info("="*60)
    logger.info("RANDOMIZED MODEL ASSIGNMENTS")
    logger.info("="*60)
    for power, model in randomized.items():
        logger.info(f"  {power.value:15} -> {model}")
    logger.info("="*60)
    logger.info("")
    
    return randomized


def save_model_assignments(
    game_folder: str,
    game_id: str,
    player_models: Dict[Power, str],
    summarizer_model: str,
    platform: str,
    randomized: bool
):
    """
    Save model assignments to JSON file for tracking.
    
    Args:
        game_folder: Root folder for game files
        game_id: Game identifier
        player_models: Power->model mapping
        summarizer_model: Summarizer model ID
        platform: Platform being used (bedrock/openrouter)
        randomized: Whether assignments were randomized
    """
    assignments = {
        "game_id": game_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "randomized": randomized,
        "assignments": {
            power.value: model_id 
            for power, model_id in player_models.items()
        },
        "summarizer": summarizer_model
    }
    
    # Ensure game folder exists
    os.makedirs(game_folder, exist_ok=True)
    
    # Save to JSON
    assignments_path = os.path.join(game_folder, "model_assignments.json")
    with open(assignments_path, 'w') as f:
        json.dump(assignments, f, indent=2)
    
    logger.info(f"Model assignments saved: {assignments_path}")


def main():
    """Run a complete LLM Diplomacy game."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run LLM-powered Diplomacy game')
    parser.add_argument('--test-spring-fall', action='store_true',
                       help='Run Spring and Fall 1901 then exit (tests state continuity)')
    parser.add_argument('--test-full-year', action='store_true',
                       help='Run full year 1901 (Spring, Fall, Winter) then exit')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate visualizations after each phase')
    parser.add_argument('--gun-boat', action='store_true',
                       help='Enable gunboat mode (no press/communication)')
    parser.add_argument('--game-id', default='llm_game_001',
                       help='Game identifier (default: llm_game_001)')
    args = parser.parse_args()
    
    # Load configuration from environment
    model_platform = os.getenv('MODEL_PLATFORM', 'bedrock').lower()
    aws_region = os.getenv('AWS_REGION', 'eu-west-1')
    aws_profile = os.getenv('AWS_PROFILE', 'sf-datadev-dataeng')
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    max_years = int(os.getenv('MAX_YEARS', '20'))
    press_rounds_spring_1901 = int(os.getenv('PRESS_ROUNDS_SPRING_1901', '3'))
    press_rounds_default = int(os.getenv('PRESS_ROUNDS_DEFAULT', '2'))
    summarizer_model = os.getenv('MODEL_SUMMARIZER')  # Optional
    
    # Game configuration
    game_id = args.game_id if args.game_id != 'llm_game_001' else os.getenv('DEFAULT_GAME_ID', 'llm_game_001')
    game_folder = os.path.join("games", game_id)
    
    # Load model assignments from environment
    player_models = {
        Power.ENGLAND: os.getenv('MODEL_ENGLAND', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.FRANCE: os.getenv('MODEL_FRANCE', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.GERMANY: os.getenv('MODEL_GERMANY', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.ITALY: os.getenv('MODEL_ITALY', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.AUSTRIA: os.getenv('MODEL_AUSTRIA', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.RUSSIA: os.getenv('MODEL_RUSSIA', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
        Power.TURKEY: os.getenv('MODEL_TURKEY', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
    }
    
    # Randomize assignments if enabled
    randomize = os.getenv('RANDOMIZE_ASSIGNMENTS', 'false').lower() == 'true'
    if randomize:
        player_models = randomize_model_assignments(player_models)
    
    # Save model assignments for tracking
    save_model_assignments(
        game_folder=game_folder,
        game_id=game_id,
        player_models=player_models,
        summarizer_model=summarizer_model,
        platform=model_platform,
        randomized=randomize
    )
    
    logger.info("="*60)
    logger.info("LLM DIPLOMACY GAME")
    logger.info("="*60)
    logger.info(f"Game ID: {game_id}")
    logger.info(f"Folder: {game_folder}")
    logger.info(f"Region: {aws_region} | Profile: {aws_profile}")
    if args.test_spring_fall:
        logger.info("Mode: TEST SPRING + FALL 1901 (State Continuity Test)")
    if args.test_full_year:
        logger.info("Mode: TEST FULL YEAR 1901 (Spring, Fall, Winter)")
    if args.gun_boat:
        logger.info("Mode: GUNBOAT (No press/communication)")
    if args.visualize:
        logger.info("Visualizations: ENABLED")
    if summarizer_model:
        logger.info("Season Summaries: ENABLED")
    logger.info("")
    logger.info("Players: All using Claude Haiku")
    logger.info("="*60)
    logger.info("")
    
    try:
        # Initialize Gamemaster
        gamemaster = Gamemaster(
            game_id=game_id,
            game_folder=game_folder,
            player_models=player_models,
            model_platform=model_platform,
            aws_region=aws_region,
            aws_profile=aws_profile,
            openrouter_api_key=openrouter_api_key,
            max_years=max_years,
            enable_visualization=args.visualize,
            gunboat_mode=args.gun_boat,
            summarizer_model=summarizer_model,
            press_rounds_spring_1901=press_rounds_spring_1901,
            press_rounds_default=press_rounds_default
        )
        
        # Run the game
        if args.test_full_year:
            logger.info("Running full year 1901 test...")
            
            # Run Spring
            logger.info("\n" + "="*60)
            logger.info("SPRING 1901")
            logger.info("="*60)
            winner = gamemaster.run_spring_phase()
            
            if not winner:
                # Run Fall
                logger.info("\n" + "="*60)
                logger.info("FALL 1901")
                logger.info("="*60)
                winner = gamemaster.run_fall_phase()
            
            if not winner:
                # Run Winter
                logger.info("\n" + "="*60)
                logger.info("WINTER 1901")
                logger.info("="*60)
                winner = gamemaster.run_winter_phase()
            
            logger.info("\n" + "="*60)
            logger.info("FULL YEAR 1901 TEST COMPLETE")
            logger.info("="*60)
        elif args.test_spring_fall:
            logger.info("Running Spring + Fall 1901 test...")
            
            # Run Spring
            logger.info("\n" + "="*60)
            logger.info("SPRING 1901")
            logger.info("="*60)
            winner = gamemaster.run_spring_phase()
            
            if not winner:
                # Run Fall
                logger.info("\n" + "="*60)
                logger.info("FALL 1901")
                logger.info("="*60)
                winner = gamemaster.run_fall_phase()
            
            logger.info("\n" + "="*60)
            logger.info("SPRING + FALL 1901 TEST COMPLETE")
            logger.info("="*60)
        else:
            winner = gamemaster.run_game()
        
        # Report results
        if not args.test_spring_fall and not args.test_full_year:
            logger.info("")
            logger.info("="*60)
            logger.info("GAME COMPLETE")
            logger.info("="*60)
        
        if winner:
            logger.info(f"Winner: {winner.value}")
            logger.info(f"Final SC count: {gamemaster.state.get_sc_count(winner)}")
        else:
            logger.info("Result: Draw")
        
        logger.info(f"Final year: {gamemaster.state.year}")
        logger.info("")
        logger.info("Final Supply Center Counts:")
        for power in Power:
            sc_count = gamemaster.state.get_sc_count(power)
            unit_count = gamemaster.state.get_unit_count(power)
            logger.info(f"  {power.value:15} - {sc_count} SCs, {unit_count} units")
        
        logger.info("")
        logger.info(f"Game files saved to: {game_folder}")
        logger.info(f"  - Orders: {os.path.join(game_folder, 'orders')}")
        logger.info(f"  - States: {os.path.join(game_folder, 'states')}")
        logger.info(f"  - Press: {os.path.join(game_folder, 'press')}")
        if summarizer_model:
            logger.info(f"  - Summaries: {os.path.join(game_folder, 'summaries')}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n\nGame interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n\nGame failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
