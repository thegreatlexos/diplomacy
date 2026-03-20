"""
FastAPI backend for Diplomacy Game Viewer.
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Diplomacy Game Viewer API")

# CORS for Svelte dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to games folder (relative to where server is run)
GAMES_DIR = Path(__file__).parent.parent / "games"


class GameInfo(BaseModel):
    id: str
    platform: Optional[str] = None
    model_assignments: Optional[Dict[str, str]] = None


class Phase(BaseModel):
    year: int
    season: str
    has_orders: bool
    has_summary: bool
    has_visualization: bool
    visualization_path: Optional[str] = None


class Order(BaseModel):
    unit: str
    action: str
    destination: Optional[str] = None
    supporting: Optional[str] = None
    power: Optional[str] = None


class PressThread(BaseModel):
    id: str
    powers: List[str]
    message_count: int
    last_message_preview: str


class PressMessage(BaseModel):
    phase: str
    round: int
    sender: str
    content: str


@app.get("/api/games", response_model=List[GameInfo])
def list_games():
    """List all available games."""
    games = []
    if not GAMES_DIR.exists():
        return games

    for game_dir in sorted(GAMES_DIR.iterdir()):
        if not game_dir.is_dir():
            continue

        game_info = {"id": game_dir.name}

        # Load model assignments if available
        assignments_file = game_dir / "model_assignments.json"
        if assignments_file.exists():
            with open(assignments_file) as f:
                data = json.load(f)
                game_info["platform"] = data.get("platform")
                game_info["model_assignments"] = data.get("assignments", {})

        games.append(GameInfo(**game_info))

    return games


@app.get("/api/games/{game_id}/phases", response_model=List[Phase])
def list_phases(game_id: str):
    """List all phases for a game."""
    game_dir = GAMES_DIR / game_id
    if not game_dir.exists():
        raise HTTPException(status_code=404, detail="Game not found")

    phases = []
    seen = set()

    # Scan orders folder for phases
    orders_dir = game_dir / "orders"
    if orders_dir.exists():
        for order_file in sorted(orders_dir.glob("*.yaml")):
            # Parse filename: 1901_01_spring.yaml or 1901_01_retreat_spring.yaml
            match = re.match(r"(\d+)_\d+_(?:retreat_)?(\w+)\.yaml", order_file.name)
            if match:
                year = int(match.group(1))
                season = match.group(2)
                key = f"{year}_{season}"

                if key not in seen:
                    seen.add(key)

                    # Find visualization
                    viz_path = None
                    viz_dir = game_dir / "visualizations"
                    if viz_dir.exists():
                        # Look for _orders visualization first (shows arrows)
                        for viz in viz_dir.glob(f"*_{year}_{season}_*_orders.png"):
                            viz_path = f"/api/games/{game_id}/visualization/{viz.name}"
                            break
                        # Fallback to _after visualization
                        if not viz_path:
                            for viz in viz_dir.glob(f"*_{year}_{season}_*_after.png"):
                                viz_path = f"/api/games/{game_id}/visualization/{viz.name}"
                                break

                    phases.append(Phase(
                        year=year,
                        season=season,
                        has_orders=True,
                        has_summary=(game_dir / "summaries" / f"{year}_{season}_summary.md").exists(),
                        has_visualization=viz_path is not None,
                        visualization_path=viz_path
                    ))

    # Sort by year and season order
    season_order = {"spring": 0, "fall": 1, "winter": 2}
    phases.sort(key=lambda p: (p.year, season_order.get(p.season, 3)))

    return phases


@app.get("/api/games/{game_id}/visualization/{filename}")
def get_visualization(game_id: str, filename: str):
    """Serve a visualization image."""
    file_path = GAMES_DIR / game_id / "visualizations" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Visualization not found")
    return FileResponse(file_path, media_type="image/png")


@app.get("/api/games/{game_id}/orders/{year}/{season}", response_model=List[Order])
def get_orders(game_id: str, year: int, season: str):
    """Get orders for a specific phase."""
    game_dir = GAMES_DIR / game_id
    orders_dir = game_dir / "orders"

    # Find matching order file
    order_file = None
    for f in orders_dir.glob(f"{year}_*_{season}.yaml"):
        if "retreat" not in f.name:
            order_file = f
            break

    if not order_file or not order_file.exists():
        return []

    with open(order_file) as f:
        data = yaml.safe_load(f)

    orders = []
    for order in data.get("orders", []):
        orders.append(Order(
            unit=order.get("unit", ""),
            action=order.get("action", ""),
            destination=order.get("destination"),
            supporting=order.get("supporting"),
            power=_get_power_from_unit(order.get("unit", ""))
        ))

    return orders


def _get_power_from_unit(unit: str) -> str:
    """Infer power from unit starting location."""
    # Map starting locations to powers
    location_map = {
        "Edi": "England", "Lvp": "England", "Lon": "England",
        "Bre": "France", "Par": "France", "Mar": "France",
        "Ber": "Germany", "Mun": "Germany", "Kie": "Germany",
        "Ven": "Italy", "Rom": "Italy", "Nap": "Italy",
        "Vie": "Austria", "Bud": "Austria", "Tri": "Austria",
        "Mos": "Russia", "War": "Russia", "StP": "Russia", "Sev": "Russia",
        "Con": "Turkey", "Ank": "Turkey", "Smy": "Turkey",
    }

    # Extract location from unit string (e.g., "F Edi" -> "Edi")
    parts = unit.split()
    if len(parts) >= 2:
        loc = parts[1].split("/")[0]  # Handle StP/sc
        return location_map.get(loc, "Unknown")
    return "Unknown"


@app.get("/api/games/{game_id}/press/threads", response_model=List[PressThread])
def list_press_threads(game_id: str):
    """List all press threads for a game."""
    game_dir = GAMES_DIR / game_id
    press_dir = game_dir / "press"

    if not press_dir.exists():
        return []

    threads = []
    for press_file in sorted(press_dir.glob("*.txt")):
        # Parse filename: england_france.txt
        powers = press_file.stem.replace("-", "_").split("_")
        powers = [p.title() for p in powers]

        # Count messages and get preview
        with open(press_file) as f:
            content = f.read()

        messages = re.findall(r"\[([^\]]+)\]\s*\n([^:]+):\s*(.+?)(?=\n\[|\Z)", content, re.DOTALL)
        message_count = len(messages)

        last_preview = ""
        if messages:
            last_preview = messages[-1][2][:100].strip() + "..." if len(messages[-1][2]) > 100 else messages[-1][2].strip()

        threads.append(PressThread(
            id=press_file.stem,
            powers=powers,
            message_count=message_count,
            last_message_preview=last_preview
        ))

    return threads


@app.get("/api/games/{game_id}/press/{thread_id}", response_model=List[PressMessage])
def get_press_thread(game_id: str, thread_id: str):
    """Get all messages in a press thread."""
    game_dir = GAMES_DIR / game_id
    press_file = game_dir / "press" / f"{thread_id}.txt"

    if not press_file.exists():
        raise HTTPException(status_code=404, detail="Press thread not found")

    with open(press_file) as f:
        content = f.read()

    messages = []
    # Pattern: [Season Year - Press Round N]\nSender: Message
    pattern = r"\[([^\]]+)\]\s*\n([^:]+):\s*(.+?)(?=\n\[|\Z)"

    for match in re.finditer(pattern, content, re.DOTALL):
        phase_info = match.group(1)
        sender = match.group(2).strip()
        msg_content = match.group(3).strip()

        # Parse round from phase info
        round_match = re.search(r"Round (\d+)", phase_info)
        round_num = int(round_match.group(1)) if round_match else 1

        messages.append(PressMessage(
            phase=phase_info,
            round=round_num,
            sender=sender,
            content=msg_content
        ))

    return messages


@app.get("/api/games/{game_id}/summary/{year}/{season}")
def get_summary(game_id: str, year: int, season: str):
    """Get summary for a specific phase."""
    game_dir = GAMES_DIR / game_id
    summary_file = game_dir / "summaries" / f"{year}_{season}_summary.md"

    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Summary not found")

    with open(summary_file) as f:
        content = f.read()

    return {"content": content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
