"""
FastAPI backend for Diplomacy AI platform.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Diplomacy AI API", version="1.0.0")

# Games directory
GAMES_DIR = Path(__file__).parent.parent.parent / "games"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/diplomacy_ai")

def get_db():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Models
class Game(BaseModel):
    id: int
    game_id: str
    mode: str
    platform: str
    start_year: int
    end_year: int
    winner: str
    winner_model: str
    winner_scs: int
    status: str

class Model(BaseModel):
    id: int
    game_id: str
    power: str
    model_id: str
    provider: str
    tier: str
    final_rank: Optional[int]
    final_scs: int
    deception_score: Optional[float]
    truthfulness_score: Optional[float]
    cooperation_score: Optional[float]

class PressMessage(BaseModel):
    id: int
    game_id: str
    year: int
    season: str
    sender: str
    recipient: str
    message: str

class SupplyCenterData(BaseModel):
    year: int
    power: str
    sc_count: int

# Routes
@app.get("/")
def read_root():
    return {"message": "Diplomacy AI API", "version": "1.0.0"}

@app.get("/games", response_model=List[Game])
def list_games(mode: Optional[str] = None, platform: Optional[str] = None):
    """List all games with optional filters."""
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM games WHERE 1=1"
    params = []

    if mode:
        query += " AND mode = %s"
        params.append(mode)

    if platform:
        query += " AND platform = %s"
        params.append(platform)

    query += " ORDER BY end_year DESC, game_id DESC"

    cur.execute(query, params)
    games = cur.fetchall()
    conn.close()

    return games

@app.get("/games/{game_id}", response_model=Game)
def get_game(game_id: str):
    """Get game details."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM games WHERE game_id = %s", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return game

@app.get("/games/{game_id}/models", response_model=List[Model])
def get_game_models(game_id: str):
    """Get models for a game."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM models WHERE game_id = %s ORDER BY final_rank", (game_id,))
    models = cur.fetchall()
    conn.close()

    return models

@app.get("/games/{game_id}/supply-centers", response_model=List[SupplyCenterData])
def get_supply_centers(game_id: str):
    """Get supply center data for a game."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT year, power, sc_count
        FROM supply_centers
        WHERE game_id = %s
        ORDER BY year, power
    """, (game_id,))
    sc_data = cur.fetchall()
    conn.close()

    return sc_data

@app.get("/games/{game_id}/press", response_model=List[PressMessage])
def get_press_messages(game_id: str):
    """Get press messages for a game."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM press_messages
        WHERE game_id = %s
        ORDER BY year, season, id
    """, (game_id,))
    messages = cur.fetchall()
    conn.close()

    return messages

@app.get("/stats/overview")
def get_overview_stats():
    """Get overall platform statistics."""
    conn = get_db()
    cur = conn.cursor()

    # Total games
    cur.execute("SELECT COUNT(*) as count FROM games")
    total_games = cur.fetchone()["count"]

    # Total providers
    cur.execute("SELECT COUNT(DISTINCT provider) as count FROM models")
    total_providers = cur.fetchone()["count"]

    # Total years
    cur.execute("SELECT SUM(end_year - start_year + 1) as total FROM games")
    total_years = cur.fetchone()["total"]

    # Total orders (approximate)
    cur.execute("SELECT COUNT(*) as count FROM orders")
    total_orders = cur.fetchone()["count"]

    conn.close()

    return {
        "total_games": total_games,
        "total_providers": total_providers,
        "total_years": total_years,
        "total_orders": total_orders
    }

@app.get("/stats/tier-performance")
def get_tier_performance():
    """Get performance by model tier."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            tier,
            COUNT(*) as games,
            AVG(final_rank) as avg_rank,
            SUM(CASE WHEN final_rank = 1 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as win_rate
        FROM models
        WHERE tier IN ('budget', 'mid', 'premium')
        GROUP BY tier
        ORDER BY avg_rank
    """)
    stats = cur.fetchall()
    conn.close()

    return stats

@app.get("/games/{game_id}/visualizations/{filename}")
def get_visualization(game_id: str, filename: str):
    """Get visualization image for a game."""
    file_path = GAMES_DIR / game_id / "visualizations" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Visualization not found")

    return FileResponse(file_path)

@app.get("/games/{game_id}/orders/{filename}")
def get_orders_file(game_id: str, filename: str):
    """Get orders file for a game (YAML or JSON)."""
    # Try both .yaml and .json extensions
    yaml_path = GAMES_DIR / game_id / "orders" / filename.replace('.json', '.yaml')
    json_path = GAMES_DIR / game_id / "orders" / filename

    if yaml_path.exists():
        return FileResponse(yaml_path)
    elif json_path.exists():
        return FileResponse(json_path)
    else:
        raise HTTPException(status_code=404, detail="Orders file not found")

@app.get("/games/{game_id}/press/{filename}")
def get_press_file(game_id: str, filename: str):
    """Get press file for a game."""
    file_path = GAMES_DIR / game_id / "press" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Press file not found")

    return FileResponse(file_path)

@app.get("/games/{game_id}/summaries/{filename}")
def get_summary_file(game_id: str, filename: str):
    """Get summary file for a game."""
    file_path = GAMES_DIR / game_id / "summaries" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Summary file not found")

    return FileResponse(file_path)

@app.get("/games/{game_id}/scoring-report")
def get_scoring_report(game_id: str):
    """Get scoring report for a game."""
    file_path = GAMES_DIR / game_id / "SCORING_REPORT.md"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Scoring report not found")

    return FileResponse(file_path)

@app.get("/games/{game_id}/orders")
def get_game_orders(game_id: str, year: int = None, season: str = None):
    """Get orders for a game, optionally filtered by year/season."""
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM orders WHERE game_id = %s"
    params = [game_id]

    if year:
        query += " AND year = %s"
        params.append(year)
    if season:
        query += " AND season = %s"
        params.append(season)

    query += " ORDER BY year, season, power"

    cur.execute(query, tuple(params))
    orders = cur.fetchall()
    conn.close()

    return orders

@app.get("/games/{game_id}/power-scores")
def get_power_scores(game_id: str):
    """Get aggregate power scores for a game."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM power_scores
        WHERE game_id = %s
        ORDER BY total_score DESC
    """, (game_id,))
    scores = cur.fetchall()
    conn.close()

    return scores

@app.get("/games/{game_id}/turn-metrics")
def get_turn_metrics(game_id: str, year: int = None, season: str = None):
    """Get per-turn tactical metrics, optionally filtered by year/season."""
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM turn_metrics WHERE game_id = %s"
    params = [game_id]

    if year:
        query += " AND year = %s"
        params.append(year)
    if season:
        query += " AND season = %s"
        params.append(season)

    query += " ORDER BY year, season, power"

    cur.execute(query, tuple(params))
    metrics = cur.fetchall()
    conn.close()

    return metrics

@app.get("/games/{game_id}/press-metrics")
def get_press_metrics(game_id: str, year: int = None, season: str = None):
    """Get per-turn press quality metrics, optionally filtered by year/season."""
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM press_metrics WHERE game_id = %s"
    params = [game_id]

    if year:
        query += " AND year = %s"
        params.append(year)
    if season:
        query += " AND season = %s"
        params.append(season)

    query += " ORDER BY year, season, power"

    cur.execute(query, tuple(params))
    metrics = cur.fetchall()
    conn.close()

    return metrics

@app.get("/games/{game_id}/files")
def list_game_files(game_id: str):
    """List available files for a game."""
    game_dir = GAMES_DIR / game_id

    if not game_dir.exists():
        raise HTTPException(status_code=404, detail="Game not found")

    visualizations = []
    viz_dir = game_dir / "visualizations"
    if viz_dir.exists():
        visualizations = sorted([f.name for f in viz_dir.glob("*.png")])

    orders = []
    orders_dir = game_dir / "orders"
    if orders_dir.exists():
        orders = sorted([f.name for f in orders_dir.glob("*.json")])

    press = []
    press_dir = game_dir / "press"
    if press_dir.exists():
        press = sorted([f.name for f in press_dir.glob("*.txt")])

    summaries = []
    summaries_dir = game_dir / "summaries"
    if summaries_dir.exists():
        summaries = sorted([f.name for f in summaries_dir.glob("*.md")])

    return {
        "visualizations": visualizations,
        "orders": orders,
        "press": press,
        "summaries": summaries
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
