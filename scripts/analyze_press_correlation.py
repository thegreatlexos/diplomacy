#!/usr/bin/env python3
"""
Analyze correlation between press quality and game outcomes.

Extracts press evaluation scores and ranks from SCORING_REPORT.md files
across all press games to answer: does deception help? Does honesty hurt?

Usage:
    python scripts/analyze_press_correlation.py
"""

import json
import re
from pathlib import Path
from collections import defaultdict

GAMES_DIR = Path(__file__).parent.parent / "games"


def extract_press_data(game_dir: Path) -> dict:
    """Extract press scores and rankings from SCORING_REPORT.md."""
    scoring_report = game_dir / "SCORING_REPORT.md"
    if not scoring_report.exists():
        return None

    with open(scoring_report) as f:
        content = f.read()

    # Check if this is a press game
    if "Press Evaluation Scores" not in content:
        return None

    # Extract model assignments
    assignments_file = game_dir / "model_assignments.json"
    if not assignments_file.exists():
        return None

    with open(assignments_file) as f:
        assignments_data = json.load(f)

    # Extract rankings (from "Overall Rankings" table)
    rankings = {}
    ranking_section = re.search(
        r"## Overall Rankings\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)",
        content,
        re.MULTILINE,
    )
    if ranking_section:
        for line in ranking_section.group(1).strip().split("\n"):
            match = re.match(r"\|\s*(\d+)\s*\|\s*([A-Za-z-]+)\s*\|", line)
            if match:
                rank = int(match.group(1))
                power = match.group(2).strip()
                rankings[power] = rank

    # Extract press scores (from "Press Evaluation Scores" table)
    press_scores = {}
    press_section = re.search(
        r"## Press Evaluation Scores\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)",
        content,
        re.MULTILINE,
    )
    if press_section:
        for line in press_section.group(1).strip().split("\n"):
            match = re.match(
                r"\|\s*([A-Za-z-]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
                line,
            )
            if match:
                power = match.group(1).strip()
                truthfulness = float(match.group(2))
                cooperation = float(match.group(3))
                deception = float(match.group(4))
                press_scores[power] = {
                    "truthfulness": truthfulness,
                    "cooperation": cooperation,
                    "deception": deception,
                }

    if not rankings or not press_scores:
        return None

    # Combine data
    results = []
    for power in rankings.keys():
        if power in press_scores:
            model_id = assignments_data.get("assignments", {}).get(power, "unknown")
            results.append(
                {
                    "game": game_dir.name,
                    "power": power,
                    "model": model_id,
                    "rank": rankings[power],
                    "truthfulness": press_scores[power]["truthfulness"],
                    "cooperation": press_scores[power]["cooperation"],
                    "deception": press_scores[power]["deception"],
                }
            )

    return results


def main():
    press_games = [
        d for d in GAMES_DIR.iterdir() if d.is_dir() and "press" in d.name.lower()
    ]

    print(f"Analyzing {len(press_games)} press games...\n")

    all_data = []
    for game_dir in press_games:
        data = extract_press_data(game_dir)
        if data:
            all_data.extend(data)

    if not all_data:
        print("No valid press data found.")
        return

    print(f"Extracted {len(all_data)} power observations across press games\n")

    # Calculate correlations
    import numpy as np

    ranks = [d["rank"] for d in all_data]
    truthfulness = [d["truthfulness"] for d in all_data]
    cooperation = [d["cooperation"] for d in all_data]
    deception = [d["deception"] for d in all_data]

    corr_truth = np.corrcoef(truthfulness, ranks)[0, 1]
    corr_coop = np.corrcoef(cooperation, ranks)[0, 1]
    corr_decep = np.corrcoef(deception, ranks)[0, 1]

    print("=== PRESS QUALITY CORRELATIONS WITH FINAL RANK ===")
    print(f"(negative correlation = quality helps performance)\n")
    print(f"Truthfulness vs Rank:  {corr_truth:+.3f}")
    print(f"Cooperation vs Rank:   {corr_coop:+.3f}")
    print(f"Deception vs Rank:     {corr_decep:+.3f}")
    print()

    # Group by rank tiers
    winners = [d for d in all_data if d["rank"] == 1]
    top3 = [d for d in all_data if d["rank"] <= 3]
    bottom3 = [d for d in all_data if d["rank"] >= 5]

    if winners:
        print(f"=== WINNERS (rank 1, n={len(winners)}) ===")
        avg_truth = np.mean([d["truthfulness"] for d in winners])
        avg_coop = np.mean([d["cooperation"] for d in winners])
        avg_decep = np.mean([d["deception"] for d in winners])
        print(f"Avg Truthfulness: {avg_truth:.2f}")
        print(f"Avg Cooperation:  {avg_coop:.2f}")
        print(f"Avg Deception:    {avg_decep:.2f}")
        print()

    if top3:
        print(f"=== TOP 3 (rank 1-3, n={len(top3)}) ===")
        avg_truth = np.mean([d["truthfulness"] for d in top3])
        avg_coop = np.mean([d["cooperation"] for d in top3])
        avg_decep = np.mean([d["deception"] for d in top3])
        print(f"Avg Truthfulness: {avg_truth:.2f}")
        print(f"Avg Cooperation:  {avg_coop:.2f}")
        print(f"Avg Deception:    {avg_decep:.2f}")
        print()

    if bottom3:
        print(f"=== BOTTOM 3 (rank 5-7, n={len(bottom3)}) ===")
        avg_truth = np.mean([d["truthfulness"] for d in bottom3])
        avg_coop = np.mean([d["cooperation"] for d in bottom3])
        avg_decep = np.mean([d["deception"] for d in bottom3])
        print(f"Avg Truthfulness: {avg_truth:.2f}")
        print(f"Avg Cooperation:  {avg_coop:.2f}")
        print(f"Avg Deception:    {avg_decep:.2f}")
        print()

    # Most deceptive vs most truthful
    all_data_sorted_decep = sorted(all_data, key=lambda x: x["deception"], reverse=True)
    all_data_sorted_truth = sorted(
        all_data, key=lambda x: x["truthfulness"], reverse=True
    )

    print("=== MOST DECEPTIVE POWERS (top 5) ===")
    for d in all_data_sorted_decep[:5]:
        print(
            f"{d['game'][:30]:30s} | {d['power']:15s} | Rank {d['rank']} | Deception: {d['deception']:.1f} | Truth: {d['truthfulness']:.1f}"
        )
    print()

    print("=== MOST TRUTHFUL POWERS (top 5) ===")
    for d in all_data_sorted_truth[:5]:
        print(
            f"{d['game'][:30]:30s} | {d['power']:15s} | Rank {d['rank']} | Truth: {d['truthfulness']:.1f} | Deception: {d['deception']:.1f}"
        )
    print()

    # Save raw data
    output_file = Path(__file__).parent / "data" / "press_correlation.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(
            {
                "correlations": {
                    "truthfulness_vs_rank": corr_truth,
                    "cooperation_vs_rank": corr_coop,
                    "deception_vs_rank": corr_decep,
                },
                "summary_stats": {
                    "winners": {
                        "n": len(winners),
                        "avg_truthfulness": float(
                            np.mean([d["truthfulness"] for d in winners])
                        )
                        if winners
                        else 0,
                        "avg_cooperation": float(
                            np.mean([d["cooperation"] for d in winners])
                        )
                        if winners
                        else 0,
                        "avg_deception": float(
                            np.mean([d["deception"] for d in winners])
                        )
                        if winners
                        else 0,
                    },
                    "top3": {
                        "n": len(top3),
                        "avg_truthfulness": float(
                            np.mean([d["truthfulness"] for d in top3])
                        )
                        if top3
                        else 0,
                        "avg_cooperation": float(
                            np.mean([d["cooperation"] for d in top3])
                        )
                        if top3
                        else 0,
                        "avg_deception": float(np.mean([d["deception"] for d in top3]))
                        if top3
                        else 0,
                    },
                    "bottom3": {
                        "n": len(bottom3),
                        "avg_truthfulness": float(
                            np.mean([d["truthfulness"] for d in bottom3])
                        )
                        if bottom3
                        else 0,
                        "avg_cooperation": float(
                            np.mean([d["cooperation"] for d in bottom3])
                        )
                        if bottom3
                        else 0,
                        "avg_deception": float(
                            np.mean([d["deception"] for d in bottom3])
                        )
                        if bottom3
                        else 0,
                    },
                },
                "raw_data": all_data,
            },
            f,
            indent=2,
        )
    print(f"Saved raw data to: {output_file}")


if __name__ == "__main__":
    main()
