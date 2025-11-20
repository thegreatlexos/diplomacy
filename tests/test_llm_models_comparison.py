#!/usr/bin/env python3
"""
Test script to compare different LLM models.

Makes the same request to multiple models and prints detailed request/response info.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diplomacy_game_engine.llm_routing import LLMClientFactory

# Load environment variables
load_dotenv()


def test_model(model_id: str, prompt: str, system_prompt: str = None):
    """Test a single model with the given prompt."""
    print("\n" + "="*80)
    print(f"MODEL: {model_id}")
    print("="*80)
    
    try:
        # Determine provider and create client
        provider = LLMClientFactory.get_provider_name(model_id)
        print(f"Provider: {provider}")
        
        if provider == "bedrock":
            client = LLMClientFactory.create_client(
                model_id=model_id,
                aws_region=os.getenv('AWS_REGION', 'eu-west-1')
            )
        else:  # openrouter
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                print("⚠ SKIPPED: OPENROUTER_API_KEY not set")
                return
            client = LLMClientFactory.create_client(
                model_id=model_id,
                openrouter_api_key=api_key
            )
        
        print(f"✓ Client created")
        
        # Print request details
        print("\n--- REQUEST ---")
        if system_prompt:
            print(f"System Prompt: {system_prompt}")
        print(f"User Prompt: {prompt}")
        print(f"Temperature: 0.7")
        print(f"Max Tokens: 500")
        
        # Make the request
        print("\n--- CALLING API ---")
        response = client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        # Print response details
        print("\n--- RESPONSE ---")
        print(f"Content:\n{response['content']}")
        print(f"\n--- USAGE ---")
        print(f"Input tokens:  {response['usage']['input_tokens']}")
        print(f"Output tokens: {response['usage']['output_tokens']}")
        print(f"Total tokens:  {response['usage']['total_tokens']}")
        
        print("\n✓ Test completed successfully")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")


def main():
    """Run comparison tests across multiple models."""
    print("\n" + "="*80)
    print("LLM MODELS COMPARISON TEST")
    print("="*80)
    
    # Define the test prompt
    system_prompt = "You are a helpful assistant that provides concise, accurate answers."
    user_prompt = "Explain what the game of Diplomacy is in 2-3 sentences."
    
    print("\nTest Configuration:")
    print(f"System Prompt: {system_prompt}")
    print(f"User Prompt: {user_prompt}")
    
    # Models to test - All confirmed working free OpenRouter models
    models = [
        "tngtech/deepseek-r1t2-chimera:free",
        "openai/gpt-oss-20b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ]
    
    # Test each model
    for model_id in models:
        test_model(model_id, user_prompt, system_prompt)
    
    print("\n" + "="*80)
    print("COMPARISON TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
