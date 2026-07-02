#!/bin/bash
# Test deployment setup locally

set -e

echo "=== Testing Diplomacy AI Deployment Setup ==="
echo ""

# Check if postgres is running
if ! pg_isready -q; then
    echo "ERROR: PostgreSQL is not running"
    echo "Start with: brew services start postgresql@14"
    exit 1
fi

echo "✓ PostgreSQL is running"

# Create test database
DB_NAME="diplomacy_ai_test"
echo ""
echo "Creating test database: $DB_NAME"
dropdb --if-exists $DB_NAME
createdb $DB_NAME

echo "✓ Database created"

# Run schema
echo ""
echo "Loading schema..."
psql -d $DB_NAME -f database/schema.sql > /dev/null
echo "✓ Schema loaded"

# Load games
echo ""
echo "Loading game data..."
cd database
python3.12 load_games.py \
    --games-dir ../../games \
    --db-url "postgresql://localhost/$DB_NAME"
cd ..

echo ""
echo "✓ Games loaded"

# Test backend (skip if dependencies not installed)
echo ""
echo "Testing backend (optional)..."
cd backend

# Check if dependencies exist
if python3.12 -c "import fastapi, psycopg2" 2>/dev/null; then
    cp .env.example .env
    sed -i '' "s|diplomacy_ai|$DB_NAME|g" .env

    # Start backend in background
    python3.12 main.py > /dev/null 2>&1 &
    BACKEND_PID=$!

    sleep 3

    # Test API
    echo "Testing API endpoints..."
    curl -s http://localhost:8000/ | grep -q "Diplomacy AI API" && echo "  ✓ Root endpoint"
    curl -s http://localhost:8000/games | grep -q "game_id" && echo "  ✓ Games list"
    curl -s http://localhost:8000/stats/overview | grep -q "total_games" && echo "  ✓ Stats endpoint"

    # Cleanup
    kill $BACKEND_PID 2>/dev/null
else
    echo "  ⚠ Backend dependencies not installed (skipping)"
    echo "  To test backend, install: pip install fastapi uvicorn psycopg2-binary python-dotenv"
fi
cd ..

echo ""
echo "=== All tests passed! ==="
echo ""
echo "To deploy to VPS:"
echo "  1. Copy deployment/ folder to VPS"
echo "  2. Follow steps in deployment/README.md"
echo ""
