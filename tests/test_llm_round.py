"""
Test script for LLM integration with AWS Bedrock.
Tests a single LLM call with order parsing.
"""

import logging
import sys
import os
from dotenv import load_dotenv
from diplomacy_game_engine.llm.bedrock_client import BedrockClient

# Load environment variables
load_dotenv()
from diplomacy_game_engine.llm.order_parser import OrderParser
from diplomacy_game_engine.llm.prompts import PromptBuilder
from diplomacy_game_engine.core.game_state import create_starting_state
from diplomacy_game_engine.core.map import Power, create_standard_map

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_model(model_id: str, power: Power):
    """Test a single model with a movement order prompt."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {power.value} - Movement Orders")
    logger.info(f"Model: {model_id}")
    logger.info(f"{'='*60}")
    
    try:
        # Load config from environment
        aws_region = os.getenv('AWS_REGION', 'eu-west-1')
        aws_profile = os.getenv('AWS_PROFILE', 'sf-datadev-dataeng')
        
        # Initialize components
        client = BedrockClient(region=aws_region, profile_name=aws_profile)
        game_map = create_standard_map()
        state = create_starting_state()
        
        # Build prompt
        prompt = PromptBuilder.build_movement_orders_prompt(
            state=state,
            power=power,
            game_map=game_map,
            press_threads={}
        )
        
        logger.info(f"Prompt: {len(prompt)} chars | Invoking model...")
        
        # Call LLM
        response = client.invoke_model(
            model_id=model_id,
            prompt=prompt,
            max_tokens=2048,
            temperature=0.7
        )
        
        logger.info(f"\n--- LLM Response ({len(response)} chars) ---")
        logger.info(response)
        logger.info("-" * 60)
        
        # Parse orders
        logger.info("\nParsing orders...")
        orders = OrderParser.parse_orders(response, power)
        
        logger.info(f"\nParsed {len(orders)} orders:")
        for order in orders:
            logger.info(f"  - {order}")
        
        # Check if we got orders for all units
        expected_units = len(state.get_units_by_power(power))
        if len(orders) == expected_units:
            logger.info(f"\n✓ SUCCESS: Got orders for all {expected_units} units")
        else:
            logger.warning(f"\n⚠ WARNING: Expected {expected_units} orders, got {len(orders)}")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ FAILED: {str(e)}", exc_info=True)
        return False


def test_press_round(model_id: str, power: Power):
    """Test a press round with message parsing."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {power.value} - Press Round")
    logger.info(f"{'='*60}")
    
    try:
        # Load config from environment
        aws_region = os.getenv('AWS_REGION', 'eu-west-1')
        aws_profile = os.getenv('AWS_PROFILE', 'sf-datadev-dataeng')
        
        client = BedrockClient(region=aws_region, profile_name=aws_profile)
        game_map = create_standard_map()
        state = create_starting_state()
        
        # Build press prompt
        prompt = PromptBuilder.build_press_round_prompt(
            state=state,
            power=power,
            game_map=game_map,
            press_threads={},
            round_number=1
        )
        
        logger.info("Invoking model...")
        
        response = client.invoke_model(
            model_id=model_id,
            prompt=prompt,
            max_tokens=1024,
            temperature=0.8
        )
        
        logger.info(f"\n--- LLM Response ({len(response)} chars) ---")
        logger.info(response)
        logger.info("-" * 60)
        
        # Parse messages
        messages = OrderParser.parse_press_messages(response, power)
        
        logger.info(f"\nParsed {len(messages)} messages:")
        for recipient, message in messages.items():
            logger.info(f"  TO {recipient}: {message[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ FAILED: {str(e)}", exc_info=True)
        return False


def main():
    """Run tests for all configured models."""
    
    # Model configurations
    models = {
        # Power.ENGLAND: "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        # Power.FRANCE: "mistral.pixtral-large-2502-v1:0",
        # Power.GERMANY: "openai.gpt-oss-120b-1:0",
        # Power.ITALY: "deepseek-llm-r1-distill-llama-70b",
        # Power.AUSTRIA: "meta.llama3-2-3b-instruct-v1:0",
        # Power.RUSSIA: "amazon.nova-pro-v1:0",
        Power.TURKEY: "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    }
    
    # Load config
    aws_region = os.getenv('AWS_REGION', 'eu-west-1')
    aws_profile = os.getenv('AWS_PROFILE', 'sf-datadev-dataeng')
    
    logger.info("="*60)
    logger.info("LLM INTEGRATION TEST")
    logger.info("="*60)
    logger.info(f"Testing {len(models)} model(s) | Region: {aws_region} | Profile: {aws_profile}\n")
    
    results = {}
    
    # Test each model
    for power, model_id in models.items():
        try:
            # Test movement orders
            success = test_single_model(model_id, power)
            results[model_id] = success
            
            # If movement orders worked, also test press
            if success:
                test_press_round(model_id, power)
            
        except KeyboardInterrupt:
            logger.info("\n\nTest interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error testing {model_id}: {e}")
            results[model_id] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    for power, model_id in models.items():
        if model_id in results:
            status = "✓ PASS" if results[model_id] else "✗ FAIL"
            logger.info(f"{status} - {power.value:15} - {model_id}")
        else:
            logger.info(f"⊘ SKIP - {power.value:15} - {model_id}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info(f"\nPassed: {passed}/{total}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
