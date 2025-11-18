"""
YAML order file loader for Diplomacy game engine.
Supports structured YAML format with validation and auto-correction.
"""

import yaml
from typing import Dict, List, Optional, Tuple
from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType
from diplomacy_game_engine.core.orders import (
    Order, HoldOrder, MoveOrder, SupportOrder, ConvoyOrder,
    RetreatOrder, DisbandOrder, BuildOrder
)
from diplomacy_game_engine.core.map import Power, Coast


class OrderValidationError(Exception):
    """Raised when an order cannot be validated or corrected."""
    pass


class YAMLOrderLoader:
    """Loads and validates orders from YAML files."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.warnings = []
        self.corrections = []
    
    def load_from_file(self, filepath: str) -> Dict:
        """Load YAML order file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return data
    
    def parse_orders(self, yaml_data: Dict) -> Dict[str, Order]:
        """
        Parse orders from YAML data into Order objects.
        Returns dict of unit_id -> Order
        """
        orders = {}
        
        if 'orders' not in yaml_data:
            return orders
        
        for order_data in yaml_data['orders']:
            try:
                order = self._parse_single_order(order_data)
                if order:
                    orders[order.unit.get_id()] = order
            except Exception as e:
                self.warnings.append(f"Failed to parse order {order_data}: {e}")
        
        return orders
    
    def _parse_single_order(self, order_data: Dict) -> Optional[Order]:
        """Parse a single order from YAML data."""
        # Get unit specification
        unit_spec = order_data.get('unit', '').strip()
        if not unit_spec:
            raise OrderValidationError("Missing unit specification")
        
        # Parse unit (e.g., "F Lon" or "A Par")
        unit = self._find_unit(unit_spec)
        if not unit:
            self.warnings.append(f"Unit not found: {unit_spec}")
            return None
        
        # Get action
        action = order_data.get('action', '').lower().strip()
        action = self._normalize_action(action)
        
        # Create appropriate order based on action
        if action == 'hold':
            return HoldOrder(unit)
        
        elif action == 'move':
            dest_str = order_data.get('destination', '')
            if not dest_str:
                raise OrderValidationError(f"Missing destination for move order")
            
            # Check if destination has coast notation (e.g., "Spa/sc")
            dest_coast = self._parse_coast(order_data.get('coast'))
            if '/' in dest_str:
                parts = dest_str.split('/')
                dest = self._normalize_province(parts[0])
                # Parse coast from destination string
                coast_from_dest = self._parse_coast(parts[1])
                if coast_from_dest:
                    dest_coast = coast_from_dest
            else:
                dest = self._normalize_province(dest_str)
            
            if not dest:
                raise OrderValidationError(f"Missing destination for move order")
            
            via_convoy = order_data.get('via_convoy', False)
            
            return MoveOrder(unit, dest, dest_coast, via_convoy)
        
        elif action == 'support':
            # Accept both 'supports' and 'supporting' field names
            supported_unit_spec = order_data.get('supports', '') or order_data.get('supporting', '')
            supported_unit = self._find_unit(supported_unit_spec)
            
            if not supported_unit:
                self.warnings.append(f"Supported unit not found: {supported_unit_spec}")
                return None
            
            destination = order_data.get('destination')
            if destination:
                # Support move
                dest = self._normalize_province(destination)
                dest_coast = self._parse_coast(order_data.get('coast'))
                return SupportOrder(unit, supported_unit.location, supported_unit.coast, dest, dest_coast)
            else:
                # Support hold
                return SupportOrder(unit, supported_unit.location, supported_unit.coast)
        
        elif action == 'convoy':
            # Support 'convoys', 'convoying', and 'convoy' field names for flexibility
            convoyed_spec = order_data.get('convoys', '') or order_data.get('convoying', '') or order_data.get('convoy', '')
            convoyed_unit = self._find_unit(convoyed_spec)
            
            if not convoyed_unit:
                self.warnings.append(f"Convoyed unit not found: {convoyed_spec}")
                return None
            
            dest = self._normalize_province(order_data.get('destination', ''))
            if not dest:
                raise OrderValidationError(f"Missing destination for convoy order")
            
            return ConvoyOrder(unit, convoyed_unit.location, dest)
        
        else:
            self.warnings.append(f"Unknown action: {action}")
            return None
    
    def _find_unit(self, unit_spec: str) -> Optional[Unit]:
        """
        Find a unit from specification like "F Lon" or "A Par" or "F Spa/sc".
        Auto-corrects case and expands province names.
        """
        parts = unit_spec.strip().split()
        if len(parts) < 2:
            return None
        
        # Parse unit type
        unit_type_str = parts[0].upper()
        if unit_type_str == 'A':
            unit_type = UnitType.ARMY
        elif unit_type_str == 'F':
            unit_type = UnitType.FLEET
        else:
            return None
        
        # Parse location (may include coast like "Spa/sc")
        location_str = ' '.join(parts[1:])
        location = self._normalize_province(location_str)
        if not location:
            return None
        
        # Check if location has coast notation
        coast = None
        if '/' in location:
            loc_parts = location.split('/')
            location = loc_parts[0]
            coast = self._parse_coast(loc_parts[1])
        
        # Find unit at location (with optional coast match)
        for unit in self.game_state.units.values():
            if unit.location == location and unit.unit_type == unit_type:
                # If coast was specified, match it; otherwise any coast is fine
                if coast is None or unit.coast == coast:
                    return unit
        
        return None
    
    def _normalize_province(self, province: str) -> Optional[str]:
        """
        Normalize province name to standard abbreviation.
        Auto-corrects case and expands full names.
        Handles coast notation (e.g., "Spa/sc").
        """
        if not province:
            return None
        
        province = province.strip()
        
        # Check if province has coast notation (e.g., "Spa/sc")
        if '/' in province:
            # Return as-is with uppercase province part
            parts = province.split('/')
            if len(parts) == 2:
                prov_part = parts[0].strip()
                coast = parts[1].strip().lower()
                
                # Normalize the province part first (handle both 3-letter and full names)
                if len(prov_part) == 3:
                    # Try to find province with case-insensitive match
                    prov_abbr = None
                    for prov in self.game_state.game_map.get_all_provinces():
                        if prov.abbreviation.lower() == prov_part.lower():
                            prov_abbr = prov.abbreviation
                            break
                    if not prov_abbr:
                        return None
                else:
                    # Try to match full province name
                    prov_lower = prov_part.lower()
                    prov_abbr = None
                    for prov in self.game_state.game_map.get_all_provinces():
                        if prov.name.lower() == prov_lower:
                            prov_abbr = prov.abbreviation
                            break
                    if not prov_abbr:
                        return None
                
                # Province abbreviation is now correct, return with coast
                return f"{prov_abbr}/{coast}"
            return None
        
        # If already 3-letter abbreviation, just uppercase it
        if len(province) == 3:
            normalized = province.upper()
            # Verify it exists
            if self.game_state.game_map.get_province(normalized):
                if province != normalized:
                    self.corrections.append(f"Corrected '{province}' to '{normalized}'")
                return normalized
        
        # Try to match full province name
        province_lower = province.lower()
        for prov in self.game_state.game_map.get_all_provinces():
            if prov.name.lower() == province_lower:
                self.corrections.append(f"Expanded '{province}' to '{prov.abbreviation}'")
                return prov.abbreviation
        
        return None
    
    def _normalize_action(self, action: str) -> str:
        """Normalize action name with aliases."""
        action = action.lower().strip()
        
        # Action aliases
        aliases = {
            'm': 'move',
            'h': 'hold',
            's': 'support',
            'c': 'convoy',
            'r': 'retreat',
            'd': 'disband',
            'b': 'build'
        }
        
        if action in aliases:
            normalized = aliases[action]
            self.corrections.append(f"Expanded action '{action}' to '{normalized}'")
            return normalized
        
        return action
    
    def _parse_coast(self, coast_str: Optional[str]) -> Optional[Coast]:
        """Parse coast specification."""
        if not coast_str:
            return None
        
        coast_str = coast_str.lower().strip()
        
        if coast_str in ['nc', 'north']:
            return Coast.NORTH
        elif coast_str in ['sc', 'south']:
            return Coast.SOUTH
        elif coast_str in ['ec', 'east']:
            return Coast.EAST
        elif coast_str in ['wc', 'west']:
            return Coast.WEST
        
        return None
    
    def parse_retreats(self, yaml_data: Dict) -> Dict[str, Order]:
        """Parse retreat orders from YAML data."""
        retreats = {}
        
        if 'retreats' not in yaml_data:
            return retreats
        
        for retreat_data in yaml_data['retreats']:
            try:
                unit_spec = retreat_data.get('unit', '')
                unit = self._find_unit(unit_spec)
                
                if not unit:
                    self.warnings.append(f"Unit not found for retreat: {unit_spec}")
                    continue
                
                action = retreat_data.get('action', 'retreat').lower()
                
                if action == 'disband':
                    retreats[unit.get_id()] = DisbandOrder(unit)
                else:
                    dest = self._normalize_province(retreat_data.get('destination', ''))
                    if dest:
                        retreats[unit.get_id()] = RetreatOrder(unit, dest)
            except Exception as e:
                self.warnings.append(f"Failed to parse retreat {retreat_data}: {e}")
        
        return retreats
    
    def parse_builds(self, yaml_data: Dict) -> Dict[str, List[BuildOrder]]:
        """Parse build orders from YAML data."""
        builds = {}
        
        if 'builds' not in yaml_data:
            return builds
        
        for build_data in yaml_data['builds']:
            try:
                power_str = build_data.get('power', '')
                power = Power(power_str)
                
                unit_type_str = build_data.get('unit_type', '').lower()
                unit_type = UnitType.ARMY if unit_type_str == 'army' else UnitType.FLEET
                
                location = self._normalize_province(build_data.get('location', ''))
                coast = self._parse_coast(build_data.get('coast'))
                
                if location:
                    build_order = BuildOrder(power, unit_type, location, coast)
                    
                    if power.value not in builds:
                        builds[power.value] = []
                    builds[power.value].append(build_order)
            except Exception as e:
                self.warnings.append(f"Failed to parse build {build_data}: {e}")
        
        return builds
    
    def parse_disbands(self, yaml_data: Dict) -> Dict[str, str]:
        """
        Parse disband orders from YAML data.
        Returns dict of power -> unit_id to disband
        """
        disbands = {}
        
        if 'disbands' not in yaml_data:
            return disbands
        
        for disband_data in yaml_data['disbands']:
            try:
                power_str = disband_data.get('power', '')
                power = Power(power_str)
                
                unit_spec = disband_data.get('unit', '')
                unit = self._find_unit(unit_spec)
                
                if unit:
                    if power.value not in disbands:
                        disbands[power.value] = []
                    disbands[power.value].append(unit.get_id())
                else:
                    self.warnings.append(f"Unit not found for disband: {unit_spec}")
            except Exception as e:
                self.warnings.append(f"Failed to parse disband {disband_data}: {e}")
        
        return disbands
    
    def get_warnings(self) -> List[str]:
        """Get all warnings from parsing."""
        return self.warnings
    
    def get_corrections(self) -> List[str]:
        """Get all auto-corrections made."""
        return self.corrections
