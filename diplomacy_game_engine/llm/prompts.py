"""
Prompt builder for generating LLM prompts with game context.
"""

from typing import Dict, List, Optional
from diplomacy_game_engine.core.game_state import GameState, Season, Unit
from diplomacy_game_engine.core.map import Power, Map, ProvinceType
from diplomacy_game_engine.core.orders import Order


class PromptBuilder:
    """Builds prompts for LLM players with game rules and context."""
    
    @staticmethod
    def build_game_background() -> str:
        """Build game background and context section."""
        return """
# 🎮 DIPLOMACY - Europe 1901

You are playing the classic board game Diplomacy, set in pre-WWI Europe.

## The Setting
- **Year**: 1901
- **Map**: Europe with 75 provinces
- **Powers**: 7 great powers competing for dominance
- **Victory**: First to control 18 of 34 supply centers

## The Game Flow
- **Spring**: Diplomacy (3 rounds) → Orders → Resolution
- **Fall**: Diplomacy (3 rounds) → Orders → Resolution → SC ownership updates
- **Winter**: Build/disband units based on SC count

## Core Concept
This is a game of **negotiation, alliance, and betrayal**. You must:
- Form alliances to coordinate attacks
- Expand your territory through military conquest
- Betray allies when beneficial
- Reach 18 supply centers before anyone else

**Remember**: Only ONE power can win. Alliances are tools, not commitments.
"""
    
    @staticmethod
    def build_supply_center_list(state: GameState, power: Power) -> str:
        """Build dedicated supply center list showing targets."""
        lines = [
            "# 📍 SUPPLY CENTERS (34 Total - Your Path to Victory)",
            ""
        ]
        
        # Your home centers
        home_centers = state.game_map.get_home_centers(power)
        if home_centers:
            lines.append("## Your Home Centers:")
            home_list = [f"{hc.abbreviation} ({hc.full_name})" for hc in home_centers]
            lines.append(", ".join(home_list))
            lines.append("")
        
        # Neutral SCs
        neutral_scs = []
        for province in state.game_map.get_supply_centers():
            if province.abbreviation not in state.supply_centers:
                neutral_scs.append(f"{province.abbreviation} ({province.full_name})")
        
        if neutral_scs:
            lines.append("## Neutral Supply Centers (CAPTURE THESE FIRST - No defender!):")
            lines.append(", ".join(neutral_scs))
            lines.append("")
        
        # Enemy SCs by power
        lines.append("## Enemy Supply Centers (Harder - Need supported attacks):")
        for p in Power:
            if p != power:
                p_scs = [abbr for abbr, owner in state.supply_centers.items() if owner == p]
                if p_scs:
                    lines.append(f"- {p.value}: {', '.join(sorted(p_scs))}")
        
        lines.append("")
        lines.append("**Strategy**: Target neutral SCs first (easier), then coordinate attacks on enemy SCs.")
        
        return "\n".join(lines)
    
    @staticmethod
    def build_capture_mechanics() -> str:
        """Build explanation of how to capture supply centers."""
        return """
# 🎯 HOW TO CAPTURE SUPPLY CENTERS

To capture a supply center:
1. **Identify target SC** (check list above or [SC] markers in TERRITORIES)
2. **Move a unit to OCCUPY that province** (not just through it)
3. **If enemy-occupied**: Use supported attack (need 2+ strength to dislodge)
4. **Hold the province until end of Fall**
5. **SC ownership transfers in Fall** if you occupy it

## Critical Rules
- Moving THROUGH a province doesn't capture it
- You must END your move IN the SC province
- SC ownership only updates at end of FALL (not Spring)
- You need to HOLD the SC through Fall to claim it

## Capture Strategy
**Neutral SCs** (easiest):
- No defender, just move in
- Examples: Belgium, Holland, Denmark, Sweden, Norway

**Enemy SCs** (harder):
- Need supported attack if occupied
- Coordinate with allies: one unit attacks, another supports
- Example: A Ruh - Bel + A Mun S A Ruh - Bel (strength 2 vs 1)

**Remember**: You need 18 SCs to win. Every SC you capture matters!
"""
    
    @staticmethod
    def build_victory_status(state: GameState, power: Power) -> str:
        """Build dynamic victory status section showing competitive standings."""
        lines = [
            "# 🏆 VICTORY STATUS - THIS IS A COMPETITIVE GAME",
            "",
            "**WIN CONDITION**: First power to control 18 supply centers WINS",
            "**ONLY ONE POWER CAN WIN - You are competing against 6 other powers**",
            ""
        ]
        
        # Get SC counts for all powers and sort by count
        sc_counts = [(p, state.get_sc_count(p)) for p in Power]
        sc_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate your position
        your_sc = state.get_sc_count(power)
        needed = 18 - your_sc
        
        lines.append("CURRENT STANDINGS (Ranked by Supply Centers):")
        for i, (p, count) in enumerate(sc_counts, 1):
            leader_mark = " ⚠️ LEADER" if count >= 10 else ""
            threat_mark = " ⚠️ THREAT" if count >= 15 else ""
            you_mark = " ← YOU" if p == power else ""
            lines.append(f"{i}. {p.value:18} {count} SCs{leader_mark}{threat_mark}{you_mark}")
        
        lines.append("")
        lines.append(f"**YOUR POSITION**: {your_sc}/18 SCs - YOU NEED {needed} MORE TO WIN")
        
        # Calculate neutral SCs
        total_scs = 34
        claimed_scs = sum(count for _, count in sc_counts)
        neutral_count = total_scs - claimed_scs
        
        if neutral_count > 0:
            lines.append(f"**NEUTRAL SCs AVAILABLE**: {neutral_count} unclaimed supply centers")
            lines.append("")
            lines.append("Neutral SCs you can capture:")
            neutral_scs = []
            for province in state.game_map.get_supply_centers():
                if province.abbreviation not in state.supply_centers:
                    neutral_scs.append(f"{province.abbreviation} ({province.full_name})")
            if neutral_scs:
                lines.append(", ".join(neutral_scs))
        
        return "\n".join(lines)
    
    @staticmethod
    def build_combat_mechanics() -> str:
        """Build explanation of combat and support mechanics."""
        return """
# ⚔️ MOVEMENT AND COMBAT RULES (CRITICAL)

## Unit Type Restrictions
**Armies**:
- Can move on LAND and COASTAL provinces
- CANNOT move to SEA provinces (unless convoyed by fleets)

**Fleets**:
- Can move on SEA and COASTAL provinces
- CANNOT move to pure LAND provinces

Check the TERRITORIES section for province types.

## Adjacency Rule
- Units can ONLY move to adjacent provinces
- **Check the ADJACENCIES section before ordering**
- Non-adjacent moves are ILLEGAL and treated as HOLD (wasted turn)

## Multi-Coast Provinces
Spain (Spa), St Petersburg (StP), Bulgaria (Bul) have multiple coasts:
- Fleets must specify coast: Spa/nc, Spa/sc, StP/nc, StP/sc, Bul/ec, Bul/sc
- Different coasts have different adjacencies
- Check ADJACENCIES section for coast-specific connections

## Combat Strength Rules
- Each unit has base strength of 1
- Support from adjacent units adds +1 strength per supporter
- **Attacker needs MORE strength than defender to succeed**

## CRITICAL: 1 vs 1 = BOUNCE
- Single unit attacking occupied province: strength 1 vs 1 = BOTH STAY IN PLACE
- **To dislodge an enemy, you MUST have support** (need 2+ strength vs 1)
- This requires coordinating with another unit

## How Support Works
- Supporting unit must be adjacent to the TARGET province (not just the supported unit)
- Support adds +1 to the supported unit's strength
- With support: strength 2 vs 1 = attacker succeeds and dislodges defender
- Support is cut if the supporting unit is attacked (except by the unit being supported)

## CRITICAL: HOW TO VERIFY YOUR MOVES

Before submitting each order, YOU MUST verify it is legal:

**Step 1: Find your unit's location in ADJACENCIES section**
Example: If your unit is at Apu, look up "Apu:" in ADJACENCIES

**Step 2: Check if destination is listed**
Example: Apu: ADR, ION, Nap, Rom
- Apu CAN move to: ADR, ION, Nap, Rom
- Apu CANNOT move to: Gre, Alb, Ven (not listed = not adjacent)

**Step 3: For multi-coast provinces, verify the coast**
Example: StP has two coasts (nc and sc)
- StP/sc connects to: Bot, Fin
- StP/nc connects to: Bar, Nwy
- StP/sc CANNOT move to Swe (not adjacent to south coast)

**Common Illegal Moves (DO NOT MAKE THESE):**
- Apu → Gre (not adjacent, need 2 moves: Apu → Alb → Gre)
- StP/sc → Swe (wrong coast, need: StP → Bot → Swe)
- Ber → Den (not adjacent, need: Ber → Kie → Den)

## Before Submitting Orders - CHECKLIST:
1. ✓ Look up EACH unit in ADJACENCIES section
2. ✓ Verify destination IS LISTED in adjacencies
3. ✓ For multi-coast provinces, verify correct coast
4. ✓ For attacks on occupied provinces, ensure you have SUPPORT
5. ✓ Verify supporting units are adjacent to the TARGET
6. ✓ Remember: Illegal moves waste your turn (become HOLD)
"""
    
    GAME_RULES = """
# DIPLOMACY GAME RULES

## Unit Types
- **Army (A)**: Can move on land provinces
- **Fleet (F)**: Can move on sea and coastal provinces

## Order Types

### Movement Phase Orders
1. **HOLD (H)**: Unit stays in place
   - Format: "A Par H" or "F Lon H"

2. **MOVE (-)**: Unit moves to adjacent province
   - Format: "A Par - Bur" or "F Lon - ENG"
   - Armies can be convoyed across sea by fleets

3. **SUPPORT (S)**: Support another unit's move or hold
   - Format: "A Par S A Mar - Bur" (support move)
   - Format: "A Par S A Bur" (support hold)
   - Support is cut if the supporting unit is attacked (except by the unit being supported)

4. **CONVOY (C)**: Fleet transports an army across sea
   - Format: "F ENG C A Lon - Pic"
   - Multiple fleets can form a convoy chain

### Retreat Phase Orders
- **RETREAT (-)**: Dislodged unit retreats to adjacent unoccupied province
  - Format: "A Par - Bur"
  - Cannot retreat to province attacker came from
  - Cannot retreat to contested province

### Winter Phase Orders
1. **BUILD (B)**: Create new unit in unoccupied home supply center
   - Format: "B A Par" or "B F Bre"
   - Only if you have more SCs than units

2. **DISBAND (D)**: Remove a unit
   - Format: "D A Par"
   - Required if you have more units than SCs

## Key Rules
- Units can only move to adjacent provinces
- Multiple units moving to same province = standoff (all bounce)
- Successful attack with more strength dislodges defender
- Support adds +1 strength to supported action
- Supply center ownership updates only in Fall
- Fleets on multi-coast provinces (Spain, St Petersburg, Bulgaria) must specify coast
"""

    @staticmethod
    def build_territory_list(game_map: Map) -> str:
        """Build compact territory list."""
        land = []
        coastal = []
        sea = []
        
        for province in sorted(game_map.get_all_provinces(), key=lambda p: p.abbreviation):
            abbr = province.abbreviation
            entry = abbr
            
            if province.is_supply_center:
                if province.home_center_of:
                    entry += f"[SC,{province.home_center_of.value}]"
                else:
                    entry += "[SC]"
            
            if province.is_land():
                land.append(entry)
            elif province.is_coastal():
                if province.has_multiple_coasts():
                    coasts = ",".join([c.value for c in province.coasts])
                    entry += f"({coasts})"
                coastal.append(entry)
            else:
                sea.append(entry)
        
        return (
            "# TERRITORIES\n"
            f"LAND:{','.join(land)}|"
            f"COAST:{','.join(coastal)}|"
            f"SEA:{','.join(sea)}"
        )
    
    @staticmethod
    def build_adjacency_list(game_map: Map) -> str:
        """Build compact adjacency list."""
        adjacencies = []
        for abbr in sorted(game_map.adjacencies.keys()):
            adjacent = game_map.get_adjacent_provinces(abbr)
            if adjacent:
                adj_str = ",".join(sorted(adjacent))
                adjacencies.append(f"{abbr}:{adj_str}")
        
        return "# ADJACENCIES\n" + "|".join(adjacencies)
    
    @staticmethod
    def build_game_state_summary(state: GameState, power: Power) -> str:
        """Build compact game state summary."""
        lines = [
            f"# GAME STATE: {state.year} {state.season.value}",
            f"YOUR POWER: {power.value} ({state.get_sc_count(power)}sc,{state.get_unit_count(power)}u)",
            ""
        ]
        
        # Your units (readable format)
        your_units = state.get_units_by_power(power)
        if your_units:
            unit_strs = []
            for unit in sorted(your_units, key=lambda u: u.location):
                coast_str = f"/{unit.coast.value}" if unit.coast else ""
                unit_strs.append(f"{unit.unit_type.value[0]}-{unit.location}{coast_str}")
            lines.append(f"YOUR UNITS: {','.join(unit_strs)}")
        else:
            lines.append("YOUR UNITS: None")
        
        lines.append("")
        
        # All units - compact format
        all_units = []
        for p in Power:
            units = state.get_units_by_power(p)
            if units:
                unit_strs = []
                for unit in sorted(units, key=lambda u: u.location):
                    coast_str = f"/{unit.coast.value}" if unit.coast else ""
                    unit_strs.append(f"{unit.unit_type.value[0]}-{unit.location}{coast_str}")
                all_units.append(f"{p.value}({state.get_sc_count(p)}sc):{','.join(unit_strs)}")
        
        lines.append("ALL UNITS: " + "|".join(all_units))
        lines.append("")
        
        # SC ownership - compact format
        sc_by_power = {}
        for abbr, owner in sorted(state.supply_centers.items()):
            if owner not in sc_by_power:
                sc_by_power[owner] = []
            sc_by_power[owner].append(abbr)
        
        sc_strs = []
        for p in Power:
            if p in sc_by_power:
                sc_strs.append(f"{p.value}:{','.join(sorted(sc_by_power[p]))}")
        
        lines.append("SC OWNERSHIP: " + "|".join(sc_strs))
        
        return "\n".join(lines)
    
    @staticmethod
    def build_press_history(press_threads: Dict[str, str], power: Power) -> str:
        """Build press history from thread files."""
        if not press_threads:
            return "# PRESS HISTORY\n\nNo messages yet."
        
        lines = ["# PRESS HISTORY\n"]
        
        for other_power, thread_content in sorted(press_threads.items()):
            lines.append(f"## Conversation with {other_power}")
            lines.append(thread_content)
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def build_press_round_prompt(
        state: GameState,
        power: Power,
        game_map: Map,
        press_threads: Dict[str, str],
        round_number: int
    ) -> str:
        """Build prompt for press round."""
        prompt = f"""You are playing Diplomacy as {power.value}.

{PromptBuilder.build_game_background()}

{PromptBuilder.build_victory_status(state, power)}

{PromptBuilder.build_supply_center_list(state, power)}

{PromptBuilder.build_capture_mechanics()}

{PromptBuilder.build_combat_mechanics()}

{PromptBuilder.GAME_RULES}

{PromptBuilder.build_territory_list(game_map)}

{PromptBuilder.build_adjacency_list(game_map)}

{PromptBuilder.build_game_state_summary(state, power)}

{PromptBuilder.build_press_history(press_threads, power)}

---

# TASK: PRESS ROUND {round_number}

This is press round {round_number} for {state.season.value} {state.year}.

## STRATEGIC PRESS GUIDANCE

**You do NOT need to message every power every round.**

Strategic considerations:
- **Focus your diplomacy** on 2-3 key powers (allies or targets)
- **Silence can be strategic** - not messaging a power sends a message
- **Prioritize based on geography** - focus on neighbors and threats
- **Save effort for important negotiations** - quality over quantity
- **Avoid revealing too much** - selective communication maintains mystery

When to message:
- Coordinating attacks with allies
- Negotiating non-aggression with neighbors
- Deceiving potential enemies
- Responding to messages received

When NOT to message:
- Powers too far away to interact with
- Powers you're planning to betray (maintain plausible deniability)
- When you have nothing strategic to say

Remember:
- **Form alliances to coordinate supported attacks** (you need 2+ units to dislodge enemies)
- **Identify expansion targets** (neutral SCs or weak enemy positions)
- **Negotiate support** for your attacks
- **Deceive if beneficial** - you can lie about your intentions
- **Only ONE power wins** - alliances are temporary tools

## RESPONSE FORMAT (CRITICAL - FOLLOW EXACTLY)

You MUST format your response EXACTLY as shown below. Each message must be on its own line starting with "TO" followed by the power name in ALL CAPS, then a colon, then your message.

TO FRANCE: Your message to France here
TO GERMANY: Your message to Germany here
TO RUSSIA: Your message to Russia here

Valid power names: ENGLAND, FRANCE, GERMANY, ITALY, AUSTRIA, RUSSIA, TURKEY

Example response:
TO FRANCE: I propose we coordinate a supported attack on Germany. I'll move A Pic - Bur, you support from Paris. Together we can break through.
TO GERMANY: Let's maintain peace on our border this turn.

IMPORTANT:
- Start each message line with "TO POWERNAME:"
- Use power names in ALL CAPS
- You can send to multiple powers, one power, or no powers
- Do NOT include any other text before or after your messages
- Do NOT number your messages
- Do NOT use quotes around messages

Submit your messages now:
"""
        return prompt
    
    @staticmethod
    def build_movement_orders_prompt(
        state: GameState,
        power: Power,
        game_map: Map,
        press_threads: Dict[str, str]
    ) -> str:
        """Build prompt for movement orders."""
        # Build unit list
        your_units = state.get_units_by_power(power)
        unit_list = "\n".join([
            f"- {unit.unit_type.value[0]} {unit.location}{('/' + unit.coast.value) if unit.coast else ''}"
            for unit in sorted(your_units, key=lambda u: u.location)
        ])
        
        prompt = f"""You are playing Diplomacy as {power.value}.

{PromptBuilder.build_game_background()}

{PromptBuilder.build_victory_status(state, power)}

{PromptBuilder.build_supply_center_list(state, power)}

{PromptBuilder.build_capture_mechanics()}

{PromptBuilder.build_combat_mechanics()}

{PromptBuilder.GAME_RULES}

{PromptBuilder.build_territory_list(game_map)}

{PromptBuilder.build_adjacency_list(game_map)}

{PromptBuilder.build_game_state_summary(state, power)}

{PromptBuilder.build_press_history(press_threads, power)}

---

# TASK: SUBMIT MOVEMENT ORDERS

Submit orders for ALL your units for {state.season.value} {state.year}.

## STRATEGIC REMINDERS:
- **You need {18 - state.get_sc_count(power)} more SCs to win**
- **Coordinate supported attacks** - Single units usually bounce
- **Target neutral SCs** or weak enemy positions
- **Execute any coordinated plans** from your diplomatic discussions

## RESPONSE FORMAT (CRITICAL - FOLLOW EXACTLY)

You MUST format your response as a simple list of orders, one per line. Each order must start with the unit type (A or F), followed by the location, then the action.

Order formats:
- Move: A Par - Bur
- Hold: A Par H
- Support move: A Par S A Mar - Bur
- Support hold: A Par S A Bur
- Convoy: F ENG C A Lon - Pic

Example response (for France with 3 units):
F Bre - MAO
A Par - Bur
A Mar S A Par - Bur

CRITICAL RULES:
1. One order per line
2. Start each line with unit type: A (Army) or F (Fleet)
3. Use 3-letter province abbreviations (e.g., Par, Lon, ENG)
4. Use " - " (space-dash-space) for moves
5. Use " H" for holds
6. Use " S " for supports
7. Use " C " for convoys
8. Do NOT include explanations, commentary, or numbering
9. Do NOT use quotes around orders
10. Submit an order for EVERY unit you control

Your units that need orders:
{unit_list}

Submit your orders now in a code block:

```orders
F Bre - MAO
A Par - Bur
A Mar - Spa
```
"""
        return prompt
    
    @staticmethod
    def build_retreat_orders_prompt(
        state: GameState,
        power: Power,
        game_map: Map,
        dislodged_units: List
    ) -> str:
        """Build prompt for retreat orders."""
        lines = [f"You are playing Diplomacy as {power.value}.", ""]
        
        lines.append("# DISLODGED UNITS\n")
        lines.append("The following units were dislodged and must retreat or be disbanded:\n")
        
        for du in dislodged_units:
            valid_retreats = du.get_valid_retreat_destinations(game_map, state)
            lines.append(f"- {du.unit.unit_type.value[0]} {du.dislodged_from}")
            if valid_retreats:
                lines.append(f"  Valid retreat destinations: {', '.join(sorted(valid_retreats))}")
            else:
                lines.append(f"  No valid retreats - will be DISBANDED")
        
        lines.append("\n---\n")
        lines.append("# TASK: SUBMIT RETREAT ORDERS\n")
        lines.append("\n## RESPONSE FORMAT (CRITICAL - FOLLOW EXACTLY)\n")
        lines.append("For each dislodged unit, submit a retreat order on one line:")
        lines.append("Format: A Par - Bur\n")
        lines.append("Example:")
        lines.append("A Par - Bur")
        lines.append("F Lon - Yor\n")
        lines.append("IMPORTANT:")
        lines.append("- One order per line")
        lines.append("- Use format: UNIT_TYPE LOCATION - DESTINATION")
        lines.append("- Only retreat to valid destinations listed above")
        lines.append("- If you don't submit an order for a unit, it will be DISBANDED")
        lines.append("- Do NOT include explanations or commentary\n")
        lines.append("Submit your retreat orders now (one per line, no other text):")
        
        return "\n".join(lines)
    
    @staticmethod
    def build_build_disband_prompt(
        state: GameState,
        power: Power,
        game_map: Map,
        adjustment: int
    ) -> str:
        """Build prompt for build/disband orders."""
        lines = [f"You are playing Diplomacy as {power.value}.", ""]
        
        lines.append(f"# WINTER {state.year} ADJUSTMENTS\n")
        lines.append(f"Supply Centers: {state.get_sc_count(power)}")
        lines.append(f"Units: {state.get_unit_count(power)}")
        lines.append(f"Adjustment needed: {adjustment:+d}\n")
        
        if adjustment > 0:
            # Need to build
            lines.append(f"You must BUILD {adjustment} unit(s).\n")
            lines.append("Available home centers for builds:")
            home_centers = game_map.get_home_centers(power)
            for hc in home_centers:
                if state.get_unit_at(hc.abbreviation) is None:
                    if state.supply_centers.get(hc.abbreviation) == power:
                        lines.append(f"- {hc.abbreviation} ({hc.full_name})")
            
            lines.append("\n## RESPONSE FORMAT (CRITICAL - FOLLOW EXACTLY)\n")
            lines.append("Format: B A Par  or  B F Bre")
            lines.append("Example:")
            lines.append("B A Par")
            lines.append("B F Bre\n")
            lines.append("IMPORTANT:")
            lines.append("- One build per line")
            lines.append("- Start with 'B' then unit type (A or F) then location")
            lines.append("- Only build in available home centers listed above")
            lines.append("- Do NOT include explanations\n")
            lines.append("Submit your build orders now:")
            
        elif adjustment < 0:
            # Need to disband
            lines.append(f"You must DISBAND {abs(adjustment)} unit(s).\n")
            lines.append("Your units:")
            for unit in state.get_units_by_power(power):
                coast_str = f"/{unit.coast.value}" if unit.coast else ""
                lines.append(f"- {unit.unit_type.value[0]} {unit.location}{coast_str}")
            
            lines.append("\n## RESPONSE FORMAT (CRITICAL - FOLLOW EXACTLY)\n")
            lines.append("Format: D A Par  or  D F Bre")
            lines.append("Example:")
            lines.append("D A Par")
            lines.append("D F Bre\n")
            lines.append("IMPORTANT:")
            lines.append("- One disband per line")
            lines.append("- Start with 'D' then unit type (A or F) then location")
            lines.append("- Only disband your own units listed above")
            lines.append("- Do NOT include explanations\n")
            lines.append("Submit your disband orders now:")
        else:
            lines.append("No adjustments needed.")
            lines.append("\nRespond with: NO ORDERS")
        
        return "\n".join(lines)
