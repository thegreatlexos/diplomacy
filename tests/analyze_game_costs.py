#!/usr/bin/env python3
"""
Analyze game costs for different model configurations.

Compares token usage and costs between:
- Gunboat vs Press modes
- Bedrock vs OpenRouter models
- Different model presets
"""

import sys
import os
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_token_usage(game_folder: str) -> dict:
    """Load token usage from a game's CSV file."""
    csv_path = os.path.join(game_folder, "token_usage.csv")
    
    if not os.path.exists(csv_path):
        return None
    
    total_input = 0
    total_output = 0
    by_call_type = {}
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_input += int(row['input_tokens'])
            total_output += int(row['output_tokens'])
            
            call_type = row['call_type']
            if call_type not in by_call_type:
                by_call_type[call_type] = {'input': 0, 'output': 0}
            
            by_call_type[call_type]['input'] += int(row['input_tokens'])
            by_call_type[call_type]['output'] += int(row['output_tokens'])
    
    return {
        'total_input': total_input,
        'total_output': total_output,
        'by_call_type': by_call_type
    }


def load_pricing():
    """Load model pricing from config file."""
    pricing_path = os.path.join(
        os.path.dirname(__file__), '..', 
        'diplomacy_game_engine', 'config', 'model_pricing.json'
    )
    
    with open(pricing_path, 'r') as f:
        pricing_data = json.load(f)
    
    # Flatten for easy lookup
    flat = {}
    for provider, models in pricing_data.items():
        for model_key, model_data in models.items():
            flat[model_key] = model_data
    
    return flat


def calculate_preset_cost(input_tokens: int, output_tokens: int, preset_config: dict, pricing: dict) -> float:
    """Calculate cost for a specific preset configuration."""
    
    # Count how many of each model type
    model_counts = {}
    for power, model_key in preset_config.items():
        if model_key not in model_counts:
            model_counts[model_key] = 0
        model_counts[model_key] += 1
    
    # Calculate average cost per power
    total_cost = 0
    for model_key, count in model_counts.items():
        model_pricing = pricing.get(model_key, pricing.get('default', {'input': 1.0, 'output': 5.0}))
        
        # Tokens per power (divide by 7 powers)
        power_input = input_tokens / 7
        power_output = output_tokens / 7
        
        # Cost for this model type
        cost = (power_input / 1_000_000) * model_pricing['input'] + \
               (power_output / 1_000_000) * model_pricing['output']
        
        total_cost += cost * count
    
    return total_cost


def main():
    """Generate cost analysis report."""
    
    print("="*80)
    print("DIPLOMACY GAME COST ANALYSIS")
    print("="*80)
    
    # Load pricing
    pricing = load_pricing()
    print(f"\n✓ Loaded pricing for {len(pricing)} models")
    
    # Analyze existing games
    games = {
        'Gunboat Mode': 'games/archive/bedrock_mix_gunboat_000',
        'Press Mode Full (20 years)': 'games/archive/bedrock_mix_press_score_003',
        'Press Mode Optimized (20 years)': 'games/20251201_new_bedrock_mix_press_000'
    }
    
    print("\n" + "="*80)
    print("TOKEN USAGE FROM ACTUAL GAMES")
    print("="*80)
    
    for game_name, game_folder in games.items():
        usage = load_token_usage(game_folder)
        if usage:
            total = usage['total_input'] + usage['total_output']
            print(f"\n{game_name}:")
            print(f"  Input tokens:  {usage['total_input']:,}")
            print(f"  Output tokens: {usage['total_output']:,}")
            print(f"  Total tokens:  {total:,}")
            
            # Show breakdown by call type
            if usage['by_call_type']:
                print(f"\n  Token Sources:")
                
                # Group press calls together
                press_tokens = sum(
                    data['input'] + data['output'] 
                    for call_type, data in usage['by_call_type'].items() 
                    if 'press' in call_type.lower()
                )
                
                # Get other major categories
                orders_tokens = sum(
                    data['input'] + data['output']
                    for call_type, data in usage['by_call_type'].items()
                    if 'orders' in call_type.lower()
                )
                
                summary_tokens = sum(
                    data['input'] + data['output']
                    for call_type, data in usage['by_call_type'].items()
                    if 'summary' in call_type.lower()
                )
                
                if press_tokens > 0:
                    print(f"    Press messages:   {press_tokens:>12,} ({press_tokens/total*100:>5.1f}%)")
                if orders_tokens > 0:
                    print(f"    Orders:           {orders_tokens:>12,} ({orders_tokens/total*100:>5.1f}%)")
                if summary_tokens > 0:
                    print(f"    Summaries:        {summary_tokens:>12,} ({summary_tokens/total*100:>5.1f}%)")
    
    # Define presets
    presets = {
        'Bedrock Fast (All Haiku)': {
            'England': 'claude-haiku-4-5',
            'France': 'claude-haiku-4-5',
            'Germany': 'claude-haiku-4-5',
            'Italy': 'claude-haiku-4-5',
            'Austria': 'claude-haiku-4-5',
            'Russia': 'claude-haiku-4-5',
            'Turkey': 'claude-haiku-4-5',
            'Summarizer': 'claude-haiku-4-5'
        },
        'Bedrock Top (All Sonnet)': {
            'England': 'claude-sonnet-4-5',
            'France': 'claude-sonnet-4-5',
            'Germany': 'claude-sonnet-4-5',
            'Italy': 'claude-sonnet-4-5',
            'Austria': 'claude-sonnet-4-5',
            'Russia': 'claude-sonnet-4-5',
            'Turkey': 'claude-sonnet-4-5',
            'Summarizer': 'claude-sonnet-4-5'
        },
        'Bedrock Mix (4 Haiku + 3 Sonnet)': {
            'England': 'claude-haiku-4-5',
            'France': 'claude-haiku-4-5',
            'Germany': 'claude-sonnet-4-5',
            'Italy': 'claude-haiku-4-5',
            'Austria': 'claude-haiku-4-5',
            'Russia': 'claude-sonnet-4-5',
            'Turkey': 'claude-sonnet-4-5',
            'Summarizer': 'claude-sonnet-4-5'
        },
        'OpenRouter Free': {
            'all': 'deepseek-r1t2-chimera'  # All free
        },
        'OpenRouter Top (Premium - 7 Providers)': {
            'England': 'claude-sonnet-4-5',
            'France': 'gpt-5',
            'Germany': 'gemini-2-5-pro',
            'Italy': 'grok-4',
            'Austria': 'mistral-large',
            'Russia': 'deepseek-chat',
            'Turkey': 'llama-3-1-405b',
            'Summarizer': 'claude-sonnet-4-5'
        },
        'OpenRouter Fast (7 Providers)': {
            'England': 'claude-haiku-4-5',
            'France': 'gpt-5-mini',
            'Germany': 'gemini-2-5-flash-lite',
            'Italy': 'grok-4-fast',
            'Austria': 'mistral-small-3-2',
            'Russia': 'deepseek-r1-distill-llama-70b',
            'Turkey': 'llama-3-1-8b',
            'Summarizer': 'gpt-5-mini'
        },
        'OpenRouter Mix (Top + Fast)': {
            'England': 'claude-sonnet-4-5',
            'France': 'gpt-5',
            'Germany': 'gemini-2-5-flash-lite',
            'Italy': 'grok-4-fast',
            'Austria': 'mistral-large',
            'Russia': 'deepseek-r1-distill-llama-70b',
            'Turkey': 'llama-3-1-8b',
            'Summarizer': 'gpt-5-mini'
        }
    }
    
    # Load game data
    gunboat_usage = load_token_usage('games/archive/bedrock_mix_gunboat_000')
    press_full_usage = load_token_usage('games/archive/bedrock_mix_press_score_003')
    press_opt_usage = load_token_usage('games/20251201_new_bedrock_mix_press_000')
    
    if gunboat_usage and press_full_usage and press_opt_usage:
        print("\n" + "="*80)
        print("COST ESTIMATES (20-year game)")
        print("="*80)
        
        print(f"\n{'Preset':<40} {'Full Press':>13} {'Optimized':>13} {'Gunboat':>13}")
        print("-" * 80)
        
        for preset_name, preset_config in presets.items():
            if 'all' in preset_config:
                # Free model
                full_cost = opt_cost = gunboat_cost = 0.0
            else:
                full_cost = calculate_preset_cost(
                    press_full_usage['total_input'],
                    press_full_usage['total_output'],
                    preset_config,
                    pricing
                )
                opt_cost = calculate_preset_cost(
                    press_opt_usage['total_input'],
                    press_opt_usage['total_output'],
                    preset_config,
                    pricing
                )
                gunboat_cost = calculate_preset_cost(
                    gunboat_usage['total_input'],
                    gunboat_usage['total_output'],
                    preset_config,
                    pricing
                )
            
            print(f"{preset_name:<40} ${full_cost:>12.2f} ${opt_cost:>12.2f} ${gunboat_cost:>12.2f}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
