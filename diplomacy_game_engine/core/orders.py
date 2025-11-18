"""
Order system for Diplomacy game engine.
Defines order types and parsing logic.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass

from diplomacy_game_engine.core.map import Coast, Power, Map
from diplomacy_game_engine.core.game_state import Unit, UnitType, GameState


class Order(ABC):
    """Base class for all order types."""
    
    def __init__(self, unit: Unit):
        self.unit = unit
    
    @abstractmethod
    def is_valid(self, game_state: GameState) -> bool:
        """Check if this order is valid given the current game state."""
        pass
    
    @abstractmethod
    def to_string(self) -> str:
        """Convert order to string representation."""
        pass
    
    def __repr__(self) -> str:
        return self.to_string()


class HoldOrder(Order):
    """Order for a unit to hold its current position."""
    
    def is_valid(self, game_state: GameState) -> bool:
        """Hold orders are always valid."""
        return True
    
    def to_string(self) -> str:
        return f"{self.unit} H"


class MoveOrder(Order):
    """Order for a unit to move to an adjacent province."""
    
    def __init__(
        self,
        unit: Unit,
        destination: str,
        dest_coast: Optional[Coast] = None,
        via_convoy: bool = False
    ):
        super().__init__(unit)
        self.destination = destination
        self.dest_coast = dest_coast
        self.via_convoy = via_convoy
    
    def is_valid(self, game_state: GameState) -> bool:
        """
        Check if move is valid:
        - Destination must be adjacent (or convoy route exists)
        - Unit type must be compatible with destination
        - Coast specifications must be valid
        """
        game_map = game_state.game_map
        dest_province = game_map.get_province(self.destination)
        
        if dest_province is None:
            return False
        
        # Check unit type compatibility
        if self.unit.unit_type == UnitType.ARMY:
            if dest_province.is_sea() and not self.via_convoy:
                return False
        elif self.unit.unit_type == UnitType.FLEET:
            # Fleets can only move to sea provinces, not to any land-based province
            if not dest_province.is_sea():
                return False
        
        # If not via convoy, check adjacency
        if not self.via_convoy:
            if not game_map.is_adjacent(
                self.unit.location,
                self.destination,
                self.unit.coast,
                self.dest_coast
            ):
                return False
        
        return True
    
    def to_string(self) -> str:
        coast_str = f" ({self.dest_coast.value})" if self.dest_coast else ""
        convoy_str = " via convoy" if self.via_convoy else ""
        return f"{self.unit} -> {self.destination}{coast_str}{convoy_str}"


class SupportOrder(Order):
    """Order for a unit to support another unit's action."""
    
    def __init__(
        self,
        unit: Unit,
        supported_unit_location: str,
        supported_unit_coast: Optional[Coast],
        destination: Optional[str] = None,
        dest_coast: Optional[Coast] = None
    ):
        super().__init__(unit)
        self.supported_unit_location = supported_unit_location
        self.supported_unit_coast = supported_unit_coast
        self.destination = destination  # None means support to hold
        self.dest_coast = dest_coast
    
    def is_support_hold(self) -> bool:
        """Check if this is a support hold order."""
        return self.destination is None
    
    def is_valid(self, game_state: GameState) -> bool:
        """
        Check if support is valid:
        - Supporting unit must be adjacent to the destination (or supported location for hold)
        - Cannot support own unit being dislodged
        """
        game_map = game_state.game_map
        
        # Check if supported unit exists
        supported_unit = game_state.get_unit_at(
            self.supported_unit_location,
            self.supported_unit_coast
        )
        if supported_unit is None:
            return False
        
        # Cannot support dislodging own unit
        if self.destination and supported_unit.power == self.unit.power:
            dest_unit = game_state.get_unit_at(self.destination, self.dest_coast)
            if dest_unit and dest_unit.power == self.unit.power:
                return False
        
        # Check adjacency
        target = self.destination if self.destination else self.supported_unit_location
        target_coast = self.dest_coast if self.destination else self.supported_unit_coast
        
        if not game_map.is_adjacent(self.unit.location, target, self.unit.coast, target_coast):
            return False
        
        return True
    
    def to_string(self) -> str:
        if self.is_support_hold():
            coast_str = f" ({self.supported_unit_coast.value})" if self.supported_unit_coast else ""
            return f"{self.unit} S {self.supported_unit_location}{coast_str}"
        else:
            dest_coast_str = f" ({self.dest_coast.value})" if self.dest_coast else ""
            return f"{self.unit} S {self.supported_unit_location} -> {self.destination}{dest_coast_str}"


class ConvoyOrder(Order):
    """Order for a fleet to convoy an army across water."""
    
    def __init__(
        self,
        unit: Unit,
        convoyed_army_location: str,
        destination: str
    ):
        super().__init__(unit)
        self.convoyed_army_location = convoyed_army_location
        self.destination = destination
    
    def is_valid(self, game_state: GameState) -> bool:
        """
        Check if convoy is valid:
        - Convoying unit must be a fleet in a sea province
        - Convoyed unit must be an army
        """
        game_map = game_state.game_map
        
        # Convoying unit must be a fleet
        if self.unit.unit_type != UnitType.FLEET:
            return False
        
        # Fleet must be in a sea province
        fleet_province = game_map.get_province(self.unit.location)
        if fleet_province is None or not fleet_province.is_sea():
            return False
        
        # Check if army exists
        army = game_state.get_unit_at(self.convoyed_army_location)
        if army is None or army.unit_type != UnitType.ARMY:
            return False
        
        return True
    
    def to_string(self) -> str:
        return f"{self.unit} C {self.convoyed_army_location} -> {self.destination}"


class RetreatOrder(Order):
    """Order for a dislodged unit to retreat."""
    
    def __init__(self, unit: Unit, destination: str, dest_coast: Optional[Coast] = None):
        super().__init__(unit)
        self.destination = destination
        self.dest_coast = dest_coast
    
    def is_valid(self, game_state: GameState) -> bool:
        """Check if retreat destination is valid."""
        # This will be validated by the DislodgedUnit.get_valid_retreat_destinations method
        return True
    
    def to_string(self) -> str:
        coast_str = f" ({self.dest_coast.value})" if self.dest_coast else ""
        return f"{self.unit} R {self.destination}{coast_str}"


class DisbandOrder(Order):
    """Order to disband a unit (used in retreat or winter phases)."""
    
    def is_valid(self, game_state: GameState) -> bool:
        """Disband orders are always valid."""
        return True
    
    def to_string(self) -> str:
        return f"{self.unit} D"


class BuildOrder:
    """Order to build a new unit (winter phase only)."""
    
    def __init__(
        self,
        power: Power,
        unit_type: UnitType,
        location: str,
        coast: Optional[Coast] = None
    ):
        self.power = power
        self.unit_type = unit_type
        self.location = location
        self.coast = coast
    
    def is_valid(self, game_state: GameState) -> bool:
        """
        Check if build is valid:
        - Location must be a home supply center
        - Location must be vacant
        - Power must control the location
        - Power must have fewer units than supply centers
        """
        game_map = game_state.game_map
        province = game_map.get_province(self.location)
        
        if province is None:
            return False
        
        # Must be a home center of this power
        if province.home_center_of != self.power:
            return False
        
        # Must be vacant
        if game_state.get_unit_at(self.location, self.coast) is not None:
            return False
        
        # Power must control it
        if game_state.supply_centers.get(self.location) != self.power:
            return False
        
        # Power must have fewer units than SCs
        if game_state.get_unit_count(self.power) >= game_state.get_sc_count(self.power):
            return False
        
        return True
    
    def to_string(self) -> str:
        coast_str = f" ({self.coast.value})" if self.coast else ""
        return f"Build {self.unit_type.value[0]} {self.location}{coast_str}"
    
    def __repr__(self) -> str:
        return self.to_string()


class OrderParser:
    """Parse order strings into Order objects."""
    
    @staticmethod
    def parse_order(order_str: str, game_state: GameState) -> Optional[Order]:
        """
        Parse an order string into an Order object.
        
        Format examples:
        - "A Par H" - Army Paris holds
        - "F Lon-NTH" - Fleet London to North Sea
        - "A Par-Bur" - Army Paris to Burgundy
        - "A Par - Bur" - Army Paris to Burgundy (with spaces)
        - "F Bre S A Par-Pic" - Fleet Brest supports Army Paris to Picardy
        - "F Bre S A Par" - Fleet Brest supports Army Paris (hold)
        - "F NTH C A Lon-Bel" - Fleet North Sea convoys Army London to Belgium
        - "A Lon-Bel via convoy" - Army London to Belgium via convoy
        """
        # Clean up the order string and split
        order_str = order_str.strip()
        parts = order_str.split()
        
        if len(parts) < 2:
            return None
        
        # Parse unit type and location
        unit_type_str = parts[0].upper()
        location_part = parts[1]
        
        # Check if location contains a dash (e.g., "Par-Bur")
        actual_location = location_part
        destination = None
        
        if "-" in location_part:
            actual_location, destination = location_part.split("-", 1)
            destination = destination.strip()
        
        # Find the unit
        unit = None
        for u in game_state.units.values():
            if u.location == actual_location:
                if (unit_type_str == "A" and u.unit_type == UnitType.ARMY) or \
                   (unit_type_str == "F" and u.unit_type == UnitType.FLEET):
                    unit = u
                    break
        
        if unit is None:
            return None
        
        # If we found a destination in the location part, it's a move order
        if destination:
            via_convoy = "convoy" in order_str.lower()
            return MoveOrder(unit, destination, via_convoy=via_convoy)
        
        # Handle case where there are only 2 parts (unit and location) - default to hold
        if len(parts) == 2:
            return HoldOrder(unit)
        
        # Handle explicit hold orders
        if len(parts) == 3 and parts[2].upper() == "H":
            return HoldOrder(unit)
        
        # Handle alternative move format: "A Par - Bur"
        if len(parts) >= 4 and parts[2] == "-":
            destination = parts[3]
            via_convoy = "convoy" in order_str.lower()
            return MoveOrder(unit, destination, via_convoy=via_convoy)
        
        # Handle other order types
        if len(parts) >= 3:
            order_type = parts[2].upper()
            
            if order_type == "H":
                return HoldOrder(unit)
            
            elif order_type == "S":
                # Support order
                if len(parts) < 5:  # Need at least "F Bre S A Par"
                    return None
                
                # Skip the unit type of supported unit (parts[3] should be "A" or "F")
                supported_location_part = parts[4]
                
                # Check if it's support hold or support move
                if "-" in supported_location_part:
                    # Format: "F Bre S A Par-Bur"
                    supported_loc, dest = supported_location_part.split("-", 1)
                    return SupportOrder(unit, supported_loc, None, dest.strip())
                elif len(parts) >= 7 and parts[5] == "-":
                    # Format: "F Bre S A Par - Bur"
                    supported_loc = supported_location_part
                    dest = parts[6]
                    return SupportOrder(unit, supported_loc, None, dest)
                else:
                    # Support hold: "F Bre S A Par"
                    return SupportOrder(unit, supported_location_part, None)
            
            elif order_type == "C":
                # Convoy order: "F NTH C A Lon-Bel" or "F NTH C A Lon - Bel"
                if len(parts) < 6:
                    return None
                
                # Skip the unit type of convoyed unit (parts[3] should be "A")
                army_location_part = parts[4]
                
                if "-" in army_location_part:
                    # Format: "F NTH C A Lon-Bel"
                    army_loc, dest = army_location_part.split("-", 1)
                    return ConvoyOrder(unit, army_loc, dest.strip())
                elif len(parts) >= 7 and parts[5] == "-":
                    # Format: "F NTH C A Lon - Bel"
                    army_loc = army_location_part
                    dest = parts[6]
                    return ConvoyOrder(unit, army_loc, dest)
        
        return None


class OrderSet:
    """Collection of orders for a single turn."""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}  # unit_id -> Order
    
    def add_order(self, unit_id: str, order: Order) -> None:
        """Add an order for a unit."""
        self.orders[unit_id] = order
    
    def get_order(self, unit_id: str) -> Optional[Order]:
        """Get the order for a unit, or None if holding."""
        return self.orders.get(unit_id)
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders."""
        return list(self.orders.values())
    
    def validate_all(self, game_state: GameState) -> Dict[str, bool]:
        """Validate all orders and return results."""
        results = {}
        for unit_id, order in self.orders.items():
            results[unit_id] = order.is_valid(game_state)
        return results
