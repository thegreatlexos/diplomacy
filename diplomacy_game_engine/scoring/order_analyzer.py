"""
Order analyzer for precision scoring.

Parses order files and summaries to count:
- Invalid orders
- Convoys
- Supports (own/other/hold/attack)
- Bounces
"""

import os
import yaml
import re
from typing import Dict, List
from diplomacy_game_engine.core.map import Power
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
                'bounces': 0
            }
            for power in Power
        }
    
    def analyze_all_orders(self) -> Dict[str, Dict[str, int]]:
        """
        Analyze all order files in the game.
        
        Returns:
            Dict mapping power name to precision counts
        """
        if not os.path.exists(self.orders_folder):
            logger.warning("No orders folder found")
            return self.precision_counts
        
        # Get all order files
        order_files = sorted([f for f in os.listdir(self.orders_folder) if f.endswith('.yaml')])
        
        for filename in order_files:
            filepath = os.path.join(self.orders_folder, filename)
            self._analyze_order_file(filepath)
        
        # Extract invalid orders from summaries
        self._extract_invalid_orders_from_summaries()
        
        # Extract bounces from summaries
        self._extract_bounces_from_summaries()
        
        logger.info("Order analysis complete")
        return self.precision_counts
    
    def _analyze_order_file(self, filepath: str):
        """Analyze a single order file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract phase from filename (e.g., "1901_01_spring.yaml" -> "1901_spring")
        filename = os.path.basename(filepath)
        phase_key = self._extract_phase_key(filename)
        
        # Get the state from BEFORE orders execute
        state_key = self._get_state_before_orders(phase_key)
        
        orders = data.get('orders', [])
        
        for order in orders:
            unit = order.get('unit', '')
            action = order.get('action', '')
            
            # Extract power from unit string using the pre-order state
            power_name = self._get_power_from_unit(unit, state_key)
            
            # Handle convoy orders specially (search all states)
            if action == 'convoy':
                # For convoys, search all states to find the unit
                power_name = self._get_power_from_unit(unit, None)
                
                if power_name:
                    self.precision_counts[power_name]['convoys'] += 1
                continue
            
            # Skip if we can't determine power for non-convoy orders
            if not power_name:
                continue
            
            # Handle support orders
            if action == 'support':
                # Determine support type
                target_unit = order.get('supporting', '')
                target_power = self._get_power_from_unit(target_unit, phase_key)
                
                # Count own vs other
                if target_power == power_name:
                    self.precision_counts[power_name]['support_own'] += 1
                elif target_power:
                    self.precision_counts[power_name]['support_other'] += 1
                
                # Differentiate hold vs attack support
                # If there's a destination, it's supporting an attack
                # If no destination, it's supporting a hold
                if 'destination' in order and order['destination']:
                    self.precision_counts[power_name]['support_attack'] += 1
                else:
                    self.precision_counts[power_name]['support_hold'] += 1
    
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
    
    def _extract_invalid_orders_from_summaries(self):
        """Extract invalid order counts from summaries."""
        if not os.path.exists(self.summaries_folder):
            return
        
        summary_files = sorted([f for f in os.listdir(self.summaries_folder) if f.endswith('.md')])
        
        for filename in summary_files:
            filepath = os.path.join(self.summaries_folder, filename)
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
                        self.precision_counts[power_name]['invalid_orders'] += len(matches)
    
    def _extract_bounces_from_summaries(self):
        """Extract bounce counts from summaries."""
        if not os.path.exists(self.summaries_folder):
            return
        
        summary_files = sorted([f for f in os.listdir(self.summaries_folder) if f.endswith('.md')])
        
        for filename in summary_files:
            filepath = os.path.join(self.summaries_folder, filename)
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
                    if matches:
                        self.precision_counts[power_name]['bounces'] += len(matches)
