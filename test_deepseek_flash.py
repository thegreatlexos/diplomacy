#!/usr/bin/env python3
"""
Test DeepSeek reasoning models with increased max_tokens.
Verifies that bumping token budget fixes the reasoning-only content issue.
"""

import os
import sys
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from diplomacy_game_engine.llm_routing.openrouter_client import OpenRouterClient

load_dotenv()

MODELS = ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"]
MAX_TOKENS_OPTIONS = [2000, 4000, 8000]


def test_response_field(model, max_tokens):
    """Test whether response comes in content vs reasoning field."""
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        return False

    from openrouter import OpenRouter
    client = OpenRouter(api_key=openrouter_api_key)

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Respond concisely."},
        {"role": "user", "content": "Say hello in exactly 5 words."}
    ]

    try:
        response = client.chat.send(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens
        )

        has_content = hasattr(response.choices[0].message, 'content') and response.choices[0].message.content
        has_reasoning = hasattr(response.choices[0].message, 'reasoning') and response.choices[0].message.reasoning
        finish_reason = getattr(response.choices[0], 'finish_reason', 'unknown')

        content_text = response.choices[0].message.content if has_content else None
        print(f"    finish_reason={finish_reason} | content={bool(has_content)} | reasoning={bool(has_reasoning)}")
        if has_content:
            print(f"    content: {content_text[:80]}")
        return has_content

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def test_movement_orders(model, max_tokens):
    """Test movement order generation."""
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        return False

    client = OpenRouterClient(model, openrouter_api_key)

    prompt = """You are playing Diplomacy as Turkey in Spring 1901.

Your current units:
- Fleet Ankara
- Army Constantinople
- Army Smyrna

Submit your orders using this exact format:

```orders
F Ank - BLA
A Con - Bul
A Smy - Con
```"""

    try:
        response = client.generate(prompt, max_tokens=max_tokens)
        content = response.get('content', '')
        usage = response.get('usage', {})

        has_orders = bool(content and ('F ' in content or 'A ' in content))
        print(f"    tokens={usage.get('output_tokens', '?')} | has_orders={has_orders} | len={len(content)}")
        if has_orders:
            print(f"    content: {content[:100]}")
        return has_orders

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def test_press_messages(model, max_tokens):
    """Test press/diplomacy message generation."""
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        return False

    client = OpenRouterClient(model, openrouter_api_key)

    prompt = """You are playing Diplomacy as Turkey in Spring 1901.

Your current units:
- Fleet Ankara
- Army Constantinople
- Army Smyrna

You have received the following messages:
- From Russia: "I'd like to propose a Black Sea DMZ for Spring - neither of us moves a fleet there. What do you say?"
- From Austria-Hungary: "I suggest we avoid conflict in the early game. I am focusing on Serbia. What are your thoughts?"

Write diplomatic messages to other powers. Format each message as:
TO [POWER]: [message]

You may send messages to: England, France, Germany, Italy, Austria-Hungary, Russia"""

    try:
        response = client.generate(prompt, max_tokens=max_tokens)
        content = response.get('content', '')
        usage = response.get('usage', {})

        has_press = bool(content and len(content) > 50)
        print(f"    tokens={usage.get('output_tokens', '?')} | has_press={has_press} | len={len(content)}")
        if has_press:
            print(f"    content: {content[:200]}")
        return has_press

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


if __name__ == "__main__":
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment")
        sys.exit(1)

    print("DeepSeek Reasoning Model Token Budget Test")
    print("=" * 60)
    print()

    all_results = []

    for model in MODELS:
        print(f"MODEL: {model}")
        print("-" * 60)

        for max_tokens in MAX_TOKENS_OPTIONS:
            print(f"\n  max_tokens={max_tokens}:")

            print(f"  [1] Response field test:")
            r1 = test_response_field(model, max_tokens)

            print(f"  [2] Movement orders:")
            r2 = test_movement_orders(model, max_tokens)

            print(f"  [3] Press messages:")
            r3 = test_press_messages(model, max_tokens)

            all_results.append((model, max_tokens, r1, r2, r3))

        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Model':<30} {'Tokens':<8} {'Field':<6} {'Orders':<7} {'Press':<6}")
    print("-" * 60)
    for model, max_tokens, r1, r2, r3 in all_results:
        model_short = model.split('/')[-1]
        print(f"{model_short:<30} {max_tokens:<8} {'OK' if r1 else 'FAIL':<6} {'OK' if r2 else 'FAIL':<7} {'OK' if r3 else 'FAIL':<6}")

    any_failed = any(not (r1 and r2 and r3) for _, _, r1, r2, r3 in all_results)
    print()
    print("Finding minimum viable max_tokens per model:")
    for model in MODELS:
        model_short = model.split('/')[-1]
        model_results = [(mt, r1, r2, r3) for m, mt, r1, r2, r3 in all_results if m == model]
        for mt, r1, r2, r3 in model_results:
            if r1 and r2 and r3:
                print(f"  {model_short}: {mt} tokens (all pass)")
                break
        else:
            print(f"  {model_short}: NO token budget worked (all fail)")

    sys.exit(1 if any_failed else 0)
