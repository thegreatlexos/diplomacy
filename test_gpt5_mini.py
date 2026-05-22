#!/usr/bin/env python3
"""
Simple test for GPT-5-mini reasoning model.
Makes one API call and tries to extract orders.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from diplomacy_game_engine.llm_routing.openrouter_client import OpenRouterClient

load_dotenv()

def test_gpt5_mini_single_call():
    """Make single API call to GPT-5-mini and try to extract orders."""

    # Get OpenRouter API key
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment")
        return False

    print("Testing single GPT-5-mini API call...")
    print("Model: openai/gpt-5-mini")
    print()

    # Initialize client
    client = OpenRouterClient("openai/gpt-5-mini", openrouter_api_key)

    # Create simple test prompt that includes the reasoning model enhancement
    prompt = """You are playing Diplomacy as France in Spring 1901.

Your current units:
- Fleet Brest
- Army Paris
- Army Marseilles

Supply centers you control: Brest, Paris, Marseilles

Submit your orders using this exact format:

```orders
F Bre - ENG
A Par - Pic
A Mar - Spa
```

**FOR REASONING MODELS:** After your strategic analysis, you MUST provide concrete orders. Your response must end with executable orders in the exact format above. Analysis without orders = failure.

```orders
F Bre - MAO
A Par - Bur
A Mar - Spa
```"""

    print("PROMPT SENT:")
    print("=" * 50)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("=" * 50)
    print()

    try:
        # Make API call
        print("Making API call to GPT-5-mini...")
        response = client.generate(prompt)

        print("API RESPONSE:")
        print("=" * 50)
        print(f"Response type: {type(response)}")
        print(f"Response content: {response}")
        print("=" * 50)
        print()

        # Try to extract orders
        content = response.get('content', '') if response else ''
        if content and content.strip():
            print("ORDER EXTRACTION TEST:")
            print("=" * 30)

            # Look for orders pattern
            if "```orders" in content:
                print("✓ Found orders block in response")

                # Extract orders between ```orders and ```
                start = content.find("```orders") + len("```orders")
                end = content.find("```", start)
                if end != -1:
                    orders_text = content[start:end].strip()
                    print(f"Extracted orders: {orders_text}")

                    if orders_text:
                        print("✅ SUCCESS: Orders extracted successfully")
                        return True
                    else:
                        print("❌ FAIL: Orders block found but empty")
                        return False
                else:
                    print("❌ FAIL: Orders block not properly closed")
                    return False
            else:
                print("❌ FAIL: No orders block found in response")
                print("Response doesn't contain '```orders' pattern")
                return False
        else:
            print("❌ FAIL: Empty or None response")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gpt5_mini_single_call()
    print()
    print("FINAL RESULT:", "✅ PASS" if success else "❌ FAIL")
    sys.exit(0 if success else 1)