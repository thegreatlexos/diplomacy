# Diplomacy Game Engine Documentation

## Overview

A complete Python implementation of the classic board game Diplomacy, featuring order resolution, game state management, and visualization capabilities. The engine accurately simulates games from YAML order files and generates visual representations of each phase.

## Architecture

### Core Components

#### 1. Game State (`diplomacy_game_engine/core/game_state.py`)

- **GameState**: Represents the complete game state at any point
  - Units on the board with positions and coasts
  - Supply center ownership
  - Current year and season
  - Dislodged units awaiting retreat
- **Unit**: Represents individual military units (Army/Fleet)
  - Power ownership
  - Location and optional coast specification
  - Unique ID generation
- **DislodgedUnit**: Tracks units that must retreat or disband

#### 2. Map System (`diplomacy_game_engine/core/map.py`)

- **Map**: The game board with provinces and adjacencies
  - 75 provinces (land, sea, coastal)
  - 34 supply centers
  - Adjacency graph with coast support
- **Province**: Individual territories
  - Type (land/sea/coastal)
  - Supply center status
  - Home center designation
  - Multi-coast support (Spain, St Petersburg, Bulgaria)
- **Power**: The seven great powers (England, France, Germany, Italy, Austria, Russia, Turkey)

#### 3. Orders (`diplomacy_game_engine/core/orders.py`)

- **MoveOrder**: Unit movement with optional convoy flag
- **SupportOrder**: Support for move or hold
- **ConvoyOrder**: Fleet convoying an army
- **HoldOrder**: Unit holds position
- **RetreatOrder**: Dislodged unit retreat
- **DisbandOrder**: Unit removal
- **BuildOrder**: New unit construction

#### 4. Resolver (`diplomacy_game_engine/core/resolver.py`)

- **MovementResolver**: Adjudicates movement phases
  - Move legality checking
  - Strength calculation with support
  - Support cutting rules
  - Head-to-head resolution
  - Convoy path validation (BFS algorithm)
  - Dislodgement detection
- **RetreatResolver**: Handles retreat phase
  - Valid retreat destination calculation
  - Conflict detection (multiple units to same location)
- **WinterResolver**: Processes builds and disbands
  - SC count vs unit count comparison
  - Build validation (home centers, unoccupied)
  - Automatic disband selection if needed

### Input/Output

#### YAML Order Loader (`diplomacy_game_engine/io/yaml_orders.py`)

- Parses structured YAML order files
- Auto-corrects common errors (case, abbreviations)
- Validates orders against game state
- Handles coast notation (e.g., "Spa/sc", "StP/nc")
- Case-insensitive province matching
- Supports all order types

**YAML Format Example:**

```yaml
phase: "Spring 1906"
orders:
  - unit: "F Spa/sc"
    action: "move"
    destination: "MAO"
  - unit: "A Lon"
    action: "move"
    destination: "Pic"
    via_convoy: true
  - unit: "F ENG"
    action: "convoy"
    convoying: "A Lon"
    destination: "Pic"
```

### Visualization

#### Visualizer (`diplomacy_game_engine/visualization/visualizer.py`)

- **MapVisualizer**: Creates visual representations
  - Base map image overlay (915×767 pixels)
  - Unit markers (circles for armies, triangles for fleets)
  - Supply center indicators
  - Territory control coloring
  - Order arrows with multiple styles:
    - **Black solid**: Successful moves
    - **Red solid**: Failed/bounced/illegal moves
    - **Black dotted**: Valid supports
    - **Red dotted**: Cut/dislodged supports
    - **Orange solid**: Retreats
  - Dislodged unit indicators (red circles)
  - Disband indicators (red X marks)
  - Convoy indicators (wavy lines)

### Simulation

#### Simulator (`diplomacy_game_engine/simulate_yaml.py`)

- Orchestrates complete game simulation
- Processes order files sequentially
- Generates visualizations for each phase:
  1. Before state
  2. Orders with results
  3. After state
  4. After retreats (if applicable)
- Saves game states as JSON
- Creates summary report

## Key Features

### 1. Accurate Diplomacy Rules

- Standard adjacency rules
- Support cutting (except self-attack)
- Head-to-head resolution
- Convoy validation with path checking
- Dislodgement and retreat mechanics
- SC ownership (only updates in Fall)
- Build/disband rules

### 2. Coast Handling

- Multi-coast provinces (Spain, St Petersburg, Bulgaria)
- Coast-specific adjacencies
- Coast notation in orders ("Spa/sc", "StP/nc")
- Automatic coast matching for fleets

### 3. Convoy System

- Path validation using BFS
- Checks for connected sea zones
- Validates fleet survival
- Supports multi-fleet convoy chains

### 4. Visualization Features

- Failed moves show red arrows
- Illegal moves show red arrows
- Cut supports show red
- Dislodged units show red circles
- Retreats show orange arrows
- Coast-specific unit positioning

### 5. Error Handling

- Auto-correction of common mistakes
- Case-insensitive parsing
- Detailed warning messages
- Graceful handling of missing units

## Usage

### Running a Simulation

```bash
cd games/example_game_001
source ../../venv/bin/activate
python3 ../../diplomacy_game_engine/simulate_yaml.py .
```

### Game Folder Structure

```
game_folder/
├── game_info.yaml          # Game metadata and order file list
├── orders/                 # YAML order files
│   ├── 1901_01_spring.yaml
│   ├── 1901_02_fall.yaml
│   └── ...
├── states/                 # Generated JSON game states
│   ├── 1901_01_after_spring.json
│   └── ...
└── visualizations/         # Generated PNG images
    ├── 1901_01_spring/
    │   ├── 01_before.png
    │   ├── 02_orders.png
    │   └── 03_after.png
    └── ...
```

### game_info.yaml Format

```yaml
name: "Example Game"
description: "A complete Diplomacy game"
initial_state: "states/1901_01_initial.json" # Optional
order_files:
  - "orders/1901_01_spring.yaml"
  - "orders/1901_02_fall.yaml"
  - "orders/1901_03_winter.yaml"
  # ... more phases
```

## Technical Details

### Adjacency System

- Bidirectional graph structure
- Coast-specific connections
- Efficient lookup with dictionaries
- Supports complex multi-coast scenarios

### Resolution Algorithm

1. **Identify Moves**: Parse and validate all move orders
2. **Build Convoy Routes**: Link convoying fleets to armies
3. **Calculate Strengths**: Base strength + valid supports
4. **Apply Support Cutting**: Check for attacks on supporting units
5. **Recalculate Strengths**: After support cuts
6. **Determine Outcomes**: Iterative resolution for head-to-head
7. **Apply Moves**: Update game state, identify dislodgements

### Convoy Path Validation

Uses Breadth-First Search (BFS) to verify:

- Fleets form connected path from origin to destination
- Path goes through sea zones with convoying fleets
- At least one fleet in path survives attacks

### Visualization Rendering

- Matplotlib-based rendering
- Absolute pixel coordinates (915×767)
- Multiple z-order layers for proper overlap
- Smart arrow offsetting to avoid unit overlap
- Configurable styles and colors

## Recent Enhancements

### Session Improvements

1. **Coast Parsing**: Case-insensitive, handles "Province/coast" notation
2. **Convoy Validation**: BFS path checking for valid routes
3. **Illegal Move Visualization**: Red arrows for invalid moves
4. **Dislodged Support Visualization**: Red arrows when supporting unit dislodged
5. **Map Adjacency**: Added Fin-Nwy connection

### Bug Fixes

- Fixed SC ownership (only updates in Fall, not Spring)
- Fixed unit matching with coast specifications
- Fixed retreat execution
- Fixed support cutting detection
- Fixed province name case sensitivity

## File Locations

### Core Engine

- `diplomacy_game_engine/core/` - Game logic
- `diplomacy_game_engine/io/` - Input/output handling
- `diplomacy_game_engine/visualization/` - Rendering
- `diplomacy_game_engine/assets/` - Map images and data

### Example Game

- `games/example_game_001/` - Complete 1901-1911 game
- `games/example_game_001/EU_Chill.txt` - Ground truth reference

## Testing

The engine has been validated against a complete real game (EU_Chill.txt) covering:

- 33 phases (11 years)
- 400+ orders
- All order types
- Complex scenarios (convoys, support cutting, dislodgements)
- Multi-coast moves

## Future Enhancements

Potential improvements:

- Interactive game play mode
- AI player integration
- Network play support
- Alternative map variants
- Detailed move analysis reports
- Animated phase transitions

## Dependencies

- Python 3.7+
- matplotlib (visualization)
- numpy (convoy path calculations)
- PyYAML (order file parsing)

## License & Credits

This engine implements the standard Diplomacy rules as designed by Allan B. Calhamer. The implementation focuses on accuracy, clarity, and extensibility.
