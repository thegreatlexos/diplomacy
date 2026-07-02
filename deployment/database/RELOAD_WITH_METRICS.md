# Reload Database with Enhanced Metrics

The schema has been updated with three new tables:
- **turn_metrics** - Per-turn tactical stats (invalid orders, bounces, supports breakdown)
- **press_metrics** - Per-turn press quality scores (truthfulness, cooperation, deception)
- **power_scores** - Aggregate scores per power (total score, performance, precision, all tactical totals)

## Step 1: Drop and Recreate Database

```bash
# On your local machine (or VPS)
psql -U diplomacy -d diplomacy_ai

# Drop all tables
DROP TABLE IF EXISTS press_metrics CASCADE;
DROP TABLE IF EXISTS turn_metrics CASCADE;
DROP TABLE IF EXISTS power_scores CASCADE;
DROP TABLE IF EXISTS press_messages CASCADE;
DROP TABLE IF EXISTS supply_centers CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS turns CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS games CASCADE;

\q

# Recreate schema
cd /Users/alexandergroot/Documents/Personal/Repository/diplomacy/deployment/database
psql -U diplomacy -d diplomacy_ai -f schema.sql
```

## Step 2: Reload Games

```bash
# On local machine
cd /Users/alexandergroot/Documents/Personal/Repository/diplomacy/deployment/database

python3 load_games.py \
  --games-dir ../../games \
  --db-url "postgresql://diplomacy:your-password@localhost/diplomacy_ai"
```

You should see output like:
```
✓ Loaded: 7 models, 140 SC records, 245 press messages, 7 power scores, 280 turn metrics
```

## Step 3: Verify Data

```bash
psql -U diplomacy -d diplomacy_ai

-- Check power scores loaded
SELECT COUNT(*) FROM power_scores;
-- Should show ~175 (25 games × 7 powers)

-- Check turn metrics loaded
SELECT COUNT(*) FROM turn_metrics;
-- Should show thousands

-- Sample query: Top invalid order offenders
SELECT power, AVG(invalid_orders) as avg_invalid
FROM turn_metrics
WHERE invalid_orders > 0
GROUP BY power
ORDER BY avg_invalid DESC;

\q
```

## What's Next

Once data is reloaded, we'll add:
1. Backend API endpoints to serve these metrics
2. Frontend MetricsPanel component
3. Per-turn metrics display
4. Invalid order highlighting
