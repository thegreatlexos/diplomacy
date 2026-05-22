#!/usr/bin/env python3
"""
Plot average SC trajectories comparing gunboat vs press games.

Two subplots side-by-side:
1. Gunboat games - average by provider
2. Press games - average by provider

Usage:
    python scripts/plot_sc_by_mode.py --all
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

# Colors for providers
PROVIDER_COLORS = {
    "anthropic": "#FF6B35",
    "openai": "#10A881",
    "google": "#4285F4",
    "xai": "#000000",
    "mistral": "#FF7F00",
    "meta": "#0668E1",
    "qwen": "#E91E63",
}


def classify_model(model_id: str) -> dict:
    """Classify model by provider."""
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

    return {"provider": provider}


def detect_game_type(game_id: str) -> str:
    """Detect if game is gunboat or press."""
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
        "game_type": detect_game_type(game_id),
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


def plot_gunboat_vs_press(games_data: list, output_path: Path):
    """Plot gunboat vs press side-by-side, averaged by provider."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    for mode, ax in [("gunboat", ax1), ("press", ax2)]:
        # Filter games by mode
        mode_games = [g for g in games_data if g["game_type"] == mode and g["platform"] == "openrouter"]

        if not mode_games:
            ax.text(0.5, 0.5, f"No {mode} games", ha='center', va='center', fontsize=14)
            ax.set_title(f"{mode.capitalize()} Games", fontsize=15, fontweight='bold')
            continue

        # Collect trajectories by provider
        provider_trajectories = defaultdict(lambda: defaultdict(list))

        for game in mode_games:
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

        # Sort providers by total data points (descending)
        # Exclude deepseek (insufficient data)
        sorted_providers = sorted(
            [(p, data) for p, data in provider_trajectories.items() if p != "deepseek"],
            key=lambda x: sum(len(v) for v in x[1].values()),
            reverse=True
        )

        # Plot average trajectories
        from matplotlib.lines import Line2D
        legend_elements = []

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

        ax.legend(handles=legend_elements, loc="upper left", fontsize=11, framealpha=0.9)

        ax.set_xlabel("Year", fontsize=13, fontweight='bold')
        ax.set_ylabel("Average Supply Centers", fontsize=13, fontweight='bold')
        ax.set_title(f"{mode.capitalize()} Games (n={len(mode_games)})",
                     fontsize=15, fontweight='bold')

        # Set y-axis limit based on actual data max
        if sorted_providers:
            all_uppers = []
            for provider, year_data in sorted_providers:
                years = sorted(year_data.keys())
                means = [np.mean(year_data[year]) for year in years]
                stderrs = [np.std(year_data[year]) / np.sqrt(len(year_data[year])) for year in years]
                uppers = [m + se for m, se in zip(means, stderrs)]
                all_uppers.extend(uppers)
            max_val = max(all_uppers) if all_uppers else 12
            ax.set_ylim(0, min(max_val * 1.1, 18))
        else:
            ax.set_ylim(0, 12)

        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=11)

    fig.suptitle("Provider Performance: Gunboat vs Press", fontsize=17, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot SC trajectories by game mode")
    parser.add_argument("--all", "-a", action="store_true", help="Include all games")
    parser.add_argument("--pattern", "-p", help="Game ID pattern")
    parser.add_argument("--output", "-o", help="Output filename")

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

    gunboat_count = sum(1 for g in games_data if g["game_type"] == "gunboat")
    press_count = sum(1 for g in games_data if g["game_type"] == "press")

    print(f"Loaded {len(games_data)} games: {gunboat_count} Gunboat, {press_count} Press")

    output_path = args.output or "sc_trajectories_gunboat_vs_press.png"
    if not output_path.endswith('.png'):
        output_path += '.png'

    # Generate plot
    plot_gunboat_vs_press(games_data, OUTPUT_DIR / output_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
