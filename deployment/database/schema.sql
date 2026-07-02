-- Diplomacy AI Database Schema

CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) UNIQUE NOT NULL,
    mode VARCHAR(20) NOT NULL, -- 'gunboat' or 'press'
    platform VARCHAR(50) NOT NULL, -- 'bedrock' or 'openrouter'
    start_year INT DEFAULT 1901,
    end_year INT,
    winner VARCHAR(50),
    winner_model VARCHAR(100),
    winner_scs INT,
    status VARCHAR(20), -- 'solo', 'stalemate', 'incomplete'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    power VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50),
    tier VARCHAR(20), -- 'budget', 'mid', 'premium'
    final_rank INT,
    final_scs INT,
    avg_invalid_orders FLOAT,
    deception_score FLOAT,
    truthfulness_score FLOAT,
    cooperation_score FLOAT,
    UNIQUE(game_id, power)
);

CREATE TABLE IF NOT EXISTS turns (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL, -- 'spring', 'fall', 'winter'
    phase INT NOT NULL, -- 0=initial, 1=orders, 2=resolution, 3=after
    visualization_path TEXT,
    UNIQUE(game_id, year, season, phase)
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL,
    power VARCHAR(50) NOT NULL,
    order_text TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE,
    order_type VARCHAR(20), -- 'hold', 'move', 'support', 'convoy', 'build', 'disband', 'retreat'
    succeeded BOOLEAN, -- whether the order succeeded (move/support worked)
    bounced BOOLEAN DEFAULT FALSE -- whether a move bounced
);

CREATE TABLE IF NOT EXISTS press_messages (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL,
    sender VARCHAR(50) NOT NULL,
    recipient VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supply_centers (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    power VARCHAR(50) NOT NULL,
    sc_count INT NOT NULL
);

-- Tactical metrics per turn
CREATE TABLE IF NOT EXISTS turn_metrics (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL,
    power VARCHAR(50) NOT NULL,
    invalid_orders INT DEFAULT 0,
    bounces INT DEFAULT 0,
    supports_own INT DEFAULT 0,
    supports_other INT DEFAULT 0,
    supports_hold INT DEFAULT 0,
    supports_attack INT DEFAULT 0,
    convoys INT DEFAULT 0,
    successful_moves INT DEFAULT 0,
    UNIQUE(game_id, year, season, power)
);

-- Press evaluation metrics per turn
CREATE TABLE IF NOT EXISTS press_metrics (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL,
    power VARCHAR(50) NOT NULL,
    truthfulness_score FLOAT,
    cooperation_score FLOAT,
    deception_score FLOAT,
    UNIQUE(game_id, year, season, power)
);

-- Power performance scores (from SCORING_REPORT)
CREATE TABLE IF NOT EXISTS power_scores (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    power VARCHAR(50) NOT NULL,
    total_score INT,
    performance_score INT,
    precision_score INT,
    total_invalid_orders INT,
    total_bounces INT,
    total_supports_own INT,
    total_supports_other INT,
    total_supports_hold INT,
    total_supports_attack INT,
    total_convoys INT,
    UNIQUE(game_id, power)
);

-- Game events (key moments for timeline)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id) ON DELETE CASCADE,
    year INT NOT NULL,
    season VARCHAR(10) NOT NULL,
    event_type VARCHAR(30) NOT NULL, -- 'game_start', 'territory_shift', 'elimination', 'milestone', 'victory'
    power VARCHAR(50),
    description TEXT NOT NULL,
    metadata JSONB,
    severity VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'critical'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_games_game_id ON games(game_id);
CREATE INDEX idx_models_game_id ON models(game_id);
CREATE INDEX idx_turns_game_id ON turns(game_id);
CREATE INDEX idx_orders_game_id ON orders(game_id);
CREATE INDEX idx_orders_year_season ON orders(game_id, year, season);
CREATE INDEX idx_press_game_id ON press_messages(game_id);
CREATE INDEX idx_sc_game_id ON supply_centers(game_id);
CREATE INDEX idx_sc_year ON supply_centers(year);
CREATE INDEX idx_turn_metrics_game ON turn_metrics(game_id);
CREATE INDEX idx_press_metrics_game ON press_metrics(game_id);
CREATE INDEX idx_power_scores_game ON power_scores(game_id);
CREATE INDEX idx_events_game ON events(game_id);
CREATE INDEX idx_events_year_season ON events(game_id, year, season);
