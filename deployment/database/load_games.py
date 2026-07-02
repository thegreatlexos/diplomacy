#!/usr/bin/env python3
import sys
# Add user site-packages to path (where psycopg2-binary is installed)
import site
sys.path.insert(0, site.USER_SITE)
"""
Load Diplomacy game data into Postgres database.

Usage:
    python load_games.py --games-dir ../../games --db-url postgresql://user:pass@localhost/diplomacy_ai
"""

import json
import argparse
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_batch
import re

# Excluded games (DeepSeek stalemates)
EXCLUDED_GAMES = []

POWERS = ["England", "France", "Germany", "Italy", "Austria-Hungary", "Russia", "Turkey"]

MODEL_TIERS = {
    "budget": ["haiku-4-5", "llama-3.1-8b"],
    "mid": ["sonnet-4-6", "gpt-4.1-mini", "grok-4.1-fast", "gemini-3.1-flash", "mistral-small", "qwen3.5-flash"],
    "premium": ["opus-4", "gpt-5", "grok-4.3", "gemini-3.1-pro", "deepseek-v4-pro", "mistral-large", "llama-4-maverick"],
}

def classify_tier(model_id: str) -> str:
    """Classify model tier."""
    model_lower = model_id.lower()
    for tier, keywords in MODEL_TIERS.items():
        if any(kw in model_lower for kw in keywords):
            return tier
    return "unknown"

def classify_provider(model_id: str) -> str:
    """Classify provider from model ID."""
    model_lower = model_id.lower()
    if "claude" in model_lower or "opus" in model_lower or "sonnet" in model_lower or "haiku" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower or "openai" in model_lower:
        return "openai"
    elif "grok" in model_lower:
        return "xai"
    elif "gemini" in model_lower or "google" in model_lower:
        return "google"
    elif "deepseek" in model_lower:
        return "deepseek"
    elif "mistral" in model_lower:
        return "mistral"
    elif "llama" in model_lower:
        return "meta"
    elif "qwen" in model_lower:
        return "qwen"
    return "unknown"

def should_exclude_game(game_dir: Path) -> bool:
    """Check if game should be excluded (deepseek stalemates)."""
    if "deepseek" not in game_dir.name.lower():
        return False

    yearly_metrics = game_dir / "yearly_metrics.json"
    if not yearly_metrics.exists():
        return False

    with open(yearly_metrics) as f:
        data = json.load(f)

    sc_counts = data.get("sc_counts", {})
    if not sc_counts:
        return False

    final_year = max(int(y) for y in sc_counts.keys())
    final_scs = sc_counts[str(final_year)]
    max_sc = max(final_scs.values())

    # Exclude if stalemate (< 18 SCs and hit year 20+)
    if max_sc < 18 and final_year >= 1920:
        print(f"  EXCLUDING: {game_dir.name} (deepseek stalemate)")
        return True

    return False

def parse_scoring_report(scoring_report_path: Path):
    """Parse SCORING_REPORT.md and extract all metrics."""
    if not scoring_report_path.exists():
        return None

    with open(scoring_report_path) as f:
        content = f.read()

    data = {
        "rankings": {},
        "press_scores": {},
        "power_scores": {},
        "turn_metrics": [],
        "press_metrics": []
    }

    # Parse Overall Rankings
    ranking_match = re.search(r"## Overall Rankings\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)", content, re.MULTILINE)
    if ranking_match:
        for line in ranking_match.group(1).strip().split("\n"):
            match = re.match(r"\|\s*(\d+)\s*\|\s*([A-Za-z-]+)\s*\|\s*([\d-]+)\s*\|\s*([\d-]+)\s*\|\s*([\d-]+)\s*\|", line)
            if match:
                power = match.group(2).strip()
                data["rankings"][power] = int(match.group(1))
                data["power_scores"][power] = {
                    "total_score": int(match.group(3)),
                    "performance_score": int(match.group(4)),
                    "precision_score": int(match.group(5))
                }

    # Parse Press Evaluation Scores (game-level averages)
    press_match = re.search(r"## Press Evaluation Scores\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)", content, re.MULTILINE)
    if press_match:
        for line in press_match.group(1).strip().split("\n"):
            match = re.match(r"\|\s*([A-Za-z-]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", line)
            if match:
                power = match.group(1).strip()
                data["press_scores"][power] = {
                    "truthfulness": float(match.group(2)),
                    "cooperation": float(match.group(3)),
                    "deception": float(match.group(4))
                }

    # Parse Precision Scores - Detailed Breakdown
    precision_match = re.search(r"## Precision Scores - Detailed Breakdown\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)", content, re.MULTILINE)
    if precision_match:
        for line in precision_match.group(1).strip().split("\n"):
            match = re.match(r"\|\s*([A-Za-z-]+)\s*\|[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
            if match:
                power = match.group(1).strip()
                if power in data["power_scores"]:
                    data["power_scores"][power].update({
                        "total_invalid_orders": int(match.group(2)),
                        "total_convoys": int(match.group(3)),
                        "total_supports_own": int(match.group(4)),
                        "total_supports_other": int(match.group(5)),
                        "total_supports_hold": int(match.group(6)),
                        "total_supports_attack": int(match.group(7)),
                        "total_bounces": int(match.group(8))
                    })

    # Parse Per-Year Precision Metrics
    year_sections = re.findall(r"### Year (\d+)\s+\|.*?\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.*?\|\s*\n)+)", content, re.MULTILINE)
    for year_str, table_content in year_sections:
        year = int(year_str)
        for line in table_content.strip().split("\n"):
            match = re.match(r"\|\s*([A-Za-z-]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
            if match:
                power = match.group(1).strip()
                # Assume spring and fall for each year (can't distinguish from report)
                for season in ["spring", "fall"]:
                    data["turn_metrics"].append({
                        "year": year,
                        "season": season,
                        "power": power,
                        "invalid_orders": int(match.group(2)),
                        "convoys": int(match.group(3)),
                        "supports_own": int(match.group(4)),
                        "supports_other": int(match.group(5)),
                        "bounces": int(match.group(6))
                    })

    return data

def load_game(conn, game_dir: Path):
    """Load a single game into the database."""
    game_id = game_dir.name

    # Check if already loaded
    cur = conn.cursor()
    cur.execute("SELECT id FROM games WHERE game_id = %s", (game_id,))
    if cur.fetchone():
        print(f"  SKIP: {game_id} (already loaded)")
        return

    print(f"  LOADING: {game_id}")

    # Determine mode and platform
    mode = "press" if "press" in game_id.lower() else "gunboat"
    platform = "bedrock" if "bedrock" in game_id.lower() else "openrouter"

    # Load model assignments
    assignments_file = game_dir / "model_assignments.json"
    if not assignments_file.exists():
        print(f"    SKIP: No model_assignments.json")
        return

    with open(assignments_file) as f:
        assignments_data = json.load(f)

    assignments = assignments_data.get("assignments", {})

    # Load yearly metrics
    yearly_metrics_file = game_dir / "yearly_metrics.json"
    if not yearly_metrics_file.exists():
        print(f"    SKIP: No yearly_metrics.json")
        return

    with open(yearly_metrics_file) as f:
        yearly_data = json.load(f)

    sc_counts = yearly_data.get("sc_counts", {})
    if not sc_counts:
        print(f"    SKIP: No SC data")
        return

    # Determine winner
    final_year = max(int(y) for y in sc_counts.keys())
    final_scs = sc_counts[str(final_year)]
    winner_power = max(final_scs, key=final_scs.get)
    winner_scs = final_scs[winner_power]
    winner_model = assignments.get(winner_power, "unknown")

    status = "solo" if winner_scs >= 18 else ("stalemate" if final_year >= 1920 else "incomplete")

    # Insert game
    cur.execute("""
        INSERT INTO games (game_id, mode, platform, start_year, end_year, winner, winner_model, winner_scs, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (game_id, mode, platform, 1901, final_year, winner_power, winner_model, winner_scs, status))

    # Load scoring report for all metrics
    scoring_report = game_dir / "SCORING_REPORT.md"
    scoring_data = parse_scoring_report(scoring_report)
    rankings = scoring_data["rankings"] if scoring_data else {}
    press_scores = scoring_data["press_scores"] if scoring_data else {}

    # Insert models
    for power, model_id in assignments.items():
        tier = classify_tier(model_id)
        provider = classify_provider(model_id)
        rank = rankings.get(power)
        final_sc = final_scs.get(power, 0)

        press_data = press_scores.get(power, {})

        cur.execute("""
            INSERT INTO models (game_id, power, model_id, provider, tier, final_rank, final_scs,
                                deception_score, truthfulness_score, cooperation_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (game_id, power, model_id, provider, tier, rank, final_sc,
              press_data.get("deception"), press_data.get("truthfulness"), press_data.get("cooperation")))

    # Insert supply center counts
    sc_inserts = []
    for year_str, scs in sc_counts.items():
        year = int(year_str)
        for power, count in scs.items():
            sc_inserts.append((game_id, year, power, count))

    execute_batch(cur, """
        INSERT INTO supply_centers (game_id, year, power, sc_count)
        VALUES (%s, %s, %s, %s)
    """, sc_inserts)

    # Insert power scores
    if scoring_data and scoring_data["power_scores"]:
        power_score_inserts = []
        for power, scores in scoring_data["power_scores"].items():
            power_score_inserts.append((
                game_id, power,
                scores.get("total_score"), scores.get("performance_score"), scores.get("precision_score"),
                scores.get("total_invalid_orders", 0), scores.get("total_bounces", 0),
                scores.get("total_supports_own", 0), scores.get("total_supports_other", 0),
                scores.get("total_supports_hold", 0), scores.get("total_supports_attack", 0),
                scores.get("total_convoys", 0)
            ))

        execute_batch(cur, """
            INSERT INTO power_scores (game_id, power, total_score, performance_score, precision_score,
                                      total_invalid_orders, total_bounces, total_supports_own, total_supports_other,
                                      total_supports_hold, total_supports_attack, total_convoys)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, power_score_inserts)

    # Insert turn metrics
    if scoring_data and scoring_data["turn_metrics"]:
        turn_metric_inserts = []
        for metric in scoring_data["turn_metrics"]:
            turn_metric_inserts.append((
                game_id, metric["year"], metric["season"], metric["power"],
                metric["invalid_orders"], metric["bounces"],
                metric["supports_own"], metric["supports_other"], 0, 0, metric["convoys"]
            ))

        execute_batch(cur, """
            INSERT INTO turn_metrics (game_id, year, season, power, invalid_orders, bounces,
                                      supports_own, supports_other, supports_hold, supports_attack, convoys)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id, year, season, power) DO NOTHING
        """, turn_metric_inserts)

    # Load press messages (if press game)
    if mode == "press":
        press_dir = game_dir / "press"
        if press_dir.exists():
            press_inserts = []
            for press_file in press_dir.glob("*.txt"):
                # Parse filename: sender_receiver.txt
                parts = press_file.stem.split("_")
                if len(parts) >= 2:
                    sender = parts[0].replace("-", " ").title()
                    recipient = parts[1].replace("-", " ").title()

                    with open(press_file) as f:
                        content = f.read()

                    # Parse messages (format: "Spring 1901: message")
                    for line in content.split("\n"):
                        if ":" in line:
                            season_year, message = line.split(":", 1)
                            season_year = season_year.strip()
                            message = message.strip()

                            if season_year and message:
                                # Parse season/year
                                match = re.match(r"(Spring|Fall|Winter) (\d+)", season_year)
                                if match:
                                    season = match.group(1).lower()
                                    year = int(match.group(2))
                                    press_inserts.append((game_id, year, season, sender, recipient, message))

            if press_inserts:
                execute_batch(cur, """
                    INSERT INTO press_messages (game_id, year, season, sender, recipient, message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, press_inserts)

    conn.commit()

    metrics_count = len(scoring_data["turn_metrics"]) if scoring_data else 0
    power_scores_count = len(scoring_data["power_scores"]) if scoring_data else 0

    print(f"    ✓ Loaded: {len(assignments)} models, {len(sc_inserts)} SC records, "
          f"{len(press_inserts) if mode == 'press' else 0} press messages, "
          f"{power_scores_count} power scores, {metrics_count} turn metrics")

def main():
    parser = argparse.ArgumentParser(description="Load Diplomacy games into Postgres")
    parser.add_argument("--games-dir", type=str, required=True, help="Path to games directory")
    parser.add_argument("--db-url", type=str, required=True, help="Postgres connection URL")
    args = parser.parse_args()

    games_dir = Path(args.games_dir)
    if not games_dir.exists():
        print(f"ERROR: Games directory not found: {games_dir}")
        return

    # Connect to database
    conn = psycopg2.connect(args.db_url)
    db_name = args.db_url.split('/')[-1]
    print(f"Connected to database: {db_name}")

    # Load games
    games = sorted([d for d in games_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"\nFound {len(games)} games\n")

    loaded = 0
    skipped = 0

    for game_dir in games:
        if should_exclude_game(game_dir):
            skipped += 1
            continue

        try:
            load_game(conn, game_dir)
            loaded += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            conn.rollback()
            skipped += 1

    conn.close()
    print(f"\n✓ Loaded {loaded} games, skipped {skipped}")

if __name__ == "__main__":
    main()
