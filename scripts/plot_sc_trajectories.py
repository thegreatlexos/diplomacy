#!/usr/bin/env python3
"""
Plot supply center trajectories over time.

Two plots:
1. Bedrock games - colored by model tier (Haiku, Sonnet, Opus)
2. OpenRouter games - colored by provider

Usage:
    python scripts/plot_sc_trajectories.py --all
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

GAMES_DIR = Path(__file__).parent.parent / "games"
OUTPUT_DIR = GAMES_DIR

POWERS = ["England", "France", "Germany", "Italy", "Austria-Hungary", "Russia", "Turkey"]

# Colors for Bedrock (by tier)
TIER_COLORS = {
    "budget": "#e74c3c",    # red (Haiku)
    "mid": "#f39c12",       # orange (Sonnet)
    "premium": "#2ecc71",   # green (Opus)
}

# Colors for OpenRouter (by provider)
PROVIDER_COLORS = {
    "anthropic": "#FF6B35",
    "openai": "#10A881",
    "google": "#4285F4",
    "xai": "#000000",
    "mistral": "#FF7F00",
    "deepseek": "#8B4789",
    "meta": "#0668E1",
    "qwen": "#E91E63",
}


def classify_model(model_id: str) -> dict:
    """Classify model by provider and tier."""
    model_lower = model_id.lower()

    # Determine provider
    if "anthropic" in model_lower or "claude" in model_lower:
        provider = "anthropic"
    elif "openai" in model_lower or "gpt" in model_lower:
        provider = "openai"
    elif "google" in model_lower or "gemini" in model_lower:
        provider = "google"
    elif "xai" in model_lower or "grok" in model_lower:
        provider = "xai"
    elif "deepseek" in model_lower:
        provider = "deepseek"
    elif "mistral" in model_lower:
        provider = "mistral"
    elif "meta" in model_lower or "llama" in model_lower:
        provider = "meta"
    elif "qwen" in model_lower:
        provider = "qwen"
    else:
        provider = "unknown"

    # Determine tier
    if "haiku" in model_lower or "llama-3.1-8b" in model_lower:
        tier = "budget"
    elif "sonnet-4-6" in model_lower or "gpt-4.1-mini" in model_lower or "grok-4.1-fast" in model_lower or \
         "gemini-3.1-flash" in model_lower or "mistral-small" in model_lower or "qwen3.5-flash" in model_lower:
        tier = "mid"
    elif "opus" in model_lower or "gpt-5" in model_lower or "grok-4.3" in model_lower or \
         "gemini-3.1-pro" in model_lower or "deepseek-v4-pro" in model_lower or \
         "mistral-large" in model_lower or "llama-4-maverick" in model_lower:
        tier = "premium"
    else:
        tier = "unknown"

    return {"provider": provider, "tier": tier}


def detect_platform(game_id: str) -> str:
    """Detect platform from game name."""
    game_lower = game_id.lower()
    if "bedrock" in game_lower:
        return "bedrock"
    elif "openrouter" in game_lower:
        return "openrouter"
    return "unknown"


def load_game_data(game_id: str) -> dict:
    """Load model assignments and yearly SC counts."""
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


def plot_bedrock_trajectories(games_data: list, output_path: Path):
    """Plot average SC trajectories for Bedrock games, by tier."""
    bedrock_games = [g for g in games_data if g["platform"] == "bedrock"]

    if not bedrock_games:
        print("No Bedrock games found")
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    # Collect trajectories by tier
    tier_trajectories = defaultdict(lambda: defaultdict(list))

    for game in bedrock_games:
        sc_counts = game["sc_counts"]
        assignments = game["assignments"]

        if not sc_counts:
            continue

        years = sorted(sc_counts.keys())

        for power, model_id in assignments.items():
            model_info = classify_model(model_id)
            tier = model_info["tier"]

            # Collect SC counts by year for this tier
            for year in years:
                sc = sc_counts[year].get(power, 0)
                tier_trajectories[tier][year].append(sc)

    # Plot average trajectories
    from matplotlib.lines import Line2D
    legend_elements = []

    for tier in ["premium", "mid", "budget"]:
        if tier not in tier_trajectories:
            continue

        year_data = tier_trajectories[tier]
        years = sorted(year_data.keys())

        # Calculate mean and stderr for each year
        means = [np.mean(year_data[year]) for year in years]
        stderrs = [np.std(year_data[year]) / np.sqrt(len(year_data[year])) for year in years]

        color = TIER_COLORS[tier]

        # Plot mean line
        ax.plot(years, means, color=color, linewidth=3, marker='o',
                markersize=4, label=f"{tier.capitalize()}")

        # Add confidence band (mean ± stderr)
        upper = [m + se for m, se in zip(means, stderrs)]
        lower = [max(0, m - se) for m, se in zip(means, stderrs)]
        ax.fill_between(years, lower, upper, color=color, alpha=0.2)

        # Count instances
        n_total = sum(len(year_data[year]) for year in years)

        tier_labels = {
            "premium": "Opus (Premium)",
            "mid": "Sonnet (Mid)",
            "budget": "Haiku (Budget)"
        }
        legend_elements.append(
            Line2D([0], [0], color=color, linewidth=3,
                   label=f"{tier_labels[tier]} (n={n_total})")
        )

    ax.legend(handles=legend_elements, loc="upper left", fontsize=12, framealpha=0.9)

    ax.set_xlabel("Year", fontsize=13, fontweight='bold')
    ax.set_ylabel("Average Supply Centers", fontsize=13, fontweight='bold')
    ax.set_title(f"Average SC Trajectories by Model Tier: Bedrock (n={len(bedrock_games)} games)",
                 fontsize=15, fontweight='bold')

    # Set y-axis limit based on actual data max
    all_uppers = []
    for tier in ["premium", "mid", "budget"]:
        if tier in tier_trajectories:
            year_data = tier_trajectories[tier]
            years = sorted(year_data.keys())
            means = [np.mean(year_data[year]) for year in years]
            stderrs = [np.std(year_data[year]) / np.sqrt(len(year_data[year])) for year in years]
            uppers = [m + se for m, se in zip(means, stderrs)]
            all_uppers.extend(uppers)
    max_val = max(all_uppers) if all_uppers else 12
    ax.set_ylim(0, min(max_val * 1.1, 18))

    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_openrouter_trajectories(games_data: list, output_path: Path):
    """Plot average SC trajectories for OpenRouter games, by provider."""
    openrouter_games = [g for g in games_data if g["platform"] == "openrouter"]

    if not openrouter_games:
        print("No OpenRouter games found")
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    # Collect trajectories by provider
    provider_trajectories = defaultdict(lambda: defaultdict(list))

    for game in openrouter_games:
        sc_counts = game["sc_counts"]
        assignments = game["assignments"]

        if not sc_counts:
            continue

        years = sorted(sc_counts.keys())

        for power, model_id in assignments.items():
            model_info = classify_model(model_id)
            provider = model_info["provider"]

            # Collect SC counts by year for this provider
            for year in years:
                sc = sc_counts[year].get(power, 0)
                provider_trajectories[provider][year].append(sc)

    # Plot average trajectories
    from matplotlib.lines import Line2D
    legend_elements = []

    # Sort providers by total data points (descending)
    # Exclude deepseek (insufficient data - only 3 games with stalemate bias)
    sorted_providers = sorted(
        [(p, data) for p, data in provider_trajectories.items() if p != "deepseek"],
        key=lambda x: sum(len(v) for v in x[1].values()),
        reverse=True
    )

    for provider, year_data in sorted_providers:
        years = sorted(year_data.keys())

        # Calculate mean and stderr for each year
        means = [np.mean(year_data[year]) for year in years]
        stderrs = [np.std(year_data[year]) / np.sqrt(len(year_data[year])) for year in years]

        color = PROVIDER_COLORS.get(provider, "#95a5a6")

        # Plot mean line
        ax.plot(years, means, color=color, linewidth=3, marker='o',
                markersize=4, label=provider.capitalize())

        # Add confidence band (mean ± stderr)
        upper = [m + se for m, se in zip(means, stderrs)]
        lower = [max(0, m - se) for m, se in zip(means, stderrs)]
        ax.fill_between(years, lower, upper, color=color, alpha=0.2)

        # Count instances
        n_total = sum(len(year_data[year]) for year in years)

        legend_elements.append(
            Line2D([0], [0], color=color, linewidth=3,
                   label=f"{provider.capitalize()} (n={n_total})")
        )

    ax.legend(handles=legend_elements, loc="upper left", fontsize=11, framealpha=0.9, ncol=2)

    ax.set_xlabel("Year", fontsize=13, fontweight='bold')
    ax.set_ylabel("Average Supply Centers", fontsize=13, fontweight='bold')
    ax.set_title(f"Average SC Trajectories by Provider: OpenRouter (n={len(openrouter_games)} games)",
                 fontsize=15, fontweight='bold')

    # Set y-axis limit based on actual data max
    all_uppers = []
    for provider, year_data in sorted_providers:
        years = sorted(year_data.keys())
        means = [np.mean(year_data[year]) for year in years]
        stderrs = [np.std(year_data[year]) / np.sqrt(len(year_data[year])) for year in years]
        uppers = [m + se for m, se in zip(means, stderrs)]
        all_uppers.extend(uppers)
    max_val = max(all_uppers) if all_uppers else 12
    ax.set_ylim(0, min(max_val * 1.1, 18))

    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot SC trajectories over time")
    parser.add_argument("--all", "-a", action="store_true", help="Include all games")
    parser.add_argument("--pattern", "-p", help="Game ID pattern")
    parser.add_argument("--output-prefix", "-o", help="Output prefix")

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
        return

    print(f"Loading {len(game_ids)} games...")

    games_data = []
    for gid in game_ids:
        data = load_game_data(gid)
        if data and data["sc_counts"]:
            games_data.append(data)

    if not games_data:
        print("No valid game data found.")
        return

    bedrock_count = sum(1 for g in games_data if g["platform"] == "bedrock")
    openrouter_count = sum(1 for g in games_data if g["platform"] == "openrouter")

    print(f"Loaded {len(games_data)} games: {bedrock_count} Bedrock, {openrouter_count} OpenRouter")

    prefix = args.output_prefix or "sc_trajectories"

    # Generate plots
    plot_bedrock_trajectories(games_data, OUTPUT_DIR / f"{prefix}_bedrock.png")
    plot_openrouter_trajectories(games_data, OUTPUT_DIR / f"{prefix}_openrouter.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
