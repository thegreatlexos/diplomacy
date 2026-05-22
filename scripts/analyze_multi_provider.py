#!/usr/bin/env python3
"""
Multi-provider/multi-tier LLM Diplomacy analysis.

Analyzes:
1. Within-provider tier hierarchy (Anthropic: Haiku vs Sonnet vs Opus)
2. Cross-provider battles (mid-tier showdown, premium-tier showdown)
3. Press effectiveness by tier
4. Temporal dynamics by tier
5. Reasoning vs non-reasoning model reliability

Saves both data (CSV/JSON) and visualizations (PNG).
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import csv

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

GAMES_DIR = Path(__file__).parent.parent / "games"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Model classification
MODEL_PROVIDERS = {
    "anthropic": ["claude-opus", "claude-sonnet", "claude-haiku"],
    "openai": ["gpt-5", "gpt-4"],
    "google": ["gemini"],
    "xai": ["grok"],
    "deepseek": ["deepseek"],
    "mistral": ["mistral"],
    "meta": ["llama"],
    "qwen": ["qwen"],
}

MODEL_TIERS = {
    "budget": ["haiku-4-5", "llama-3.1-8b"],
    "mid": ["sonnet-4-6", "gpt-4.1-mini", "grok-4.1-fast", "gemini-3.1-flash", "mistral-small", "qwen3.5-flash"],
    "premium": ["opus-4", "gpt-5", "grok-4.3", "gemini-3.1-pro", "deepseek-v4-pro", "mistral-large", "llama-4-maverick"],
}

REASONING_MODELS = ["opus-4", "gpt-5", "deepseek-v4"]

POWERS = ["England", "France", "Germany", "Italy", "Austria-Hungary", "Russia", "Turkey"]


def classify_model(model_id: str) -> dict:
    """Classify model by provider, tier, and reasoning capability."""
    model_lower = model_id.lower()

    # Determine provider
    provider = "unknown"
    for prov, keywords in MODEL_PROVIDERS.items():
        if any(kw in model_lower for kw in keywords):
            provider = prov
            break

    # Determine tier
    tier = "unknown"
    for t, keywords in MODEL_TIERS.items():
        if any(kw in model_lower for kw in keywords):
            tier = t
            break

    # Determine if reasoning
    is_reasoning = any(kw in model_lower for kw in REASONING_MODELS)

    # Short name for display
    if "haiku" in model_lower:
        short_name = "Haiku"
    elif "sonnet-4-6" in model_lower:
        short_name = "Sonnet-4.6"
    elif "opus-4-6" in model_lower:
        short_name = "Opus-4.6"
    elif "opus-4-7" in model_lower or "opus-4.7" in model_lower:
        short_name = "Opus-4.7"
    elif "gpt-5.5" in model_lower:
        short_name = "GPT-5.5"
    elif "gpt-4.1-mini" in model_lower:
        short_name = "GPT-4.1-mini"
    elif "grok-4.3" in model_lower:
        short_name = "Grok-4.3"
    elif "grok-4.1-fast" in model_lower:
        short_name = "Grok-4.1-fast"
    elif "gemini-3.1-pro" in model_lower:
        short_name = "Gemini-3.1-pro"
    elif "gemini-3.1-flash" in model_lower:
        short_name = "Gemini-Flash"
    elif "deepseek-v4-pro" in model_lower:
        short_name = "DeepSeek-v4-pro"
    elif "mistral-large" in model_lower:
        short_name = "Mistral-Large"
    elif "mistral-small" in model_lower:
        short_name = "Mistral-Small"
    elif "llama-4-maverick" in model_lower:
        short_name = "Llama-4-Maverick"
    elif "llama-3.1-8b" in model_lower:
        short_name = "Llama-8B"
    elif "qwen" in model_lower:
        short_name = "Qwen-Flash"
    else:
        short_name = model_id.split('/')[-1] if '/' in model_id else model_id

    return {
        "provider": provider,
        "tier": tier,
        "is_reasoning": is_reasoning,
        "short_name": short_name,
        "full_id": model_id,
    }


def detect_game_type(game_id: str) -> str:
    """Detect if game is gunboat or press from name."""
    game_lower = game_id.lower()
    if "press" in game_lower:
        return "press"
    elif "gunboat" in game_lower:
        return "gunboat"
    return "unknown"


def detect_platform(game_id: str) -> str:
    """Detect platform from game name."""
    game_lower = game_id.lower()
    if "bedrock" in game_lower:
        return "bedrock"
    elif "openrouter" in game_lower:
        return "openrouter"
    return "unknown"


def load_game_data(game_id: str) -> dict:
    """Load model assignments and yearly SC counts for a game."""
    game_dir = GAMES_DIR / game_id

    if not game_dir.exists():
        return None

    assignments_file = game_dir / "model_assignments.json"
    if not assignments_file.exists():
        return None

    with open(assignments_file) as f:
        assignments_data = json.load(f)

    # Load yearly metrics
    yearly_metrics_file = game_dir / "yearly_metrics.json"
    if yearly_metrics_file.exists():
        with open(yearly_metrics_file) as f:
            yearly_data = json.load(f)
        sc_counts = {int(k): v for k, v in yearly_data.get("sc_counts", {}).items()}
    else:
        sc_counts = compute_sc_counts_from_states(game_dir)

    return {
        "game_id": game_id,
        "game_type": detect_game_type(game_id),
        "platform": detect_platform(game_id),
        "assignments": assignments_data.get("assignments", {}),
        "sc_counts": sc_counts,
    }


def compute_sc_counts_from_states(game_dir: Path) -> dict:
    """Compute yearly SC counts from state files."""
    states_dir = game_dir / "states"
    if not states_dir.exists():
        return {}

    sc_counts = {}
    for state_file in sorted(states_dir.glob("*.json")):
        with open(state_file) as f:
            state = json.load(f)

        year = state.get("year", 0)
        season = state.get("season", "").lower()

        if season not in ["winter", "fall"]:
            continue
        if year in sc_counts and season == "fall":
            continue

        sc_counts[year] = {}
        for power in POWERS:
            sc_counts[year][power] = sum(
                1 for sc_power in state.get("supply_centers", {}).values()
                if sc_power == power
            )

    return sc_counts


def compute_within_game_ranks(game: dict) -> dict:
    """Compute final rank for each power within a game."""
    sc_counts = game["sc_counts"]
    assignments = game["assignments"]

    if not sc_counts:
        return {}

    final_year = max(sc_counts.keys())
    final_counts = sc_counts[final_year]

    # Sort powers by SC count descending
    power_scs = [(p, final_counts.get(p, 0)) for p in assignments.keys()]
    power_scs.sort(key=lambda x: x[1], reverse=True)

    # Assign ranks (handle ties with average rank)
    ranks = {}
    i = 0
    while i < len(power_scs):
        same_sc = [power_scs[i]]
        j = i + 1
        while j < len(power_scs) and power_scs[j][1] == power_scs[i][1]:
            same_sc.append(power_scs[j])
            j += 1

        avg_rank = (i + 1 + j) / 2
        for power, _ in same_sc:
            ranks[power] = avg_rank

        i = j

    return ranks


def compute_survival_years(game: dict) -> dict:
    """Compute how many years each power survived."""
    sc_counts = game["sc_counts"]
    assignments = game["assignments"]

    if not sc_counts:
        return {}

    game_years = sorted(sc_counts.keys())
    start_year = game_years[0]

    survival = {}
    for power in assignments.keys():
        survival[power] = 0
        for year in game_years:
            if sc_counts.get(year, {}).get(power, 0) > 0:
                survival[power] = year - start_year + 1

    return survival


# =============================================================================
# ANALYSIS 1: WITHIN-PROVIDER TIER HIERARCHY
# =============================================================================

def analyze_anthropic_tiers(games_data: list) -> dict:
    """Analyze Haiku vs Sonnet vs Opus performance in Bedrock games."""
    bedrock_games = [g for g in games_data if g["platform"] == "bedrock"]

    tier_data = defaultdict(lambda: {"ranks": [], "wins": 0, "top3": 0, "total": 0, "survival": []})

    for game in bedrock_games:
        ranks = compute_within_game_ranks(game)
        survival = compute_survival_years(game)
        assignments = game["assignments"]

        for power, rank in ranks.items():
            model_info = classify_model(assignments.get(power, ""))
            tier = model_info["tier"]

            tier_data[tier]["ranks"].append(rank)
            tier_data[tier]["total"] += 1
            tier_data[tier]["survival"].append(survival.get(power, 0))

            if rank == 1:
                tier_data[tier]["wins"] += 1
            if rank <= 3:
                tier_data[tier]["top3"] += 1

    # Calculate statistics
    results = {}
    for tier in ["budget", "mid", "premium"]:
        if tier not in tier_data:
            continue

        data = tier_data[tier]
        results[tier] = {
            "avg_rank": np.mean(data["ranks"]),
            "std_rank": np.std(data["ranks"], ddof=1),
            "win_rate": data["wins"] / data["total"] * 100 if data["total"] > 0 else 0,
            "top3_rate": data["top3"] / data["total"] * 100 if data["total"] > 0 else 0,
            "avg_survival": np.mean(data["survival"]),
            "n": data["total"],
        }

    return results


# =============================================================================
# ANALYSIS 2: CROSS-PROVIDER BATTLES
# =============================================================================

def analyze_provider_battle(games_data: list, tier: str) -> dict:
    """Analyze provider performance within a specific tier."""
    tier_games = [g for g in games_data
                  if any(classify_model(m)["tier"] == tier for m in g["assignments"].values())]

    provider_data = defaultdict(lambda: {
        "ranks": [], "wins": 0, "top3": 0, "total": 0,
        "survival": [], "models": set()
    })

    for game in tier_games:
        ranks = compute_within_game_ranks(game)
        survival = compute_survival_years(game)
        assignments = game["assignments"]

        for power, rank in ranks.items():
            model_info = classify_model(assignments.get(power, ""))

            if model_info["tier"] != tier:
                continue

            provider = model_info["provider"]
            provider_data[provider]["ranks"].append(rank)
            provider_data[provider]["total"] += 1
            provider_data[provider]["survival"].append(survival.get(power, 0))
            provider_data[provider]["models"].add(model_info["short_name"])

            if rank == 1:
                provider_data[provider]["wins"] += 1
            if rank <= 3:
                provider_data[provider]["top3"] += 1

    # Calculate statistics
    results = {}
    for provider, data in provider_data.items():
        if data["total"] == 0:
            continue

        results[provider] = {
            "avg_rank": np.mean(data["ranks"]),
            "std_rank": np.std(data["ranks"], ddof=1) if len(data["ranks"]) > 1 else 0,
            "win_rate": data["wins"] / data["total"] * 100,
            "top3_rate": data["top3"] / data["total"] * 100,
            "avg_survival": np.mean(data["survival"]),
            "n": data["total"],
            "models": sorted(data["models"]),
        }

    return results


# =============================================================================
# ANALYSIS 3: PRESS EFFECTIVENESS BY TIER
# =============================================================================

def analyze_press_effectiveness(games_data: list) -> dict:
    """Analyze press impact by tier."""
    results = {}

    for tier in ["budget", "mid", "premium"]:
        gunboat_ranks = []
        press_ranks = []

        for game in games_data:
            if game["game_type"] == "unknown":
                continue

            ranks = compute_within_game_ranks(game)
            assignments = game["assignments"]

            for power, rank in ranks.items():
                model_info = classify_model(assignments.get(power, ""))
                if model_info["tier"] != tier:
                    continue

                if game["game_type"] == "gunboat":
                    gunboat_ranks.append(rank)
                elif game["game_type"] == "press":
                    press_ranks.append(rank)

        if not gunboat_ranks or not press_ranks:
            continue

        results[tier] = {
            "gunboat_avg_rank": np.mean(gunboat_ranks),
            "press_avg_rank": np.mean(press_ranks),
            "delta": np.mean(gunboat_ranks) - np.mean(press_ranks),  # positive = press helps
            "gunboat_n": len(gunboat_ranks),
            "press_n": len(press_ranks),
        }

    return results


# =============================================================================
# ANALYSIS 4: TEMPORAL DYNAMICS BY TIER
# =============================================================================

def analyze_temporal_dynamics(games_data: list) -> dict:
    """Analyze early vs late game performance by tier."""
    results = {}

    for tier in ["budget", "mid", "premium"]:
        early_scs = []  # Years 1-5
        late_scs = []   # Years 11+

        for game in games_data:
            sc_counts = game["sc_counts"]
            assignments = game["assignments"]

            if not sc_counts:
                continue

            game_years = sorted(sc_counts.keys())
            start_year = game_years[0]

            for power, model_id in assignments.items():
                model_info = classify_model(model_id)
                if model_info["tier"] != tier:
                    continue

                # Early game (first 5 years)
                for year in game_years[:5]:
                    if power in sc_counts[year]:
                        early_scs.append(sc_counts[year][power])

                # Late game (year 11+)
                late_years = [y for y in game_years if y >= start_year + 10]
                for year in late_years:
                    if power in sc_counts[year]:
                        late_scs.append(sc_counts[year][power])

        if early_scs:
            results[tier] = {
                "early_avg_sc": np.mean(early_scs),
                "late_avg_sc": np.mean(late_scs) if late_scs else 0,
                "early_n": len(early_scs),
                "late_n": len(late_scs),
            }

    return results


# =============================================================================
# ANALYSIS 5: REASONING VS NON-REASONING
# =============================================================================

def analyze_reasoning_models(games_data: list) -> dict:
    """Compare reasoning vs non-reasoning models."""
    sys.path.insert(0, str(GAMES_DIR.parent))
    from diplomacy_game_engine.scoring.order_analyzer import OrderAnalyzer

    reasoning_data = {"ranks": [], "invalid": [], "complexity": []}
    nonreasoning_data = {"ranks": [], "invalid": [], "complexity": []}

    for game in games_data:
        ranks = compute_within_game_ranks(game)
        assignments = game["assignments"]

        # Load order metrics
        game_path = GAMES_DIR / game["game_id"]
        try:
            analyzer = OrderAnalyzer(str(game_path))
            analyzer.analyze_all_orders(max_year=None)

            for power, rank in ranks.items():
                model_info = classify_model(assignments.get(power, ""))

                if power in analyzer.precision_counts:
                    invalid_rate = analyzer.compute_error_rate().get(power, 0)
                    complexity = analyzer.compute_order_complexity().get(power, 0)

                    if model_info["is_reasoning"]:
                        reasoning_data["ranks"].append(rank)
                        reasoning_data["invalid"].append(invalid_rate)
                        reasoning_data["complexity"].append(complexity)
                    else:
                        nonreasoning_data["ranks"].append(rank)
                        nonreasoning_data["invalid"].append(invalid_rate)
                        nonreasoning_data["complexity"].append(complexity)
        except Exception as e:
            print(f"Warning: Could not analyze orders for {game['game_id']}: {e}")

    results = {}
    if reasoning_data["ranks"]:
        results["reasoning"] = {
            "avg_rank": np.mean(reasoning_data["ranks"]),
            "avg_invalid_rate": np.mean(reasoning_data["invalid"]) * 100,
            "avg_complexity": np.mean(reasoning_data["complexity"]) * 100,
            "n": len(reasoning_data["ranks"]),
        }

    if nonreasoning_data["ranks"]:
        results["non_reasoning"] = {
            "avg_rank": np.mean(nonreasoning_data["ranks"]),
            "avg_invalid_rate": np.mean(nonreasoning_data["invalid"]) * 100,
            "avg_complexity": np.mean(nonreasoning_data["complexity"]) * 100,
            "n": len(nonreasoning_data["ranks"]),
        }

    return results


# =============================================================================
# SAVE DATA
# =============================================================================

def save_analysis_data(all_results: dict, timestamp: str):
    """Save all analysis results to CSV and JSON."""
    output_prefix = DATA_DIR / f"analysis_{timestamp}"

    # Save as JSON
    json_path = output_prefix.with_suffix(".json")
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved JSON: {json_path}")

    # Save anthropic tiers to CSV
    if "anthropic_tiers" in all_results:
        csv_path = DATA_DIR / f"anthropic_tiers_{timestamp}.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["tier", "avg_rank", "win_rate", "top3_rate", "avg_survival", "n"])
            for tier, data in all_results["anthropic_tiers"].items():
                writer.writerow([
                    tier, data["avg_rank"], data["win_rate"],
                    data["top3_rate"], data["avg_survival"], data["n"]
                ])
        print(f"Saved CSV: {csv_path}")

    # Save provider battles to CSV
    for tier in ["mid", "premium"]:
        key = f"provider_battle_{tier}"
        if key in all_results:
            csv_path = DATA_DIR / f"provider_battle_{tier}_{timestamp}.csv"
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["provider", "avg_rank", "win_rate", "top3_rate", "avg_survival", "n", "models"])
                for provider, data in all_results[key].items():
                    writer.writerow([
                        provider, data["avg_rank"], data["win_rate"],
                        data["top3_rate"], data["avg_survival"], data["n"],
                        "; ".join(data["models"])
                    ])
            print(f"Saved CSV: {csv_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Multi-provider/multi-tier analysis")
    parser.add_argument("--all", "-a", action="store_true", help="Analyze all games")
    parser.add_argument("--pattern", "-p", help="Game ID pattern")
    parser.add_argument("--output", "-o", help="Output prefix")

    args = parser.parse_args()

    # Find games
    if args.all:
        game_ids = sorted([d.name for d in GAMES_DIR.iterdir()
                          if d.is_dir() and not d.name.startswith(".") and d.name != "archive"])
    elif args.pattern:
        import glob as glob_module
        game_ids = sorted([d.name for d in GAMES_DIR.iterdir()
                          if d.is_dir() and glob_module.fnmatch.fnmatch(d.name, args.pattern)])
    else:
        print("Use --all or --pattern to select games")
        sys.exit(1)

    print(f"Loading {len(game_ids)} games...")

    games_data = []
    for gid in game_ids:
        data = load_game_data(gid)
        if data and data["sc_counts"]:
            games_data.append(data)

    if not games_data:
        print("No valid game data found.")
        sys.exit(1)

    # Count game types
    bedrock_count = sum(1 for g in games_data if g["platform"] == "bedrock")
    openrouter_count = sum(1 for g in games_data if g["platform"] == "openrouter")
    gunboat_count = sum(1 for g in games_data if g["game_type"] == "gunboat")
    press_count = sum(1 for g in games_data if g["game_type"] == "press")

    print(f"Loaded {len(games_data)} games:")
    print(f"  Bedrock: {bedrock_count} | OpenRouter: {openrouter_count}")
    print(f"  Gunboat: {gunboat_count} | Press: {press_count}")
    print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Run analyses
    all_results = {}

    print("Analyzing Anthropic tier hierarchy...")
    all_results["anthropic_tiers"] = analyze_anthropic_tiers(games_data)

    print("Analyzing mid-tier provider battle...")
    all_results["provider_battle_mid"] = analyze_provider_battle(games_data, "mid")

    print("Analyzing premium-tier provider battle...")
    all_results["provider_battle_premium"] = analyze_provider_battle(games_data, "premium")

    print("Analyzing press effectiveness by tier...")
    all_results["press_effectiveness"] = analyze_press_effectiveness(games_data)

    print("Analyzing temporal dynamics...")
    all_results["temporal_dynamics"] = analyze_temporal_dynamics(games_data)

    print("Analyzing reasoning vs non-reasoning...")
    all_results["reasoning_comparison"] = analyze_reasoning_models(games_data)

    # Save results
    print("\nSaving results...")
    save_analysis_data(all_results, timestamp)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if "anthropic_tiers" in all_results:
        print("\nANTHROPIC TIER HIERARCHY:")
        for tier in ["budget", "mid", "premium"]:
            if tier in all_results["anthropic_tiers"]:
                data = all_results["anthropic_tiers"][tier]
                print(f"  {tier:10} | Rank: {data['avg_rank']:.2f} | Win: {data['win_rate']:.1f}% | n={data['n']}")

    if "provider_battle_mid" in all_results:
        print("\nMID-TIER PROVIDER BATTLE:")
        sorted_providers = sorted(all_results["provider_battle_mid"].items(),
                                 key=lambda x: x[1]["avg_rank"])
        for provider, data in sorted_providers:
            print(f"  {provider:12} | Rank: {data['avg_rank']:.2f} | Win: {data['win_rate']:.1f}% | n={data['n']}")

    if "press_effectiveness" in all_results:
        print("\nPRESS EFFECTIVENESS (delta = positive means press helps):")
        for tier, data in all_results["press_effectiveness"].items():
            print(f"  {tier:10} | Gunboat: {data['gunboat_avg_rank']:.2f} | Press: {data['press_avg_rank']:.2f} | Delta: {data['delta']:+.2f}")

    if "reasoning_comparison" in all_results:
        print("\nREASONING VS NON-REASONING:")
        if "reasoning" in all_results["reasoning_comparison"]:
            data = all_results["reasoning_comparison"]["reasoning"]
            print(f"  Reasoning    | Rank: {data['avg_rank']:.2f} | Invalid: {data['avg_invalid_rate']:.1f}% | n={data['n']}")
        if "non_reasoning" in all_results["reasoning_comparison"]:
            data = all_results["reasoning_comparison"]["non_reasoning"]
            print(f"  Non-Reasoning| Rank: {data['avg_rank']:.2f} | Invalid: {data['avg_invalid_rate']:.1f}% | n={data['n']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
