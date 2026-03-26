#!/usr/bin/env python3
"""
Generate scientifically defensible charts for LLM Diplomacy evaluation.

Addresses:
- Non-independence: Uses within-game rankings (game as unit of analysis)
- Survivorship bias: Early-game metrics (first 5 years)
- Press comparison: Detects gunboat vs press from game names

Usage:
    python scripts/plot_sc_comparison.py --all -t scientific
    python scripts/plot_sc_comparison.py --all -t press_comparison
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import glob as glob_module

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

GAMES_DIR = Path(__file__).parent.parent / "games"

# Model detection and styling
def normalize_model(model_id: str) -> str:
    """Normalize model ID to canonical name."""
    model_lower = model_id.lower()
    if "haiku" in model_lower:
        return "Haiku"
    elif "sonnet" in model_lower:
        return "Sonnet"
    elif "opus" in model_lower:
        return "Opus"
    return "Unknown"


def detect_game_type(game_id: str) -> str:
    """Detect if game is gunboat or press from name."""
    game_lower = game_id.lower()
    if "press" in game_lower:
        return "press"
    elif "gunboat" in game_lower:
        return "gunboat"
    return "unknown"


MODEL_COLORS = {
    "Sonnet": "#2ecc71",   # green
    "Haiku": "#e74c3c",    # red
    "Opus": "#3498db",     # blue
    "Unknown": "#7f8c8d",  # gray
}

MODEL_ORDER = ["Haiku", "Sonnet", "Opus"]
POWERS = ["England", "France", "Germany", "Italy", "Austria-Hungary", "Russia", "Turkey"]
EARLY_GAME_YEARS = 5  # First N years for early-game analysis


def load_game_data(game_id: str) -> dict:
    """Load model assignments and yearly SC counts for a game."""
    game_dir = GAMES_DIR / game_id

    if not game_dir.exists():
        print(f"Warning: Game {game_id} not found")
        return None

    assignments_file = game_dir / "model_assignments.json"
    if not assignments_file.exists():
        print(f"Warning: No model assignments for {game_id}")
        return None

    with open(assignments_file) as f:
        assignments_data = json.load(f)

    # Load yearly metrics or compute from states
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
        # Find all powers with same SC count
        same_sc = [power_scs[i]]
        j = i + 1
        while j < len(power_scs) and power_scs[j][1] == power_scs[i][1]:
            same_sc.append(power_scs[j])
            j += 1

        # Average rank for ties
        avg_rank = (i + 1 + j) / 2
        for power, _ in same_sc:
            ranks[power] = avg_rank

        i = j

    return ranks


def load_early_game_orders(game_id: str, max_years: int = EARLY_GAME_YEARS) -> dict:
    """Load order metrics for first N years only."""
    sys.path.insert(0, str(GAMES_DIR.parent))
    from diplomacy_game_engine.scoring.order_analyzer import OrderAnalyzer

    game_path = GAMES_DIR / game_id
    analyzer = OrderAnalyzer(str(game_path))

    # Get starting year
    game_data = load_game_data(game_id)
    if not game_data or not game_data["sc_counts"]:
        return {}

    start_year = min(game_data["sc_counts"].keys())
    cutoff_year = start_year + max_years

    # Analyze orders up to cutoff
    analyzer.analyze_all_orders(max_year=cutoff_year)

    return {
        "counts": analyzer.precision_counts,
        "complexity": analyzer.compute_order_complexity(),
        "error_rate": analyzer.compute_error_rate(),
    }


# =============================================================================
# SCIENTIFIC CHARTS
# =============================================================================

def plot_average_rank(games_data: list, output_path: Path):
    """Bar chart of average final rank by model with error bars.

    Unit of analysis: game (addresses non-independence).
    """
    # Collect ranks per model
    model_ranks = defaultdict(list)

    for game in games_data:
        ranks = compute_within_game_ranks(game)
        assignments = game["assignments"]

        for power, rank in ranks.items():
            model = normalize_model(assignments.get(power, "unknown"))
            model_ranks[model].append(rank)

    # Calculate statistics
    models = [m for m in MODEL_ORDER if m in model_ranks]
    means = [np.mean(model_ranks[m]) for m in models]
    stds = [np.std(model_ranks[m], ddof=1) for m in models]
    ns = [len(model_ranks[m]) for m in models]
    sems = [s / np.sqrt(n) for s, n in zip(stds, ns)]

    # Statistical test (Kruskal-Wallis for ranks)
    if len(models) >= 2:
        rank_groups = [model_ranks[m] for m in models]
        if all(len(g) >= 2 for g in rank_groups):
            h_stat, p_value = stats.kruskal(*rank_groups)
        else:
            h_stat, p_value = np.nan, np.nan
    else:
        h_stat, p_value = np.nan, np.nan

    # Plot
    fig, ax = plt.subplots(figsize=(10, 7))

    x = np.arange(len(models))
    colors = [MODEL_COLORS.get(m, "#7f8c8d") for m in models]

    bars = ax.bar(x, means, yerr=sems, capsize=5, color=colors, width=0.6,
                  edgecolor='black', linewidth=1.2)

    # Add value labels
    for bar, mean, n in zip(bars, means, ns):
        ax.annotate(f'{mean:.2f}\n(n={n})',
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 8), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Average Final Rank (lower = better)", fontsize=12)
    ax.set_title(f"Average Final Rank by Model ({len(games_data)} games)", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=12)
    ax.set_ylim(0, 7.5)
    ax.invert_yaxis()  # Lower rank = better, so invert
    ax.grid(True, alpha=0.3, axis="y")

    # Statistical annotation
    if not np.isnan(p_value):
        sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        ax.text(0.98, 0.02, f"Kruskal-Wallis H={h_stat:.2f}, p={p_value:.4f} {sig}",
                transform=ax.transAxes, fontsize=9, ha='right', va='bottom',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


def plot_win_rate(games_data: list, output_path: Path):
    """Bar chart of win rate and top-3 rate by model."""
    model_outcomes = defaultdict(lambda: {"wins": 0, "top3": 0, "total": 0})

    for game in games_data:
        ranks = compute_within_game_ranks(game)
        assignments = game["assignments"]

        for power, rank in ranks.items():
            model = normalize_model(assignments.get(power, "unknown"))
            model_outcomes[model]["total"] += 1
            if rank == 1:
                model_outcomes[model]["wins"] += 1
            if rank <= 3:
                model_outcomes[model]["top3"] += 1

    models = [m for m in MODEL_ORDER if m in model_outcomes]
    win_rates = [model_outcomes[m]["wins"] / model_outcomes[m]["total"] * 100 for m in models]
    top3_rates = [model_outcomes[m]["top3"] / model_outcomes[m]["total"] * 100 for m in models]
    ns = [model_outcomes[m]["total"] for m in models]

    # Plot
    fig, ax = plt.subplots(figsize=(10, 7))

    x = np.arange(len(models))
    width = 0.35

    bars1 = ax.bar(x - width/2, win_rates, width, label="Win Rate (1st)",
                   color=[MODEL_COLORS.get(m) for m in models], alpha=0.9, edgecolor='black')
    bars2 = ax.bar(x + width/2, top3_rates, width, label="Top 3 Rate",
                   color=[MODEL_COLORS.get(m) for m in models], alpha=0.5, edgecolor='black')

    # Add value labels
    for bar, rate in zip(bars1, win_rates):
        if rate > 0:
            ax.annotate(f'{rate:.0f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    for bar, rate in zip(bars2, top3_rates):
        ax.annotate(f'{rate:.0f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Percentage", fontsize=12)
    ax.set_title(f"Win Rate & Top 3 Rate by Model ({len(games_data)} games)", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(n={n})" for m, n in zip(models, ns)], fontsize=11)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


def plot_early_game_complexity(games_data: list, output_path: Path):
    """Bar chart of order complexity in first 5 years (addresses survivorship bias)."""
    model_complexity = defaultdict(list)
    model_error_rate = defaultdict(list)

    for game in games_data:
        game_id = game["game_id"]
        assignments = game["assignments"]

        try:
            metrics = load_early_game_orders(game_id)
            complexity = metrics.get("complexity", {})
            error_rate = metrics.get("error_rate", {})

            for power, model_id in assignments.items():
                model = normalize_model(model_id)
                if power in complexity:
                    model_complexity[model].append(complexity[power])
                if power in error_rate:
                    model_error_rate[model].append(error_rate[power])
        except Exception as e:
            print(f"Warning: Could not load early-game metrics for {game_id}: {e}")

    models = [m for m in MODEL_ORDER if m in model_complexity]
    avg_complexity = [np.mean(model_complexity[m]) * 100 for m in models]
    avg_error = [np.mean(model_error_rate[m]) * 100 for m in models]
    ns = [len(model_complexity[m]) for m in models]

    # Plot
    fig, ax = plt.subplots(figsize=(10, 7))

    x = np.arange(len(models))
    width = 0.35

    bars1 = ax.bar(x - width/2, avg_complexity, width, label="Complexity %", color="#3498db")
    bars2 = ax.bar(x + width/2, avg_error, width, label="Error Rate %", color="#e74c3c")

    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Percentage", fontsize=12)
    ax.set_title(f"Early-Game Order Metrics (First {EARLY_GAME_YEARS} Years, {len(games_data)} games)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(n={n})" for m, n in zip(models, ns)], fontsize=11)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_ylim(0, max(max(avg_complexity), max(avg_error)) * 1.4 if avg_complexity else 50)

    # Explanation
    ax.text(0.02, 0.98, "Complexity = (supports + convoys) / total\nError Rate = (invalid + self-attacks) / total",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# PRESS COMPARISON CHARTS
# =============================================================================

def plot_press_comparison_rank(games_data: list, output_path: Path):
    """Compare average rank: gunboat vs press, grouped by model."""
    # Separate by game type
    gunboat_games = [g for g in games_data if g["game_type"] == "gunboat"]
    press_games = [g for g in games_data if g["game_type"] == "press"]

    if not gunboat_games or not press_games:
        print("Warning: Need both gunboat and press games for comparison")
        return

    # Collect ranks
    def get_model_ranks(games):
        model_ranks = defaultdict(list)
        for game in games:
            ranks = compute_within_game_ranks(game)
            for power, rank in ranks.items():
                model = normalize_model(game["assignments"].get(power, "unknown"))
                model_ranks[model].append(rank)
        return model_ranks

    gunboat_ranks = get_model_ranks(gunboat_games)
    press_ranks = get_model_ranks(press_games)

    models = [m for m in MODEL_ORDER if m in gunboat_ranks or m in press_ranks]

    # Plot
    fig, ax = plt.subplots(figsize=(12, 7))

    x = np.arange(len(models))
    width = 0.35

    gunboat_means = [np.mean(gunboat_ranks.get(m, [np.nan])) for m in models]
    press_means = [np.mean(press_ranks.get(m, [np.nan])) for m in models]
    gunboat_ns = [len(gunboat_ranks.get(m, [])) for m in models]
    press_ns = [len(press_ranks.get(m, [])) for m in models]

    bars1 = ax.bar(x - width/2, gunboat_means, width, label=f"Gunboat (n={len(gunboat_games)} games)",
                   color="#7f8c8d", edgecolor='black')
    bars2 = ax.bar(x + width/2, press_means, width, label=f"Press (n={len(press_games)} games)",
                   color="#9b59b6", edgecolor='black')

    for bar, mean, n in zip(bars1, gunboat_means, gunboat_ns):
        if not np.isnan(mean) and n > 0:
            ax.annotate(f'{mean:.2f}\n(n={n})', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 5), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    for bar, mean, n in zip(bars2, press_means, press_ns):
        if not np.isnan(mean) and n > 0:
            ax.annotate(f'{mean:.2f}\n(n={n})', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 5), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Average Final Rank (lower = better)", fontsize=12)
    ax.set_title("Gunboat vs Press: Average Final Rank by Model", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=12)
    ax.set_ylim(0, 7.5)
    ax.invert_yaxis()
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


def plot_press_impact_delta(games_data: list, output_path: Path):
    """Show delta in performance: press - gunboat (positive = press helps)."""
    gunboat_games = [g for g in games_data if g["game_type"] == "gunboat"]
    press_games = [g for g in games_data if g["game_type"] == "press"]

    if not gunboat_games or not press_games:
        print("Warning: Need both gunboat and press games for comparison")
        return

    def get_model_ranks(games):
        model_ranks = defaultdict(list)
        for game in games:
            ranks = compute_within_game_ranks(game)
            for power, rank in ranks.items():
                model = normalize_model(game["assignments"].get(power, "unknown"))
                model_ranks[model].append(rank)
        return model_ranks

    gunboat_ranks = get_model_ranks(gunboat_games)
    press_ranks = get_model_ranks(press_games)

    models = [m for m in MODEL_ORDER if m in gunboat_ranks and m in press_ranks]

    # Calculate delta (negative = press improves rank = good)
    deltas = []
    for m in models:
        gunboat_mean = np.mean(gunboat_ranks[m])
        press_mean = np.mean(press_ranks[m])
        deltas.append(gunboat_mean - press_mean)  # Positive = press helps (lower rank is better)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(models))
    colors = ['#2ecc71' if d > 0 else '#e74c3c' for d in deltas]

    bars = ax.bar(x, deltas, color=colors, width=0.6, edgecolor='black')

    for bar, delta in zip(bars, deltas):
        va = 'bottom' if delta >= 0 else 'top'
        offset = 3 if delta >= 0 else -3
        ax.annotate(f'{delta:+.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, offset), textcoords="offset points", ha='center', va=va,
                    fontsize=11, fontweight='bold')

    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Rank Improvement (positive = press helps)", fontsize=12)
    ax.set_title("Press Impact: Change in Average Rank", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")

    # Annotation
    ax.text(0.02, 0.98, "Green = press improves performance\nRed = press hurts performance",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


def plot_press_volume(games_data: list, output_path: Path):
    """Bar chart of communication volume by model (press games only)."""
    from diplomacy_game_engine.scoring.press_analyzer import PressAnalyzer

    press_games = [g for g in games_data if g["game_type"] == "press"]
    if not press_games:
        print("No press games for volume analysis")
        return

    # Aggregate volume by model
    model_volume = defaultdict(lambda: {
        "messages": [], "words": [], "avg_length": []
    })

    for game in press_games:
        game_path = GAMES_DIR / game["game_id"]
        try:
            analyzer = PressAnalyzer(str(game_path))
            vol = analyzer.analyze_volume()

            for power, model_id in game["assignments"].items():
                model = normalize_model(model_id)
                if power in vol:
                    model_volume[model]["messages"].append(vol[power]["messages_sent"])
                    model_volume[model]["words"].append(vol[power]["words_sent"])
                    model_volume[model]["avg_length"].append(vol[power]["avg_words_per_message"])
        except Exception as e:
            print(f"Warning: Could not analyze press for {game['game_id']}: {e}")

    models = [m for m in MODEL_ORDER if m in model_volume]
    if not models:
        print("No volume data collected")
        return

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Messages sent
    ax = axes[0]
    means = [np.mean(model_volume[m]["messages"]) for m in models]
    stds = [np.std(model_volume[m]["messages"]) for m in models]
    colors = [MODEL_COLORS.get(m) for m in models]
    bars = ax.bar(models, means, yerr=stds, capsize=5, color=colors, edgecolor='black')
    for bar, mean in zip(bars, means):
        ax.annotate(f'{mean:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 5), textcoords="offset points", ha='center', fontsize=10)
    ax.set_ylabel("Messages Sent")
    ax.set_title("Total Messages")
    ax.grid(True, alpha=0.3, axis="y")

    # Words sent
    ax = axes[1]
    means = [np.mean(model_volume[m]["words"]) for m in models]
    stds = [np.std(model_volume[m]["words"]) for m in models]
    bars = ax.bar(models, means, yerr=stds, capsize=5, color=colors, edgecolor='black')
    for bar, mean in zip(bars, means):
        ax.annotate(f'{mean:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 5), textcoords="offset points", ha='center', fontsize=10)
    ax.set_ylabel("Words Sent")
    ax.set_title("Total Words")
    ax.grid(True, alpha=0.3, axis="y")

    # Average message length
    ax = axes[2]
    means = [np.mean(model_volume[m]["avg_length"]) for m in models]
    stds = [np.std(model_volume[m]["avg_length"]) for m in models]
    bars = ax.bar(models, means, yerr=stds, capsize=5, color=colors, edgecolor='black')
    for bar, mean in zip(bars, means):
        ax.annotate(f'{mean:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 5), textcoords="offset points", ha='center', fontsize=10)
    ax.set_ylabel("Words per Message")
    ax.set_title("Avg Message Length")
    ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle(f"Communication Volume by Model ({len(press_games)} press games)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


def plot_saydo_rate(games_data: list, output_path: Path):
    """Bar chart of say-do correlation by model (did they do what they said?)."""
    from diplomacy_game_engine.scoring.press_analyzer import PressAnalyzer

    press_games = [g for g in games_data if g["game_type"] == "press"]
    if not press_games:
        print("No press games for say-do analysis")
        return

    model_saydo = defaultdict(lambda: {"rates": [], "made": [], "kept": []})

    for game in press_games:
        game_path = GAMES_DIR / game["game_id"]
        try:
            analyzer = PressAnalyzer(str(game_path))
            sd = analyzer.analyze_saydo()

            for power, model_id in game["assignments"].items():
                model = normalize_model(model_id)
                if power in sd and sd[power]["saydo_rate"] is not None:
                    model_saydo[model]["rates"].append(sd[power]["saydo_rate"])
                    model_saydo[model]["made"].append(sd[power]["promises_made"])
                    model_saydo[model]["kept"].append(sd[power]["promises_kept"])
        except Exception as e:
            print(f"Warning: Could not analyze say-do for {game['game_id']}: {e}")

    models = [m for m in MODEL_ORDER if m in model_saydo and model_saydo[m]["rates"]]
    if not models:
        print("No say-do data collected")
        return

    # Plot
    fig, ax = plt.subplots(figsize=(10, 7))

    means = [np.mean(model_saydo[m]["rates"]) * 100 for m in models]
    stds = [np.std(model_saydo[m]["rates"]) * 100 for m in models]
    total_made = [sum(model_saydo[m]["made"]) for m in models]
    total_kept = [sum(model_saydo[m]["kept"]) for m in models]
    colors = [MODEL_COLORS.get(m) for m in models]

    bars = ax.bar(models, means, yerr=stds, capsize=5, color=colors, edgecolor='black', width=0.6)

    for bar, mean, made, kept in zip(bars, means, total_made, total_kept):
        ax.annotate(f'{mean:.0f}%\n({kept}/{made})',
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 8), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Say-Do Rate (%)", fontsize=12)
    ax.set_title(f"Say-Do Correlation by Model ({len(press_games)} press games)", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis="y")

    ax.text(0.02, 0.98, "Say-Do = explicit order mentions in press\nthat matched actual submitted orders",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# LEGACY CHARTS (kept for backwards compatibility)
# =============================================================================

def plot_sc_by_model_average(games_data: list, output_path: Path):
    """Plot average SC per model over time."""
    model_sc_by_year = defaultdict(lambda: defaultdict(list))

    for game in games_data:
        assignments = game["assignments"]
        sc_counts = game["sc_counts"]

        for power, model_id in assignments.items():
            model = normalize_model(model_id)
            for year, counts in sc_counts.items():
                if power in counts:
                    model_sc_by_year[model][year].append(counts[power])

    all_years = set()
    for model_data in model_sc_by_year.values():
        all_years.update(model_data.keys())
    years = sorted(all_years)

    # Calculate survival years
    model_survival = defaultdict(list)
    for game in games_data:
        assignments = game["assignments"]
        sc_counts = game["sc_counts"]
        game_years = sorted(sc_counts.keys())
        if not game_years:
            continue
        start_year = game_years[0]

        for power, model_id in assignments.items():
            model = normalize_model(model_id)
            survival = 0
            for year in game_years:
                if sc_counts.get(year, {}).get(power, 0) > 0:
                    survival = year - start_year + 1
            model_survival[model].append(survival)

    survival_years = {m: np.mean(yrs) for m, yrs in model_survival.items()}

    # Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    markers = {"Haiku": "s", "Sonnet": "o", "Opus": "^"}
    linestyles = {"Haiku": "--", "Sonnet": "-", "Opus": "-."}

    for model in MODEL_ORDER:
        if model not in model_sc_by_year:
            continue
        year_data = model_sc_by_year[model]
        means = [np.mean(year_data.get(y, [0])) for y in years]

        ax.plot(years, means, marker=markers.get(model, "o"),
                linestyle=linestyles.get(model, "-"), linewidth=2.5, markersize=8,
                label=model, color=MODEL_COLORS[model])

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Average Supply Centers", fontsize=12)
    ax.set_title(f"Average SC by Model ({len(games_data)} games)", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 18)

    # Survival annotation
    survival_text = "Avg Survival Years:\n"
    for model in ["Opus", "Sonnet", "Haiku"]:
        if model in survival_years:
            survival_text += f"  {model}: {survival_years[model]:.1f}\n"

    ax.text(0.98, 0.98, survival_text.strip(), transform=ax.transAxes, fontsize=10,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.9),
            family="monospace")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def find_games(pattern: str = None, game_ids: list = None, all_games: bool = False) -> list:
    """Find game directories based on input."""
    if all_games:
        return sorted([d.name for d in GAMES_DIR.iterdir()
                      if d.is_dir() and not d.name.startswith(".") and d.name != "archive"])

    if pattern:
        matches = []
        for d in GAMES_DIR.iterdir():
            if d.is_dir() and glob_module.fnmatch.fnmatch(d.name, pattern):
                matches.append(d.name)
        return sorted(matches)

    if game_ids:
        return game_ids

    return []


def main():
    parser = argparse.ArgumentParser(description="Generate SC comparison charts")
    parser.add_argument("game_ids", nargs="*", help="Game IDs to include")
    parser.add_argument("--pattern", "-p", help="Glob pattern for game IDs")
    parser.add_argument("--all", "-a", action="store_true", help="Include all games")
    parser.add_argument("--output", "-o", help="Output filename prefix")
    parser.add_argument("--type", "-t",
                        choices=["scientific", "press_comparison", "average", "all"],
                        default="scientific", help="Chart type")

    args = parser.parse_args()

    game_ids = find_games(pattern=args.pattern, game_ids=args.game_ids, all_games=args.all)

    if not game_ids:
        print("No games specified. Use --help for usage.")
        sys.exit(1)

    print(f"Loading {len(game_ids)} games...")

    games_data = []
    for gid in game_ids:
        data = load_game_data(gid)
        if data:
            games_data.append(data)

    if not games_data:
        print("No valid game data found.")
        sys.exit(1)

    # Count game types
    gunboat_count = sum(1 for g in games_data if g["game_type"] == "gunboat")
    press_count = sum(1 for g in games_data if g["game_type"] == "press")
    print(f"Loaded {len(games_data)} games ({gunboat_count} gunboat, {press_count} press)")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = args.output or f"analysis_{timestamp}"

    # Generate charts
    if args.type in ["scientific", "all"]:
        plot_average_rank(games_data, GAMES_DIR / f"{base_name}_rank.png")
        plot_win_rate(games_data, GAMES_DIR / f"{base_name}_winrate.png")
        plot_early_game_complexity(games_data, GAMES_DIR / f"{base_name}_early_complexity.png")

    if args.type in ["press_comparison", "all"]:
        if press_count > 0 and gunboat_count > 0:
            plot_press_comparison_rank(games_data, GAMES_DIR / f"{base_name}_press_rank.png")
            plot_press_impact_delta(games_data, GAMES_DIR / f"{base_name}_press_delta.png")
        else:
            print("Skipping press comparison (need both gunboat and press games)")

        if press_count > 0:
            plot_press_volume(games_data, GAMES_DIR / f"{base_name}_press_volume.png")
            plot_saydo_rate(games_data, GAMES_DIR / f"{base_name}_saydo.png")

    if args.type in ["average", "all"]:
        plot_sc_by_model_average(games_data, GAMES_DIR / f"{base_name}_avg.png")


if __name__ == "__main__":
    main()
