# LLM Diplomacy Capability Study - Experiment Plan

## Existing Data (2 Games Already Run)

### Game 1: `20251201_new_bedrock_mix_press_000`
- **Duration**: 20 years, ~$24 cost
- **Config**: 4 Haiku + 3 Sonnet (mixed)
- **Key Results**:

| Model | Power | Final SCs | Supports (Own+Attack) | Invalid Orders | Bounces |
|-------|-------|-----------|----------------------|----------------|---------|
| Sonnet 4.5 | Russia | 11 | 42 + 60 = 102 | 8 | 64 |
| Haiku 4.5 | France | 11 | 18 + 30 = 48 | 8 | 39 |
| Haiku 4.5 | England | 7 | 4 + 5 = 9 | 6 | 24 |
| Sonnet 4.5 | Turkey | 4 | 5 + 8 = 13 | 9 | 48 |
| Sonnet 4.5 | Germany | 0 | 7 + 14 = 21 | 4 | 42 |
| Haiku 4.5 | Austria | 0 | 4 + 3 = 7 | 2 | 29 |
| Haiku 4.5 | Italy | 0 | 1 + 2 = 3 | 6 | 20 |

**Key Insight**: Russia (Sonnet) dominated through **10x more support orders** than eliminated powers. Support usage correlates strongly with victory. Model tier alone doesn't guarantee success (Germany/Sonnet eliminated).

### Game 2: `20260312_latest_bedrock_models_press_000`
- **Duration**: 2 years (short test), minimal cost
- **Config**: 2 Opus 4.6 + 3 Sonnet 4.6 + 2 Haiku 4.5
- **Key Results**:

| Model | Power | Final SCs | Invalid Orders |
|-------|-------|-----------|----------------|
| Sonnet 4.6 | Germany | 5 | 0 |
| Sonnet 4.6 | Russia | 5 | 1 |
| Sonnet 4.6 | France | 5 | 1 |
| Opus 4.6 | England | 4 | 2 |
| Opus 4.6 | Turkey | 4 | 1 |
| Haiku 4.5 | Austria | 4 | 2 |
| Haiku 4.5 | Italy | 3 | 1 |

**Key Insight**: Only 2 years of data, but Opus 4.6 had **higher invalid order rate** than Sonnet 4.6 in this sample. Too short for conclusions.

### What We Already Know
1. **Support usage is critical** - winner used 10x more supports
2. **Invalid order rate ~2-5%** across all model tiers
3. **Zero convoys** in 20+ years - naval coordination is rare/hard
4. **Position matters** - France (Haiku) matched Russia (Sonnet) despite tier difference
5. **Model tier != victory** - Germany (Sonnet) was eliminated

### Gaps in Existing Data
- No homogeneous games (all same model) for clean comparison
- No gunboat games (press impact unknown)
- No OpenRouter/cross-provider data
- No degradation analysis (need per-year breakdown)
- Short game 2 not useful for most metrics

---

## Research Questions

1. **Territorial Expansion**: Can LLMs successfully expand territory over time?
2. **Order Validity**: What is the rate of valid vs invalid order generation by model tier?
3. **Complex Order Execution**: Can LLMs execute convoys, supports, and coordinated attacks?
4. **Press Quality**: How coherent and strategic is diplomatic communication?
5. **Press-Action Consistency**: Do LLMs follow through on diplomatic promises or betray?
6. **Degradation Over Time**: Does performance degrade as game context grows (years 10-15)?
7. **Cross-Provider Comparison**: How do different LLM providers compare head-to-head?

---

## Metrics We Can Measure (Per Turn)

### From Scoring System (`game_scorer.py`, `order_analyzer.py`)

| Metric | Source | Granularity |
|--------|--------|-------------|
| Supply Center count | `states/*.json` | Per power, per turn |
| SC growth/loss | Computed | Per power, per turn |
| Invalid orders | Summaries + order parsing | Per power, per turn |
| Convoy attempts | `orders/*.yaml` | Per power, per turn |
| Support own units | `orders/*.yaml` | Per power, per turn |
| Support other powers | `orders/*.yaml` | Per power, per turn |
| Support hold vs attack | `orders/*.yaml` | Per power, per turn |
| Bounced moves | Summaries | Per power, per turn |

### From Press Evaluation (`summarizer.py`)

| Metric | Source | Granularity |
|--------|--------|-------------|
| Truthfulness (0-10) | LLM summary | Per power, per turn |
| Cooperation (0-10) | LLM summary | Per power, per turn |
| Deception (0-10) | LLM summary | Per power, per turn |

**Note**: Truthfulness score directly measures press-action consistency. Low truthfulness = either intentional betrayal OR model failure to follow through.

### From Token Tracker (`token_tracker.py`)

| Metric | Source | Granularity |
|--------|--------|-------------|
| Input tokens | `token_usage.csv` | Per call |
| Output tokens | `token_usage.csv` | Per call |
| Cost USD | `token_usage.csv` | Per call |
| Tokens by call type | Report | Press, orders, summary |

---

## Cost Estimates

Based on existing game data (~11M input tokens, ~320K output tokens for 20-year game):

| Configuration | Est. Cost/Game (15 yr) | Est. Cost/Game (20 yr) |
|---------------|------------------------|------------------------|
| Bedrock: All Haiku 4.5 | ~$5 | ~$7 |
| Bedrock: All Sonnet 4.6 | ~$13 | ~$17 |
| Bedrock: All Opus 4.6 | ~$80 | ~$110 |
| Bedrock: Mix (2 Opus, 3 Sonnet, 2 Haiku) | ~$30 | ~$40 |
| OpenRouter: 7 Premium Providers | ~$15 | ~$20 |
| OpenRouter: Free tier only | $0 | $0 |

---

## Experiment Matrix

### Phase 1: Bedrock Homogeneous Baselines (PRIORITY)

**Goal**: Establish clean baselines per model tier (no mixing confounds)

| Game ID | Models | Press | Years | Est. Cost | Purpose |
|---------|--------|-------|-------|-----------|---------|
| `bedrock_haiku_press_001` | All Haiku 4.5 | Yes | 15 | ~$5 | Baseline: cheap model |
| `bedrock_sonnet_press_001` | All Sonnet 4.6 | Yes | 15 | ~$13 | Baseline: mid-tier |

**Why no Opus homogeneous?** At ~$80/game, cost is prohibitive. Existing mixed data shows Opus doesn't outperform Sonnet on invalid orders anyway.

**Data Points**:
- 15 years x 2 seasons x 7 powers = 210 order submissions per game
- Compare to existing mixed game data
- Clean model-tier comparison without position/opponent confounds

### Phase 2: Bedrock Gunboat Control (PRIORITY)

**Goal**: Isolate press vs no-press impact

| Game ID | Models | Press | Years | Est. Cost | Purpose |
|---------|--------|-------|-------|-----------|---------|
| `bedrock_sonnet_gunboat_001` | All Sonnet 4.6 | No | 15 | ~$8 | Control: no press |

**Data Points**:
- Compare to `bedrock_sonnet_press_001`
- Does press help or hurt order quality?
- Is degradation worse with accumulating press history?
- Isolate "press-action consistency" question (no press = no betrayal possible)

### Phase 3: Bedrock Mixed (ALREADY HAVE DATA)

**Status**: We have `20251201_new_bedrock_mix_press_000` (4 Haiku + 3 Sonnet, 20 years)

**Additional run needed?** One more with randomization to eliminate position bias:

| Game ID | Models | Press | Years | Est. Cost | Purpose |
|---------|--------|-------|-------|-----------|---------|
| `bedrock_mixed_press_randomized_001` | 2 Opus, 3 Sonnet, 2 Haiku | Yes | 15 | ~$30 | Position bias control |

Set `RANDOMIZE_ASSIGNMENTS=true` to shuffle model-to-power mapping.

### Phase 4: OpenRouter Provider Battle (PRIORITY)

**Goal**: Cross-provider comparison (within $10-20 budget)

| Game ID | Models | Press | Years | Est. Cost | Purpose |
|---------|--------|-------|-------|-----------|---------|
| `openrouter_battle_001` | 7 providers | Yes | 12 | ~$15 | Provider comparison |

**Model Assignments** (7 unique providers):
```
MODEL_ENGLAND=anthropic/claude-sonnet-4.5      # Anthropic
MODEL_FRANCE=openai/gpt-5                       # OpenAI
MODEL_GERMANY=google/gemini-2.5-pro             # Google
MODEL_ITALY=x-ai/grok-4                         # xAI
MODEL_AUSTRIA=mistralai/mistral-large           # Mistral
MODEL_RUSSIA=deepseek/deepseek-chat             # DeepSeek
MODEL_TURKEY=meta-llama/llama-4-maverick        # Meta
MODEL_SUMMARIZER=meta-llama/llama-3.3-70b-instruct:free
```

**Note**: Cap at 12 years to stay within $15-20 budget. Monitor cost during run.

### Phase 5: OpenRouter Free Tier (OPTIONAL - $0)

**Goal**: Bonus data at zero cost

| Game ID | Models | Press | Years | Est. Cost | Purpose |
|---------|--------|-------|-------|-----------|---------|
| `openrouter_free_001` | 7 free models | Yes | 15 | $0 | Free comparison |

---

## Total Estimated Costs (Revised)

| Phase | Games | Bedrock Cost | OpenRouter Cost | Priority |
|-------|-------|--------------|-----------------|----------|
| Phase 1 | 2 | ~$18 | - | HIGH |
| Phase 2 | 1 | ~$8 | - | HIGH |
| Phase 3 | 1 | ~$30 | - | MEDIUM |
| Phase 4 | 1 | - | ~$15 | HIGH |
| Phase 5 | 1 | - | $0 | LOW |
| **Total** | **6** | **~$56** | **~$15** | |

**Total new spend: ~$71** (down from $181 by leveraging existing data)

---

## Data Analysis Plan

### 1. Order Validity Analysis
- **Metric**: Invalid order rate (invalid orders / total orders)
- **Group by**: Model tier, year (for degradation), power
- **Visualization**: Line chart of invalid rate over years, bar chart by model

### 2. Complex Order Analysis
- **Metric**: Convoy attempts, support rates (own vs other)
- **Group by**: Model tier
- **Question**: Do higher-tier models attempt more complex coordination?

### 3. Territorial Performance
- **Metric**: SC count trajectory over time
- **Group by**: Model tier, individual model (in OpenRouter battle)
- **Visualization**: SC count line charts per power

### 4. Press-Action Consistency
- **Metric**: Truthfulness score distribution
- **Group by**: Model tier
- **Analysis**: Correlate low truthfulness with:
  - Successful betrayal (SC gain) → Intentional deception
  - SC loss or bounces → Model failure to execute promises

### 5. Degradation Analysis
- **Metric**: Invalid order rate, response quality over years
- **Focus**: Years 10-15 vs years 1-5
- **Visualization**: Rolling average of metrics over time

### 6. Provider Comparison (OpenRouter)
- **Metrics**: All above metrics per provider
- **Ranking**: Final SC count, order validity, press quality

---

## Run Commands

```bash
# Phase 1: Bedrock Homogeneous Baselines (update .env first)
python run_llm_game.py --game-id bedrock_haiku_press_001 --visualize
python run_llm_game.py --game-id bedrock_sonnet_press_001 --visualize

# Phase 2: Gunboat Control
python run_llm_game.py --game-id bedrock_sonnet_gunboat_001 --visualize --gun-boat

# Phase 3: Mixed with Randomization (set RANDOMIZE_ASSIGNMENTS=true)
python run_llm_game.py --game-id bedrock_mixed_press_randomized_001 --visualize

# Phase 4: OpenRouter Battle (update .env with OpenRouter config)
python run_llm_game.py --game-id openrouter_battle_001 --visualize

# Phase 5: Free Tier (optional)
python run_llm_game.py --game-id openrouter_free_001 --visualize
```

---

## .env Configurations Needed

### Bedrock All Haiku
```bash
MODEL_PLATFORM=bedrock
MODEL_ENGLAND=eu.anthropic.claude-haiku-4-5-20251001-v1:0
MODEL_FRANCE=eu.anthropic.claude-haiku-4-5-20251001-v1:0
# ... (all 7 powers = haiku)
MODEL_SUMMARIZER=eu.anthropic.claude-haiku-4-5-20251001-v1:0
```

### Bedrock All Sonnet
```bash
MODEL_PLATFORM=bedrock
MODEL_ENGLAND=eu.anthropic.claude-sonnet-4-6
# ... (all 7 powers = sonnet)
MODEL_SUMMARIZER=eu.anthropic.claude-haiku-4-5-20251001-v1:0
```

### Bedrock All Opus
```bash
MODEL_PLATFORM=bedrock
MODEL_ENGLAND=eu.anthropic.claude-opus-4-6-v1
# ... (all 7 powers = opus)
MODEL_SUMMARIZER=eu.anthropic.claude-haiku-4-5-20251001-v1:0
```

### OpenRouter Battle
```bash
MODEL_PLATFORM=openrouter
OPENROUTER_API_KEY=sk-or-...
MODEL_ENGLAND=anthropic/claude-sonnet-4.5
MODEL_FRANCE=openai/gpt-5
MODEL_GERMANY=google/gemini-2.5-pro
MODEL_ITALY=x-ai/grok-4
MODEL_AUSTRIA=mistralai/mistral-large
MODEL_RUSSIA=deepseek/deepseek-chat
MODEL_TURKEY=meta-llama/llama-4-maverick
MODEL_SUMMARIZER=meta-llama/llama-3.3-70b-instruct:free
```

---

## Minimum Viable Experiment (Budget-Constrained)

If you need to cut costs, prioritize:

1. **Must have**: `bedrock_sonnet_press_001` (baseline, $13) - clean single-model data
2. **Must have**: `bedrock_sonnet_gunboat_001` (control, $8) - press vs no-press comparison
3. **Must have**: `openrouter_battle_001` (provider comparison, $15) - cross-provider data
4. **Already have**: `20251201_new_bedrock_mix_press_000` - mixed model competition (free!)

**Minimum new spend**: ~$36 for 3 new games + 1 existing = 4 games with publishable data.

### What You Can Publish With Minimum Viable

| Research Question | Data Source |
|-------------------|-------------|
| Can LLMs win territory? | Existing mixed game + new Sonnet baseline |
| Valid order generation rate | All 4 games |
| Complex order execution (supports) | Existing game (detailed support data) |
| Press quality | Existing + Sonnet press game |
| Press-action consistency | Compare press vs gunboat games |
| Cross-provider comparison | OpenRouter battle |
| Degradation over time | Extract per-year from all 15+ year games |

---

## Output Artifacts Per Game

Each game produces:
- `model_assignments.json` - Which model played which power
- `orders/*.yaml` - All orders submitted
- `states/*.json` - Game state snapshots
- `press/*.md` - All diplomatic messages
- `summaries/*.md` - LLM-generated phase summaries with press scores
- `token_usage.csv` - Detailed token consumption
- `TOKEN_USAGE_REPORT.md` - Cost summary
- `SCORING_REPORT.md` - Performance and precision scores
- `visualizations/*.png` - Map images (if --visualize)

---

## Open Questions

1. Should we run duplicate games for statistical significance? (doubles cost)
2. Do you want to manually review press messages for qualitative analysis?
3. Should we add a metric for "betrayal success rate" (low truthfulness + SC gain)?
4. Want to track response latency per model?
5. Need to build per-year metrics extractor for degradation analysis (currently only game-level totals)

---

## Summary: Games to Run

| # | Game ID | Config | Est. Cost | Status |
|---|---------|--------|-----------|--------|
| 1 | `20251201_new_bedrock_mix_press_000` | 4 Haiku + 3 Sonnet, 20yr | $24 | DONE |
| 2 | `20260312_latest_bedrock_models_press_000` | 2 Opus + 3 Sonnet + 2 Haiku, 2yr | ~$2 | DONE (too short) |
| 3 | `bedrock_haiku_press_001` | All Haiku 4.5, 15yr | ~$5 | TODO |
| 4 | `bedrock_sonnet_press_001` | All Sonnet 4.6, 15yr | ~$13 | TODO |
| 5 | `bedrock_sonnet_gunboat_001` | All Sonnet 4.6, no press, 15yr | ~$8 | TODO |
| 6 | `bedrock_mixed_press_randomized_001` | Mixed + randomized, 15yr | ~$30 | TODO (optional) |
| 7 | `openrouter_battle_001` | 7 providers, 12yr | ~$15 | TODO |
| 8 | `openrouter_free_001` | 7 free models, 15yr | $0 | TODO (optional) |

**Priority order**: 4 → 5 → 7 → 3 → 6 → 8
