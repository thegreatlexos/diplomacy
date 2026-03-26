"""
Order analyzer for precision scoring.

Parses order files and summaries to count:
- Invalid orders (programmatically checked via adjacencies)
- Convoys
- Supports (own/other/hold/attack)
- Bounces
"""

import os
import yaml
import re
from typing import Dict, List, Optional
from diplomacy_game_engine.core.map import Power, Map, create_standard_map
from diplomacy_game_engine.core.game_state import UnitType
import logging

logger = logging.getLogger(__name__)


class OrderAnalyzer:
    """Analyzes orders and summaries for precision metrics."""
    
    def __init__(self, game_folder: str):
        """
        Initialize order analyzer.

        Args:
            game_folder: Root folder containing game files
        """
        self.game_folder = game_folder
        self.orders_folder = os.path.join(game_folder, "orders")
        self.summaries_folder = os.path.join(game_folder, "summaries")
        self.states_folder = os.path.join(game_folder, "states")

        # Load game map for adjacency checking
        self.game_map = create_standard_map()

        # Load game states for unit ownership lookup
        self.game_states = self._load_game_states()

        # Initialize counters
        self.precision_counts = {
            power.value: {
                'invalid_orders': 0,
                'convoys': 0,
                'support_own': 0,
                'support_other': 0,
                'support_hold': 0,
                'support_attack': 0,
                'bounces': 0,
                # New metrics
                'self_attacks': 0,       # Attacking own units
                'self_blocks': 0,        # Moving to same destination as own unit
                'wasted_supports': 0,    # Supporting unit that isn't moving/holding
                'unused_convoy_opps': 0, # Fleet in sea adjacent to army but not convoying
                'holds': 0,              # Simple hold orders
                'moves': 0,              # Move orders (valid or not)
            }
            for power in Power
        }

        # Strategic metrics (computed from game states)
        self.strategic_metrics = {
            power.value: {
                'peak_sc_count': 0,
                'final_sc_count': 0,
                'survival_years': 0,
                'eliminated_year': None,
                'sc_gains': [],  # List of (year, delta) tuples
            }
            for power in Power
        }

        # Initialize per-year counters
        self.yearly_counts = {}  # year -> power -> metrics
    
    def analyze_all_orders(self, max_year: Optional[int] = None) -> Dict[str, Dict[str, int]]:
        """
        Analyze all order files in the game.

        Args:
            max_year: If provided, only analyze orders up to this year (inclusive)

        Returns:
            Dict mapping power name to precision counts
        """
        if not os.path.exists(self.orders_folder):
            logger.warning("No orders folder found")
            return self.precision_counts

        # Get all order files (exclude retreat/winter for main analysis)
        order_files = sorted([
            f for f in os.listdir(self.orders_folder)
            if f.endswith('.yaml') and 'retreat' not in f and 'winter' not in f
        ])

        for filename in order_files:
            # Filter by max_year if specified
            if max_year is not None:
                year = self._extract_year(filename)
                if year is not None and year > max_year:
                    continue
            filepath = os.path.join(self.orders_folder, filename)
            self._analyze_order_file(filepath)

        # Extract bounces from summaries (still needed - can't detect programmatically)
        self._extract_bounces_from_summaries()

        # Compute strategic metrics from game states
        self._compute_strategic_metrics()

        logger.info("Order analysis complete")
        return self.precision_counts
    
    def _analyze_order_file(self, filepath: str):
        """Analyze a single order file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        # Extract phase from filename (e.g., "1901_01_spring.yaml" -> "1901_spring")
        filename = os.path.basename(filepath)
        phase_key = self._extract_phase_key(filename)

        # Extract year for per-year tracking
        year = self._extract_year(filename)

        # Get the state from BEFORE orders execute
        state_key = self._get_state_before_orders(phase_key)

        orders = data.get('orders', [])

        # Build order maps for cross-order analysis
        orders_by_power = {}  # power -> list of orders
        move_destinations = {}  # power -> list of destinations
        unit_positions = {}  # power -> set of current locations
        convoy_orders = {}  # power -> list of convoy orders
        fleet_positions = {}  # power -> list of (location, is_sea)

        # First pass: categorize orders and build maps
        for order in orders:
            unit = order.get('unit', '')
            action = order.get('action', '')
            destination = order.get('destination', '')

            power_name = self._get_power_from_unit(unit, state_key)
            if not power_name:
                # For convoy, search all states
                if action == 'convoy':
                    power_name = self._get_power_from_unit(unit, None)
                if not power_name:
                    continue

            # Initialize power structures
            if power_name not in orders_by_power:
                orders_by_power[power_name] = []
                move_destinations[power_name] = []
                unit_positions[power_name] = set()
                convoy_orders[power_name] = []
                fleet_positions[power_name] = []

            orders_by_power[power_name].append(order)

            # Extract unit location
            parts = unit.strip().split()
            if len(parts) >= 2:
                unit_type = parts[0].upper()
                location = parts[1].split('/')[0]
                unit_positions[power_name].add(location.upper())

                # Track fleet positions for convoy opportunity detection
                if unit_type == 'F':
                    province = self.game_map.get_province(location)
                    is_sea = province.is_sea() if province else False
                    fleet_positions[power_name].append((location, is_sea))

            # Track move destinations
            if action == 'move' and destination:
                dest_normalized = destination.split('/')[0].upper()
                move_destinations[power_name].append(dest_normalized)

            # Track convoy orders
            if action == 'convoy':
                convoy_orders[power_name].append(order)

        # Second pass: analyze orders with full context
        for order in orders:
            unit = order.get('unit', '')
            action = order.get('action', '')
            destination = order.get('destination', '')

            power_name = self._get_power_from_unit(unit, state_key)
            if action == 'convoy' and not power_name:
                power_name = self._get_power_from_unit(unit, None)
            if not power_name:
                continue

            # Count basic order types
            if action == 'hold':
                self._increment_count(power_name, 'holds', year)

            elif action == 'move':
                self._increment_count(power_name, 'moves', year)

                if destination:
                    dest_normalized = destination.split('/')[0].upper()

                    # Check for invalid move
                    if self._is_invalid_move(unit, destination):
                        self._increment_count(power_name, 'invalid_orders', year)
                        logger.debug(f"Invalid move detected: {unit} -> {destination}")

                    # Check for self-attack (moving to location where own unit is)
                    if dest_normalized in unit_positions.get(power_name, set()):
                        self._increment_count(power_name, 'self_attacks', year)
                        logger.debug(f"Self-attack detected: {unit} -> {destination}")

                    # Check for self-block (multiple own units moving to same destination)
                    dest_count = move_destinations.get(power_name, []).count(dest_normalized)
                    if dest_count > 1:
                        # Only count once per duplicate (not per unit)
                        # We'll handle this by checking if this is the first occurrence
                        first_occurrence = True
                        for prev_order in orders_by_power.get(power_name, []):
                            if prev_order == order:
                                break
                            prev_dest = prev_order.get('destination', '')
                            if prev_dest and prev_dest.split('/')[0].upper() == dest_normalized:
                                first_occurrence = False
                                break
                        if not first_occurrence:
                            self._increment_count(power_name, 'self_blocks', year)
                            logger.debug(f"Self-block detected: multiple units to {destination}")

            elif action == 'convoy':
                self._increment_count(power_name, 'convoys', year)

            elif action == 'support':
                target_unit = order.get('supporting', '')
                target_power = self._get_power_from_unit(target_unit, phase_key)

                # Count own vs other
                if target_power == power_name:
                    self._increment_count(power_name, 'support_own', year)
                elif target_power:
                    self._increment_count(power_name, 'support_other', year)

                # Differentiate hold vs attack support
                if destination:
                    self._increment_count(power_name, 'support_attack', year)
                else:
                    self._increment_count(power_name, 'support_hold', year)

        # Detect unused convoy opportunities
        self._detect_unused_convoy_opportunities(
            orders_by_power, fleet_positions, unit_positions, year
        )
    
    def _extract_phase_key(self, filename: str) -> str:
        """Extract phase key from order filename."""
        # Filename format: "1901_01_spring.yaml" or "1901_02_fall.yaml"
        # Extract year and season
        parts = filename.replace('.yaml', '').split('_')
        if len(parts) >= 3:
            year = parts[0]
            season = parts[2]
            return f"{year}_{season}"
        return None

    def _extract_year(self, filename: str) -> int:
        """Extract year from order filename."""
        parts = filename.replace('.yaml', '').split('_')
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
        return 0

    def _ensure_yearly_counts(self, year: int, power_name: str):
        """Ensure yearly_counts has structure for this year/power."""
        if year not in self.yearly_counts:
            self.yearly_counts[year] = {}
        if power_name not in self.yearly_counts[year]:
            self.yearly_counts[year][power_name] = {
                'invalid_orders': 0,
                'convoys': 0,
                'support_own': 0,
                'support_other': 0,
                'support_hold': 0,
                'support_attack': 0,
                'bounces': 0,
                'self_attacks': 0,
                'self_blocks': 0,
                'wasted_supports': 0,
                'unused_convoy_opps': 0,
                'holds': 0,
                'moves': 0,
            }

    def _increment_count(self, power_name: str, metric: str, year: int = 0):
        """Increment a count for both aggregate and per-year tracking."""
        self.precision_counts[power_name][metric] += 1
        if year > 0:
            self._ensure_yearly_counts(year, power_name)
            self.yearly_counts[year][power_name][metric] += 1
    
    def _get_state_before_orders(self, phase_key: str) -> str:
        """
        Get the state key that shows unit positions BEFORE orders execute.
        
        For spring orders, we need the previous fall's state.
        For fall orders, we need the spring state from same year.
        """
        if not phase_key:
            return None
        
        year_str, season = phase_key.split('_')
        year = int(year_str)
        
        if season == 'spring':
            # For spring orders, use previous year's fall state
            prev_year = year - 1
            if prev_year < 1901:
                # For 1901 spring, no previous state exists
                # Try using initial state or the spring state itself
                return phase_key
            lookup_key = f"{prev_year}_fall"
        else:  # fall
            # For fall orders, use same year's spring state
            lookup_key = f"{year}_spring"
        
        # Verify the state exists, otherwise fall back to current phase
        if lookup_key in self.game_states:
            return lookup_key
        else:
            return phase_key
    
    def _load_game_states(self) -> Dict:
        """Load all game states for unit ownership lookup."""
        states = {}
        if not os.path.exists(self.states_folder):
            return states
        
        import json
        state_files = [f for f in os.listdir(self.states_folder) if f.endswith('.json')]
        
        for filename in state_files:
            filepath = os.path.join(self.states_folder, filename)
            with open(filepath, 'r') as f:
                state_data = json.load(f)
                # Key by year_season for easy lookup
                year = state_data.get('year', 0)
                season = state_data.get('season', '').lower()
                key = f"{year}_{season}"
                states[key] = state_data
        
        return states
    
    def _get_power_from_unit(self, unit_str: str, phase_key: str = None) -> str:
        """
        Extract power name from unit string by looking up unit ownership in game state.
        
        Args:
            unit_str: Unit string like "A Lvp" or "F Lon"
            phase_key: Optional phase key like "1901_spring" to look up specific state
            
        Returns:
            Power name or None if not found
        """
        if not unit_str or not self.game_states:
            return None
        
        # Parse unit string to get location
        # Format: "A Lvp" or "F Lon" or "F StP/sc"
        parts = unit_str.strip().split()
        if len(parts) < 2:
            return None
        
        location = parts[1].split('/')[0]  # Handle coast notation like "StP/sc"
        
        # If we have a specific phase, use that state
        if phase_key and phase_key in self.game_states:
            state = self.game_states[phase_key]
            return self._find_unit_owner(location, state)
        
        # Otherwise, try to find in any state (less accurate but better than nothing)
        for state in self.game_states.values():
            owner = self._find_unit_owner(location, state)
            if owner:
                return owner
        
        return None
    
    def _find_unit_owner(self, location: str, state: Dict) -> str:
        """Find which power owns a unit at the given location."""
        units = state.get('units', [])

        for unit in units:
            if unit.get('location') == location:
                return unit.get('power')

        return None

    def _is_invalid_move(self, unit: str, destination: str) -> bool:
        """
        Check if a move order is invalid (non-adjacent destination or wrong unit type).

        Args:
            unit: Unit string like "A Lon" or "F NTH"
            destination: Destination province like "Hol" or "NWG"

        Returns:
            True if the move is invalid, False if valid
        """
        # Parse unit string to get type and location
        parts = unit.strip().split()
        if len(parts) < 2:
            return False  # Can't determine, assume valid

        unit_type = parts[0].upper()  # 'A' or 'F'
        source = parts[1].split('/')[0]  # Handle coast notation like "StP/sc"

        # Normalize destination (remove coast notation for adjacency check)
        dest = destination.split('/')[0] if destination else ''

        if not dest:
            return False  # No destination, not a move order issue

        # Check adjacency using the game map
        if not self.game_map.is_adjacent(source, dest):
            logger.debug(f"Non-adjacent move: {source} -> {dest}")
            return True

        # Check unit type restrictions
        dest_province = self.game_map.get_province(dest)
        if dest_province:
            # Army trying to move to sea
            if unit_type == 'A' and dest_province.is_sea():
                logger.debug(f"Army trying to move to sea: {unit} -> {dest}")
                return True

            # Fleet trying to move to land-only province
            if unit_type == 'F' and dest_province.is_land():
                logger.debug(f"Fleet trying to move to land: {unit} -> {dest}")
                return True

        return False

    def _extract_year_from_summary(self, filename: str) -> int:
        """Extract year from summary filename (e.g., '1901_spring_summary.md')."""
        parts = filename.replace('.md', '').split('_')
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
        return 0

    def _extract_invalid_orders_from_summaries(self):
        """Extract invalid order counts from summaries."""
        if not os.path.exists(self.summaries_folder):
            return

        summary_files = sorted([f for f in os.listdir(self.summaries_folder) if f.endswith('.md')])

        for filename in summary_files:
            filepath = os.path.join(self.summaries_folder, filename)
            year = self._extract_year_from_summary(filename)
            with open(filepath, 'r') as f:
                content = f.read()

            # Look for the "Critical Errors" or "Illegal Orders" section
            # This section lists each power's errors once
            illegal_section_pattern = r'(?:Critical Errors|Illegal Orders)[^\n]*\n\n(.*?)(?:\n\n##|\Z)'
            illegal_section_match = re.search(illegal_section_pattern, content, re.DOTALL | re.IGNORECASE)

            if illegal_section_match:
                illegal_section = illegal_section_match.group(1)

                # Count bullet points mentioning each power
                for power in Power:
                    power_name = power.value

                    # Look for bullet points mentioning this power
                    # Pattern: - **PowerName** or - PowerName
                    pattern = rf'^[-•]\s*\*?\*?{power_name}\*?\*?'
                    matches = re.findall(pattern, illegal_section, re.MULTILINE | re.IGNORECASE)

                    if matches:
                        # Each bullet point = 1 invalid order
                        for _ in matches:
                            self._increment_count(power_name, 'invalid_orders', year)
    
    def _extract_bounces_from_summaries(self):
        """Extract bounce counts from summaries."""
        if not os.path.exists(self.summaries_folder):
            return

        summary_files = sorted([f for f in os.listdir(self.summaries_folder) if f.endswith('.md')])

        for filename in summary_files:
            filepath = os.path.join(self.summaries_folder, filename)
            year = self._extract_year_from_summary(filename)
            with open(filepath, 'r') as f:
                content = f.read()

            # Look for bounce mentions in the text
            # Common patterns: "PowerName...bounced", "PowerName's move bounced"
            for power in Power:
                power_name = power.value

                # Search for this power mentioned with bounces
                # Pattern: PowerName (or possessive) followed by bounce/bounced within reasonable distance
                patterns = [
                    rf'{power_name}[^\n.]*?bounced?',
                    rf'{power_name}\'s[^\n.]*?bounced?',
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for _ in matches:
                        self._increment_count(power_name, 'bounces', year)

    def get_yearly_metrics(self) -> Dict[int, Dict[str, Dict[str, int]]]:
        """
        Return per-year metrics after analysis is complete.

        Returns:
            Dict: year -> power -> metrics
        """
        return self.yearly_counts

    def get_strategic_metrics(self) -> Dict[str, Dict]:
        """Return strategic metrics for all powers."""
        return self.strategic_metrics

    def _detect_unused_convoy_opportunities(
        self,
        orders_by_power: Dict,
        fleet_positions: Dict,
        unit_positions: Dict,
        year: int  # noqa: ARG002 - kept for future use
    ):
        """
        Detect cases where a fleet in sea could have convoyed an army but didn't.

        This is a heuristic - we check if a power has:
        - A fleet in a sea zone
        - An army on a coastal province adjacent to that sea
        - The fleet is not convoying

        Note: Currently disabled as convoy chain detection is complex.

        Args:
            orders_by_power: Dict of power -> list of orders
            fleet_positions: Dict of power -> list of (location, is_sea)
            unit_positions: Dict of power -> set of unit locations
            year: Year for tracking (unused currently)
        """
        for power_name, fleets in fleet_positions.items():
            # Get orders for this power
            power_orders = orders_by_power.get(power_name, [])

            # Check which fleets are convoying
            convoying_fleets = set()
            for order in power_orders:
                if order.get('action') == 'convoy':
                    unit = order.get('unit', '')
                    parts = unit.strip().split()
                    if len(parts) >= 2:
                        convoying_fleets.add(parts[1].split('/')[0].upper())

            # Check each fleet in sea
            for fleet_loc, is_sea in fleets:
                if not is_sea:
                    continue

                fleet_loc_upper = fleet_loc.upper()
                if fleet_loc_upper in convoying_fleets:
                    continue  # Already convoying

                # Check if there's an army on an adjacent coastal province
                adjacent = self.game_map.get_adjacent_provinces(fleet_loc)
                for adj_loc in adjacent:
                    adj_upper = adj_loc.upper()
                    if adj_upper in unit_positions.get(power_name, set()):
                        # Check if it's an army (not a fleet) - would need more context
                        # For simplicity, check if the adjacent is coastal (army could be there)
                        adj_province = self.game_map.get_province(adj_loc)
                        if adj_province and adj_province.is_coastal():
                            # Convoy opportunity detection is complex - skip for now
                            # Would need to verify army is trying to cross water and has valid path
                            break

    def _compute_strategic_metrics(self):
        """Compute strategic metrics from game states."""
        if not self.game_states:
            return

        # Sort states by year and season
        sorted_states = []
        for key, state in self.game_states.items():
            year = state.get('year', 0)
            season = state.get('season', '').lower()
            season_order = {'spring': 0, 'fall': 1, 'winter': 2}.get(season, 3)
            sorted_states.append((year, season_order, key, state))

        sorted_states.sort(key=lambda x: (x[0], x[1]))

        # Track SC counts over time
        prev_sc_counts = {power.value: 3 for power in Power}  # Starting SCs

        for year, season_order, key, state in sorted_states:
            # Only count after fall (when SC ownership updates)
            if season_order != 1:  # Not fall
                continue

            supply_centers = state.get('supply_centers', {})

            # Count SCs per power
            sc_counts = {power.value: 0 for power in Power}
            for sc, owner in supply_centers.items():
                if owner in sc_counts:
                    sc_counts[owner] += 1

            for power_name, count in sc_counts.items():
                # Update peak SC
                if count > self.strategic_metrics[power_name]['peak_sc_count']:
                    self.strategic_metrics[power_name]['peak_sc_count'] = count

                # Track SC changes
                prev_count = prev_sc_counts.get(power_name, 0)
                delta = count - prev_count
                if delta != 0:
                    self.strategic_metrics[power_name]['sc_gains'].append((year, delta))

                # Update final SC count
                self.strategic_metrics[power_name]['final_sc_count'] = count

                # Check for elimination
                if count == 0 and prev_count > 0:
                    self.strategic_metrics[power_name]['eliminated_year'] = year

                # Update survival years
                if count > 0:
                    self.strategic_metrics[power_name]['survival_years'] = year - 1901 + 1

                prev_sc_counts[power_name] = count

    def compute_order_complexity(self) -> Dict[str, float]:
        """
        Compute order complexity score for each power.

        Complexity = (supports + convoys) / total_orders
        Higher = more sophisticated play

        Returns:
            Dict mapping power name to complexity score (0.0 to 1.0)
        """
        complexity_scores = {}

        for power_name, counts in self.precision_counts.items():
            total_supports = counts['support_own'] + counts['support_other']
            total_convoys = counts['convoys']
            total_holds = counts['holds']
            total_moves = counts['moves']

            total_orders = total_supports + total_convoys + total_holds + total_moves
            if total_orders == 0:
                complexity_scores[power_name] = 0.0
            else:
                # Complexity = advanced orders / total orders
                advanced = total_supports + total_convoys
                complexity_scores[power_name] = round(advanced / total_orders, 3)

        return complexity_scores

    def compute_error_rate(self) -> Dict[str, float]:
        """
        Compute error rate for each power.

        Error rate = (invalid + self_attacks + self_blocks) / total_orders
        Lower = better play

        Returns:
            Dict mapping power name to error rate (0.0 to 1.0)
        """
        error_rates = {}

        for power_name, counts in self.precision_counts.items():
            total_errors = (
                counts['invalid_orders'] +
                counts['self_attacks'] +
                counts['self_blocks']
            )
            total_orders = (
                counts['support_own'] + counts['support_other'] +
                counts['convoys'] + counts['holds'] + counts['moves']
            )

            if total_orders == 0:
                error_rates[power_name] = 0.0
            else:
                error_rates[power_name] = round(total_errors / total_orders, 3)

        return error_rates
