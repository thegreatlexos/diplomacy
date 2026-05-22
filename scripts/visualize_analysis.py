#!/usr/bin/env python3
"""
Generate publication-ready visualizations from saved analysis data.

Usage:
    python scripts/visualize_analysis.py --input scripts/data/analysis_20260520_142201.json
    python scripts/visualize_analysis.py --latest
"""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "games"

# Publication styling
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = {
    "budget": "#e74c3c",    # red
    "mid": "#f39c12",       # orange
    "premium": "#2ecc71",   # green
    "reasoning": "#3498db", # blue
    "non_reasoning": "#95a5a6", # gray
}

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


def find_latest_analysis() -> Path:
    """Find most recent analysis JSON file."""
    json_files = sorted(DATA_DIR.glob("analysis_*.json"))
    if not json_files:
        raise FileNotFoundError("No analysis files found in scripts/data/")
    return json_files[-1]


def load_analysis(json_path: Path) -> dict:
    """Load analysis results from JSON."""
    with open(json_path) as f:
        return json.load(f)


# =============================================================================
# CHART 1: ANTHROPIC TIER HIERARCHY
# =============================================================================

def plot_anthropic_tiers(data: dict, output_path: Path):
    """Bar chart: Haiku vs Sonnet vs Opus performance."""
    tiers_data = data.get("anthropic_tiers", {})
    if not tiers_data:
        print("No Anthropic tier data available")
        return

    tiers = ["budget", "mid", "premium"]
    tier_labels = ["Haiku\n(Budget)", "Sonnet\n(Mid)", "Opus\n(Premium)"]

    ranks = [tiers_data[t]["avg_rank"] for t in tiers if t in tiers_data]
    win_rates = [tiers_data[t]["win_rate"] for t in tiers if t in tiers_data]
    ns = [tiers_data[t]["n"] for t in tiers if t in tiers_data]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Average rank
    colors = [COLORS[t] for t in tiers]
    bars = ax1.bar(tier_labels, ranks, color=colors, edgecolor='black', linewidth=1.5, width=0.6)

    for bar, rank, n in zip(bars, ranks, ns):
        ax1.annotate(f'{rank:.2f}\n(n={n})',
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 8), textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax1.set_ylabel("Average Final Rank (lower = better)", fontsize=13, fontweight='bold')
    ax1.set_title("Anthropic Model Tier Performance", fontsize=15, fontweight='bold')
    ax1.set_ylim(0, 7)
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.tick_params(axis='x', labelsize=11)

    # Win rate
    bars = ax2.bar(tier_labels, win_rates, color=colors, edgecolor='black', linewidth=1.5, width=0.6)

    for bar, rate in zip(bars, win_rates):
        ax2.annotate(f'{rate:.1f}%',
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax2.set_ylabel("Win Rate (%)", fontsize=13, fontweight='bold')
    ax2.set_title("Solo Victory Rate by Tier", fontsize=15, fontweight='bold')
    ax2.set_ylim(0, max(win_rates) * 1.3 if win_rates else 50)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.tick_params(axis='x', labelsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# CHART 2: MID-TIER PROVIDER BATTLE
# =============================================================================

def plot_provider_battle_mid(data: dict, output_path: Path):
    """Bar chart: Mid-tier provider comparison."""
    battle_data = data.get("provider_battle_mid", {})
    if not battle_data:
        print("No mid-tier battle data available")
        return

    # Sort by average rank
    sorted_providers = sorted(battle_data.items(), key=lambda x: x[1]["avg_rank"])

    providers = [p for p, _ in sorted_providers]
    ranks = [d["avg_rank"] for _, d in sorted_providers]
    win_rates = [d["win_rate"] for _, d in sorted_providers]
    ns = [d["n"] for _, d in sorted_providers]
    colors = [PROVIDER_COLORS.get(p, "#95a5a6") for p in providers]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Average rank
    bars = ax1.barh(providers, ranks, color=colors, edgecolor='black', linewidth=1.5)

    for bar, rank, n in zip(bars, ranks, ns):
        ax1.annotate(f'{rank:.2f} (n={n})',
                    xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                    xytext=(5, 0), textcoords="offset points",
                    ha='left', va='center', fontsize=11, fontweight='bold')

    ax1.set_xlabel("Average Final Rank (lower = better)", fontsize=13, fontweight='bold')
    ax1.set_title("Mid-Tier Provider Showdown: Rank", fontsize=15, fontweight='bold')
    ax1.invert_xaxis()
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.tick_params(axis='y', labelsize=12)

    # Win rate
    bars = ax2.barh(providers, win_rates, color=colors, edgecolor='black', linewidth=1.5)

    for bar, rate in zip(bars, win_rates):
        if rate > 0:
            ax2.annotate(f'{rate:.1f}%',
                        xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                        xytext=(5, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=11, fontweight='bold')

    ax2.set_xlabel("Win Rate (%)", fontsize=13, fontweight='bold')
    ax2.set_title("Mid-Tier Provider Showdown: Wins", fontsize=15, fontweight='bold')
    ax2.set_xlim(0, max(win_rates) * 1.3 if win_rates else 100)
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.tick_params(axis='y', labelsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# CHART 3: PREMIUM-TIER PROVIDER BATTLE
# =============================================================================

def plot_provider_battle_premium(data: dict, output_path: Path):
    """Bar chart: Premium-tier provider comparison."""
    battle_data = data.get("provider_battle_premium", {})
    if not battle_data:
        print("No premium-tier battle data available (need more games)")
        return

    # Sort by average rank
    sorted_providers = sorted(battle_data.items(), key=lambda x: x[1]["avg_rank"])

    providers = [p for p, _ in sorted_providers]
    ranks = [d["avg_rank"] for _, d in sorted_providers]
    win_rates = [d["win_rate"] for _, d in sorted_providers]
    ns = [d["n"] for _, d in sorted_providers]
    models = [", ".join(d["models"]) for _, d in sorted_providers]
    colors = [PROVIDER_COLORS.get(p, "#95a5a6") for p in providers]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Average rank
    bars = ax1.barh(providers, ranks, color=colors, edgecolor='black', linewidth=1.5)

    for bar, rank, n, model in zip(bars, ranks, ns, models):
        ax1.annotate(f'{rank:.2f} (n={n})',
                    xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                    xytext=(5, 0), textcoords="offset points",
                    ha='left', va='center', fontsize=11, fontweight='bold')

    ax1.set_xlabel("Average Final Rank (lower = better)", fontsize=13, fontweight='bold')
    ax1.set_title("Premium-Tier Provider Battle: Rank", fontsize=15, fontweight='bold')
    ax1.invert_xaxis()
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.tick_params(axis='y', labelsize=12)

    # Win rate
    bars = ax2.barh(providers, win_rates, color=colors, edgecolor='black', linewidth=1.5)

    for bar, rate in zip(bars, win_rates):
        if rate > 0:
            ax2.annotate(f'{rate:.1f}%',
                        xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                        xytext=(5, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=11, fontweight='bold')

    ax2.set_xlabel("Win Rate (%)", fontsize=13, fontweight='bold')
    ax2.set_title("Premium-Tier Provider Battle: Wins", fontsize=15, fontweight='bold')
    ax2.set_xlim(0, max(win_rates) * 1.3 if win_rates else 100)
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.tick_params(axis='y', labelsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# CHART 4: PRESS EFFECTIVENESS BY TIER
# =============================================================================

def plot_press_effectiveness(data: dict, output_path: Path):
    """Bar chart: Press impact by tier."""
    press_data = data.get("press_effectiveness", {})
    if not press_data:
        print("No press effectiveness data available")
        return

    tiers = ["budget", "mid", "premium"]
    tier_labels = ["Budget\n(Haiku)", "Mid\n(Sonnet/Mini)", "Premium\n(Opus/GPT-5)"]

    deltas = [press_data[t]["delta"] for t in tiers if t in press_data]
    gunboat_ranks = [press_data[t]["gunboat_avg_rank"] for t in tiers if t in press_data]
    press_ranks = [press_data[t]["press_avg_rank"] for t in tiers if t in press_data]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Delta (press impact)
    colors = ['#2ecc71' if d > 0 else '#e74c3c' for d in deltas]
    bars = ax1.bar(tier_labels, deltas, color=colors, edgecolor='black', linewidth=1.5, width=0.6)

    for bar, delta in zip(bars, deltas):
        va = 'bottom' if delta >= 0 else 'top'
        offset = 8 if delta >= 0 else -8
        ax1.annotate(f'{delta:+.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, offset), textcoords="offset points",
                    ha='center', va=va, fontsize=13, fontweight='bold')

    ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax1.set_ylabel("Rank Change\n(positive = press helps)", fontsize=13, fontweight='bold')
    ax1.set_title("Press Impact by Tier", fontsize=15, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.tick_params(axis='x', labelsize=11)

    # Gunboat vs Press comparison
    x = np.arange(len(tier_labels))
    width = 0.35

    bars1 = ax2.bar(x - width/2, gunboat_ranks, width, label='Gunboat',
                   color='#7f8c8d', edgecolor='black', linewidth=1.5)
    bars2 = ax2.bar(x + width/2, press_ranks, width, label='Press',
                   color='#9b59b6', edgecolor='black', linewidth=1.5)

    for bars, ranks in [(bars1, gunboat_ranks), (bars2, press_ranks)]:
        for bar, rank in zip(bars, ranks):
            ax2.annotate(f'{rank:.2f}',
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax2.set_ylabel("Average Final Rank", fontsize=13, fontweight='bold')
    ax2.set_title("Gunboat vs Press by Tier", fontsize=15, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(tier_labels, fontsize=11)
    ax2.legend(fontsize=11, loc='upper right')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# CHART 5: REASONING VS NON-REASONING
# =============================================================================

def plot_reasoning_comparison(data: dict, output_path: Path):
    """Bar chart: Reasoning vs non-reasoning models."""
    reasoning_data = data.get("reasoning_comparison", {})
    if not reasoning_data:
        print("No reasoning comparison data available")
        return

    categories = []
    ranks = []
    invalid_rates = []
    complexity_rates = []
    ns = []

    if "reasoning" in reasoning_data:
        categories.append("Reasoning\n(Opus, GPT-5, DeepSeek)")
        ranks.append(reasoning_data["reasoning"]["avg_rank"])
        invalid_rates.append(reasoning_data["reasoning"]["avg_invalid_rate"])
        complexity_rates.append(reasoning_data["reasoning"]["avg_complexity"])
        ns.append(reasoning_data["reasoning"]["n"])

    if "non_reasoning" in reasoning_data:
        categories.append("Non-Reasoning\n(Grok, Gemini, Mistral, etc.)")
        ranks.append(reasoning_data["non_reasoning"]["avg_rank"])
        invalid_rates.append(reasoning_data["non_reasoning"]["avg_invalid_rate"])
        complexity_rates.append(reasoning_data["non_reasoning"]["avg_complexity"])
        ns.append(reasoning_data["non_reasoning"]["n"])

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    colors = [COLORS["reasoning"], COLORS["non_reasoning"]]

    # Average rank
    ax = axes[0]
    bars = ax.bar(categories, ranks, color=colors, edgecolor='black', linewidth=1.5, width=0.5)
    for bar, rank, n in zip(bars, ranks, ns):
        ax.annotate(f'{rank:.2f}\n(n={n})',
                   xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 8), textcoords="offset points",
                   ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_ylabel("Average Final Rank", fontsize=13, fontweight='bold')
    ax.set_title("Performance", fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='x', labelsize=10)

    # Invalid order rate
    ax = axes[1]
    bars = ax.bar(categories, invalid_rates, color=colors, edgecolor='black', linewidth=1.5, width=0.5)
    for bar, rate in zip(bars, invalid_rates):
        ax.annotate(f'{rate:.1f}%',
                   xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 5), textcoords="offset points",
                   ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_ylabel("Invalid Order Rate (%)", fontsize=13, fontweight='bold')
    ax.set_title("Reliability", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='x', labelsize=10)

    # Order complexity
    ax = axes[2]
    bars = ax.bar(categories, complexity_rates, color=colors, edgecolor='black', linewidth=1.5, width=0.5)
    for bar, rate in zip(bars, complexity_rates):
        ax.annotate(f'{rate:.1f}%',
                   xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 5), textcoords="offset points",
                   ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_ylabel("Complexity Rate (%)", fontsize=13, fontweight='bold')
    ax.set_title("Tactical Sophistication", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(axis='x', labelsize=10)

    fig.suptitle("Reasoning vs Non-Reasoning Models", fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# CHART 6: TEMPORAL DYNAMICS
# =============================================================================

def plot_temporal_dynamics(data: dict, output_path: Path):
    """Line chart: Early vs late game performance by tier."""
    temporal_data = data.get("temporal_dynamics", {})
    if not temporal_data:
        print("No temporal dynamics data available")
        return

    tiers = ["budget", "mid", "premium"]
    tier_labels = ["Budget", "Mid", "Premium"]

    early_scs = [temporal_data[t]["early_avg_sc"] for t in tiers if t in temporal_data]
    late_scs = [temporal_data[t]["late_avg_sc"] for t in tiers if t in temporal_data]

    fig, ax = plt.subplots(figsize=(10, 7))

    x = np.arange(len(tier_labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, early_scs, width, label='Early Game (Y1-5)',
                   color='#3498db', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, late_scs, width, label='Late Game (Y11+)',
                   color='#e74c3c', edgecolor='black', linewidth=1.5)

    for bars, scs in [(bars1, early_scs), (bars2, late_scs)]:
        for bar, sc in zip(bars, scs):
            if sc > 0:
                ax.annotate(f'{sc:.1f}',
                           xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                           xytext=(0, 5), textcoords="offset points",
                           ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_ylabel("Average Supply Centers", fontsize=13, fontweight='bold')
    ax.set_xlabel("Model Tier", fontsize=13, fontweight='bold')
    ax.set_title("Temporal Performance: Early vs Late Game", fontsize=15, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tier_labels, fontsize=12)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(max(early_scs), max(late_scs)) * 1.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate visualizations from analysis data")
    parser.add_argument("--input", "-i", type=Path, help="Input JSON file")
    parser.add_argument("--latest", "-l", action="store_true", help="Use latest analysis file")
    parser.add_argument("--output-prefix", "-o", help="Output filename prefix")

    args = parser.parse_args()

    # Find input file
    if args.latest:
        json_path = find_latest_analysis()
        print(f"Using latest analysis: {json_path}")
    elif args.input:
        json_path = args.input
    else:
        print("Error: Specify --input or --latest")
        return

    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        return

    # Load data
    data = load_analysis(json_path)

    # Output prefix
    timestamp = json_path.stem.replace("analysis_", "")
    prefix = args.output_prefix or f"viz_{timestamp}"

    # Generate charts
    print("\nGenerating visualizations...")

    plot_anthropic_tiers(data, OUTPUT_DIR / f"{prefix}_anthropic_tiers.png")
    plot_provider_battle_mid(data, OUTPUT_DIR / f"{prefix}_provider_mid.png")
    plot_provider_battle_premium(data, OUTPUT_DIR / f"{prefix}_provider_premium.png")
    plot_press_effectiveness(data, OUTPUT_DIR / f"{prefix}_press_effectiveness.png")
    plot_reasoning_comparison(data, OUTPUT_DIR / f"{prefix}_reasoning_comparison.png")
    plot_temporal_dynamics(data, OUTPUT_DIR / f"{prefix}_temporal_dynamics.png")

    print(f"\nAll visualizations saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
