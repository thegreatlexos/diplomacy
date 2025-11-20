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
        
        logger.info("Order analysis complete")
        return self.precision_counts
    
    def _analyze_order_file(self, filepath: str):
        """Analyze a single order file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        orders = data.get('orders', [])
        
        for order in orders:
            unit = order.get('unit', '')
            action = order.get('action', '')
            
            # Extract power from unit string (e.g., "A Lvp" -> England owns Liverpool)
            power_name = self._get_power_from_unit(unit)
            if not power_name:
                continue
            
            # Count order types
            if action == 'convoy':
                self.precision_counts[power_name]['convoys'] += 1
            
            elif action == 'support':
                # Determine support type
                target_unit = order.get('supporting', '')
                target_power = self._get_power_from_unit(target_unit)
                
                if target_power == power_name:
                    self.precision_counts[power_name]['support_own'] += 1
                elif target_power:
                    self.precision_counts[power_name]['support_other'] += 1
                
                # Check if it's a hold or attack support
                # (This would require more context from resolution)
    
    def _get_power_from_unit(self, unit_str: str) -> str:
        """
        Extract power name from unit string.
        
        This is a simplified version - in reality we'd need to look up
        which power owns each province.
        """
        # For now, return None - we'll need to cross-reference with game state
        # This is a placeholder that needs proper implementation
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
