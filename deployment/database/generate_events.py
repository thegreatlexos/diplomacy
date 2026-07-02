#!/usr/bin/env python3
"""
Generate game events for timeline feature.

Detects key moments:
- Game start
- Territory shifts (gain/loss of 3+ SCs in one year)
- Eliminations (power reduced to 0 SCs)
- Milestones (reaching 10, 15 SCs)
- Victory (game end)
"""

import sys
sys.path.insert(0, '/Users/alexandergroot/.local/lib/python3.12/site-packages')

import argparse
import psycopg2
from psycopg2.extras import execute_batch
import json


def detect_events(conn, game_id):
    """Detect all events for a game."""
    cur = conn.cursor()

    # Get game info
    cur.execute("SELECT * FROM games WHERE game_id = %s", (game_id,))
    game = cur.fetchone()
    if not game:
        return []

    game_dict = dict(game)

    # Get supply center history
    cur.execute("""
        SELECT year, power, sc_count
        FROM supply_centers
        WHERE game_id = %s
        ORDER BY year, power
    """, (game_id,))
    sc_data = cur.fetchall()

    # Organize by year and power
    sc_by_year = {}
    for row in sc_data:
        year, power, count = row['year'], row['power'], row['sc_count']
        if year not in sc_by_year:
            sc_by_year[year] = {}
        sc_by_year[year][power] = count

    events = []

    # Event 1: Game Start
    events.append({
        'year': game_dict['start_year'],
        'season': 'spring',
        'event_type': 'game_start',
        'power': None,
        'description': f"Game begins: {game_dict['mode']} mode with 7 AI powers",
        'metadata': json.dumps({'mode': game_dict['mode']}),
        'severity': 'normal'
    })

    # Track previous year for comparison
    years = sorted(sc_by_year.keys())
    prev_year_scs = {}
    eliminated_powers = set()
    milestone_10_reached = set()
    milestone_15_reached = set()

    for year in years:
        current_scs = sc_by_year[year]

        # Detect territory shifts, eliminations, milestones
        for power, sc_count in current_scs.items():
            prev_count = prev_year_scs.get(power, current_scs[power])  # Use current if first year

            # Event: Elimination
            if sc_count == 0 and prev_count > 0 and power not in eliminated_powers:
                eliminated_powers.add(power)
                events.append({
                    'year': year,
                    'season': 'fall',
                    'event_type': 'elimination',
                    'power': power,
                    'description': f"{power} eliminated (lost all {prev_count} supply centers)",
                    'metadata': json.dumps({'prev_scs': prev_count}),
                    'severity': 'high'
                })

            # Event: Territory Shift (gain of 3+ SCs)
            elif sc_count - prev_count >= 3 and year > game_dict['start_year']:
                events.append({
                    'year': year,
                    'season': 'fall',
                    'event_type': 'territory_shift',
                    'power': power,
                    'description': f"{power} surges forward (+{sc_count - prev_count} SCs → {sc_count} total)",
                    'metadata': json.dumps({'gain': sc_count - prev_count, 'new_total': sc_count}),
                    'severity': 'normal'
                })

            # Event: Territory Shift (loss of 3+ SCs)
            elif prev_count - sc_count >= 3 and sc_count > 0:
                events.append({
                    'year': year,
                    'season': 'fall',
                    'event_type': 'territory_shift',
                    'power': power,
                    'description': f"{power} under pressure (-{prev_count - sc_count} SCs → {sc_count} total)",
                    'metadata': json.dumps({'loss': prev_count - sc_count, 'new_total': sc_count}),
                    'severity': 'normal'
                })

            # Event: Milestone - 10 SCs
            if sc_count >= 10 and prev_count < 10 and power not in milestone_10_reached:
                milestone_10_reached.add(power)
                events.append({
                    'year': year,
                    'season': 'fall',
                    'event_type': 'milestone',
                    'power': power,
                    'description': f"{power} reaches 10 supply centers",
                    'metadata': json.dumps({'milestone': 10, 'total_scs': sc_count}),
                    'severity': 'high'
                })

            # Event: Milestone - 15 SCs
            if sc_count >= 15 and prev_count < 15 and power not in milestone_15_reached:
                milestone_15_reached.add(power)
                events.append({
                    'year': year,
                    'season': 'fall',
                    'event_type': 'milestone',
                    'power': power,
                    'description': f"{power} reaches 15 supply centers - approaching victory",
                    'metadata': json.dumps({'milestone': 15, 'total_scs': sc_count}),
                    'severity': 'critical'
                })

        prev_year_scs = current_scs.copy()

    # Event: Victory
    events.append({
        'year': game_dict['end_year'],
        'season': 'fall',
        'event_type': 'victory',
        'power': game_dict['winner'],
        'description': f"{game_dict['winner']} wins with {game_dict['winner_scs']} supply centers ({game_dict['status']})",
        'metadata': json.dumps({
            'status': game_dict['status'],
            'final_scs': game_dict['winner_scs']
        }),
        'severity': 'critical'
    })

    return events


def load_events_for_game(conn, game_id):
    """Generate and load events for a single game."""
    cur = conn.cursor()

    # Check if events already exist
    cur.execute("SELECT COUNT(*) as count FROM events WHERE game_id = %s", (game_id,))
    existing_count = cur.fetchone()['count']

    if existing_count > 0:
        print(f"  SKIP: {game_id} (already has {existing_count} events)")
        return 0

    # Detect events
    events = detect_events(conn, game_id)

    if not events:
        print(f"  SKIP: {game_id} (no events detected)")
        return 0

    # Insert events
    event_inserts = []
    for event in events:
        event_inserts.append((
            game_id,
            event['year'],
            event['season'],
            event['event_type'],
            event['power'],
            event['description'],
            event['metadata'],
            event['severity']
        ))

    execute_batch(cur, """
        INSERT INTO events (game_id, year, season, event_type, power, description, metadata, severity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, event_inserts)

    conn.commit()
    print(f"  ✓ {game_id}: {len(events)} events")
    return len(events)


def main():
    parser = argparse.ArgumentParser(description="Generate game events for timeline")
    parser.add_argument("--db-url", type=str, required=True, help="Postgres connection URL")
    parser.add_argument("--game-id", type=str, help="Process single game (optional)")
    args = parser.parse_args()

    conn = psycopg2.connect(args.db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    print(f"Connected to database\n")

    if args.game_id:
        # Process single game
        total = load_events_for_game(conn, args.game_id)
        print(f"\n✓ Generated {total} events")
    else:
        # Process all games
        cur = conn.cursor()
        cur.execute("SELECT game_id FROM games ORDER BY game_id")
        games = [row['game_id'] for row in cur.fetchall()]

        print(f"Found {len(games)} games\n")

        total_events = 0
        for game_id in games:
            total_events += load_events_for_game(conn, game_id)

        print(f"\n✓ Generated {total_events} events across {len(games)} games")

    conn.close()


if __name__ == "__main__":
    main()
