#!/usr/bin/env python3
"""
Recalculate game costs using corrected OpenRouter pricing.
"""
import csv
import json
import sys

def load_pricing():
    """Load pricing data"""
    with open('diplomacy_game_engine/config/model_pricing.json') as f:
        pricing_data = json.load(f)

    # Flatten pricing structure
    pricing = {}
    for provider, models in pricing_data.items():
        if isinstance(models, dict):
            for model_id, rates in models.items():
                if isinstance(rates, dict) and 'input' in rates:
                    pricing[model_id] = rates
    return pricing

def recalculate_game_costs(game_folder):
    """Recalculate costs for a specific game"""
    csv_file = f"games/{game_folder}/token_usage.csv"
    pricing = load_pricing()

    print(f"Recalculating costs for {game_folder}")
    print(f"Loading: {csv_file}")
    print()

    total_old_cost = 0
    total_new_cost = 0
    model_costs = {}

    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                model_id = row['model_id']
                input_tokens = int(row['input_tokens'])
                output_tokens = int(row['output_tokens'])
                old_cost = float(row['estimated_cost_usd'])

                # Calculate new cost
                if model_id in pricing:
                    rates = pricing[model_id]
                    input_rate = rates['input'] / 1000  # Convert from per-1K to per-token
                    output_rate = rates['output'] / 1000
                    new_cost = (input_tokens * input_rate) + (output_tokens * output_rate)
                else:
                    print(f"Warning: No pricing for {model_id}, using old cost")
                    new_cost = old_cost

                total_old_cost += old_cost
                total_new_cost += new_cost

                if model_id not in model_costs:
                    model_costs[model_id] = {'old': 0, 'new': 0, 'input': 0, 'output': 0}
                model_costs[model_id]['old'] += old_cost
                model_costs[model_id]['new'] += new_cost
                model_costs[model_id]['input'] += input_tokens
                model_costs[model_id]['output'] += output_tokens

    except FileNotFoundError:
        print(f"Error: Could not find {csv_file}")
        return

    # Print results
    print("=" * 80)
    print("COST RECALCULATION RESULTS")
    print("=" * 80)
    print(f"Old estimate: ${total_old_cost:.4f}")
    print(f"New estimate: ${total_new_cost:.4f}")
    print(f"Difference:   ${total_new_cost - total_old_cost:.4f} ({100*(total_new_cost/total_old_cost - 1):.1f}%)")
    print()

    print("BY MODEL:")
    print("-" * 60)
    for model_id, costs in sorted(model_costs.items(), key=lambda x: x[1]['new'], reverse=True):
        old_cost = costs['old']
        new_cost = costs['new']
        change_pct = 100 * (new_cost / old_cost - 1) if old_cost > 0 else 0
        print(f"{model_id:40} ${old_cost:.4f} → ${new_cost:.4f} ({change_pct:+.1f}%)")

    print()
    print("ACTUAL vs NEW ESTIMATE:")
    print("-" * 40)

    # Dashboard actuals from user
    actuals = {
        'openai/gpt-5-mini': 0.332,
        'anthropic/claude-haiku-4.5': 0.245,
        'x-ai/grok-4.1-fast': 0.147,
        'qwen/qwen3.5-flash-02-23': 0.129,
        'google/gemini-3.1-flash-lite-preview': 0.0411,
        'mistralai/mistral-small-2603': 0.0233,
        'meta-llama/llama-3.1-8b-instruct': 0.00376
    }

    total_actual = sum(actuals.values())

    for model_id in model_costs:
        if model_id in actuals:
            actual = actuals[model_id]
            estimate = model_costs[model_id]['new']
            accuracy = 100 * (1 - abs(estimate - actual) / actual) if actual > 0 else 0
            print(f"{model_id:40} Actual: ${actual:.4f}, Estimate: ${estimate:.4f} ({accuracy:.1f}% accurate)")

    print()
    print(f"TOTAL: Actual ${total_actual:.4f} vs New Estimate ${total_new_cost:.4f}")
    accuracy = 100 * (1 - abs(total_new_cost - total_actual) / total_actual)
    print(f"Overall accuracy: {accuracy:.1f}%")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recalculate_costs.py <game_folder>")
        print("Example: python recalculate_costs.py 20260402_openrouter_gunboat_000")
        sys.exit(1)

    game_folder = sys.argv[1]
    recalculate_game_costs(game_folder)