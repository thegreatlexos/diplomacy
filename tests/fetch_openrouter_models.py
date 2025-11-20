#!/usr/bin/env python3
"""
Fetch and display all available OpenRouter models.

This script queries the OpenRouter API to get a list of all available models,
their pricing, and other metadata. Useful for discovering new models to use.
"""

import os
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()


def fetch_models(api_key: str) -> List[Dict[str, Any]]:
    """Fetch all models from OpenRouter API."""
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print("Fetching models from OpenRouter API...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    return data.get("data", [])


def format_price(price: float) -> str:
    """Format price in dollars per million tokens."""
    if price == 0:
        return "FREE"
    return f"${price:.2f}"


def categorize_models(models: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize models by provider."""
    categories = {}
    
    for model in models:
        model_id = model.get("id", "")
        provider = model_id.split("/")[0] if "/" in model_id else "other"
        
        if provider not in categories:
            categories[provider] = []
        categories[provider].append(model)
    
    return categories


def display_models(models: List[Dict[str, Any]], filter_free: bool = False, filter_provider: str = None):
    """Display models in a formatted table."""
    
    # Filter models
    filtered = models
    if filter_free:
        filtered = [m for m in filtered if m.get("pricing", {}).get("prompt", 0) == 0]
    if filter_provider:
        filtered = [m for m in filtered if m.get("id", "").startswith(filter_provider + "/")]
    
    print(f"\n{'='*120}")
    print(f"Found {len(filtered)} models")
    print(f"{'='*120}")
    print(f"{'Model ID':<50} {'Input Price':<15} {'Output Price':<15} {'Context':<10}")
    print(f"{'-'*120}")
    
    for model in sorted(filtered, key=lambda x: x.get("id", "")):
        model_id = model.get("id", "N/A")
        pricing = model.get("pricing", {})
        
        # Prices are in dollars per token, convert to per million
        input_price = float(pricing.get("prompt", 0)) * 1_000_000
        output_price = float(pricing.get("completion", 0)) * 1_000_000
        context = model.get("context_length", 0)
        
        print(f"{model_id:<50} {format_price(input_price):<15} {format_price(output_price):<15} {context:<10,}")


def save_models_json(models: List[Dict[str, Any]], filename: str = "openrouter_models.json"):
    """Save models to JSON file."""
    filepath = os.path.join("tests", filename)
    with open(filepath, 'w') as f:
        json.dump(models, f, indent=2)
    print(f"\n✓ Saved {len(models)} models to {filepath}")


def display_by_category(models: List[Dict[str, Any]]):
    """Display models grouped by provider."""
    categories = categorize_models(models)
    
    print(f"\n{'='*120}")
    print("MODELS BY PROVIDER")
    print(f"{'='*120}")
    
    for provider in sorted(categories.keys()):
        provider_models = categories[provider]
        free_count = sum(1 for m in provider_models if m.get("pricing", {}).get("prompt", 0) == 0)
        paid_count = len(provider_models) - free_count
        
        print(f"\n{provider.upper()}: {len(provider_models)} models ({free_count} free, {paid_count} paid)")
        print(f"{'-'*120}")
        
        for model in sorted(provider_models, key=lambda x: x.get("id", ""))[:10]:  # Show first 10
            model_id = model.get("id", "")
            pricing = model.get("pricing", {})
            input_price = float(pricing.get("prompt", 0)) * 1_000_000
            output_price = float(pricing.get("completion", 0)) * 1_000_000
            
            price_str = "FREE" if input_price == 0 else f"${input_price:.2f}/${output_price:.2f}"
            print(f"  {model_id:<60} {price_str}")
        
        if len(provider_models) > 10:
            print(f"  ... and {len(provider_models) - 10} more")


def main():
    """Main function."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in .env file")
        return
    
    try:
        # Fetch all models
        models = fetch_models(api_key)
        
        # Display summary
        print(f"\n✓ Fetched {len(models)} models from OpenRouter")
        
        # Display by category
        display_by_category(models)
        
        # Display free models
        print(f"\n{'='*120}")
        print("FREE MODELS")
        display_models(models, filter_free=True)
        
        # Display specific providers
        for provider in ["anthropic", "openai", "google", "meta-llama", "mistralai", "deepseek"]:
            provider_models = [m for m in models if m.get("id", "").startswith(provider + "/")]
            if provider_models:
                print(f"\n{'='*120}")
                print(f"{provider.upper()} MODELS")
                display_models(provider_models)
        
        # Save to JSON
        save_models_json(models)
        
        print(f"\n{'='*120}")
        print("DONE")
        print(f"{'='*120}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching models: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
