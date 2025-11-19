#!/usr/bin/env python3
"""
Test suite for LLM routing module.

Tests the factory pattern, model ID detection, and client implementations.
Uses deepseek/deepseek-chat-v3.1:free for OpenRouter testing (no cost).
"""

import os
from dotenv import load_dotenv
from diplomacy_game_engine.llm_routing import (
    LLMClient,
    BedrockClientWrapper,
    OpenRouterClient,
    LLMClientFactory
)

# Load environment variables from .env file
load_dotenv()


def test_model_id_detection():
    """Test that model IDs are correctly identified as Bedrock or OpenRouter."""
    print("="*80)
    print("TEST: Model ID Detection")
    print("="*80)
    
    # Bedrock models
    bedrock_models = [
        "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "ap-southeast-1.anthropic.claude-3-haiku-20240307-v1:0",
    ]
    
    # OpenRouter models
    openrouter_models = [
        "anthropic/claude-4.5-sonnet",
        "google/gemini-2.5-flash",
        "openai/gpt-5",
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-4-scout",
    ]
    
    print("\n--- Testing Bedrock Model Detection ---")
    for model_id in bedrock_models:
        is_bedrock = LLMClientFactory.is_bedrock_model(model_id)
        provider = LLMClientFactory.get_provider_name(model_id)
        status = "✓" if is_bedrock else "✗"
        print(f"{status} {model_id}: {provider}")
        if not is_bedrock:
            print(f"  ERROR: Should be detected as Bedrock!")
            return False
    
    print("\n--- Testing OpenRouter Model Detection ---")
    for model_id in openrouter_models:
        is_bedrock = LLMClientFactory.is_bedrock_model(model_id)
        provider = LLMClientFactory.get_provider_name(model_id)
        status = "✓" if not is_bedrock else "✗"
        print(f"{status} {model_id}: {provider}")
        if is_bedrock:
            print(f"  ERROR: Should be detected as OpenRouter!")
            return False
    
    print("\n✓✓ All model IDs correctly detected!")
    print("="*80)
    return True


def test_factory_creates_correct_client():
    """Test that factory creates the correct client type."""
    print("\n" + "="*80)
    print("TEST: Factory Client Creation")
    print("="*80)
    
    # Test Bedrock client creation
    print("\n--- Creating Bedrock Client ---")
    bedrock_model = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    try:
        client = LLMClientFactory.create_client(
            model_id=bedrock_model,
            aws_region="eu-west-1"
        )
        if isinstance(client, BedrockClientWrapper):
            print(f"✓ Created BedrockClientWrapper for {bedrock_model}")
        else:
            print(f"✗ Wrong client type: {type(client)}")
            return False
    except Exception as e:
        print(f"✗ Failed to create Bedrock client: {e}")
        return False
    
    # Test OpenRouter client creation (should fail without API key)
    print("\n--- Creating OpenRouter Client (without API key) ---")
    openrouter_model = "deepseek/deepseek-chat-v3.1:free"
    try:
        client = LLMClientFactory.create_client(
            model_id=openrouter_model
        )
        print(f"✗ Should have raised ValueError for missing API key!")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
    
    # Test OpenRouter client creation (with API key)
    print("\n--- Creating OpenRouter Client (with API key) ---")
    try:
        client = LLMClientFactory.create_client(
            model_id=openrouter_model,
            openrouter_api_key="test_key"
        )
        if isinstance(client, OpenRouterClient):
            print(f"✓ Created OpenRouterClient for {openrouter_model}")
        else:
            print(f"✗ Wrong client type: {type(client)}")
            return False
    except Exception as e:
        print(f"✗ Failed to create OpenRouter client: {e}")
        return False
    
    print("\n✓✓ Factory creates correct client types!")
    print("="*80)
    return True


def test_openrouter_with_free_model():
    """
    Test OpenRouter client with free Llama model.
    
    This test requires OPENROUTER_API_KEY to be set in environment.
    Uses meta-llama/llama-3.2-3b-instruct:free which has no cost.
    """
    print("\n" + "="*80)
    print("TEST: OpenRouter API Call (Free Model)")
    print("="*80)
    
    # Check for API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key or api_key == 'your_openrouter_api_key_here':
        print("\n⚠ SKIPPED: OPENROUTER_API_KEY not set")
        print("  Set your OpenRouter API key in .env to run this test")
        print("  Get a key from: https://openrouter.ai/settings/keys")
        print("="*80)
        return True  # Not a failure, just skipped
    
    print(f"\n✓ API key found: {api_key[:10]}...")
    
    # Create client
    model_id = "meta-llama/llama-3.2-3b-instruct:free"
    print(f"✓ Using free model: {model_id}")
    
    try:
        client = LLMClientFactory.create_client(
            model_id=model_id,
            openrouter_api_key=api_key
        )
        print(f"✓ Client created successfully")
        
        # Make a simple API call
        print("\n--- Making API Call ---")
        response = client.generate(
            prompt="Say 'Hello from OpenRouter!' and nothing else.",
            temperature=0.0,
            max_tokens=50
        )
        
        print(f"✓ API call successful!")
        print(f"\nResponse:")
        print(f"  Content: {response['content']}")
        print(f"  Input tokens: {response['usage']['input_tokens']}")
        print(f"  Output tokens: {response['usage']['output_tokens']}")
        print(f"  Total tokens: {response['usage']['total_tokens']}")
        
        # Verify response format
        if 'content' not in response or 'usage' not in response:
            print(f"\n✗ Response missing required keys!")
            return False
        
        if not all(k in response['usage'] for k in ['input_tokens', 'output_tokens', 'total_tokens']):
            print(f"\n✗ Usage dict missing required keys!")
            return False
        
        print("\n✓✓ OpenRouter integration working correctly!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("="*80)
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LLM ROUTING TEST SUITE")
    print("="*80)
    
    results = []
    
    # Run tests
    results.append(("Model ID Detection", test_model_id_detection()))
    results.append(("Factory Client Creation", test_factory_creates_correct_client()))
    results.append(("OpenRouter API Call", test_openrouter_with_free_model()))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓✓ ALL TESTS PASSED! ✓✓")
        print("\nThe LLM routing module is ready for integration!")
    else:
        print(f"\n✗✗ {total - passed} TEST(S) FAILED ✗✗")
    
    print("="*80)
