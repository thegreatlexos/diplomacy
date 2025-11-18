"""
Game state module for Diplomacy game engine.
Represents units, board state, and game progression.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json

from diplomacy_game_engine.core.map import Power, Coast, Map, create_standard_map


class UnitType(Enum):
    """Type of military unit."""
    ARMY = "Army"
    FLEET = "Fleet"


class Season(Enum):
    """Game seasons/phases."""
    SPRING = "Spring"
    FALL = "Fall"
    RETREAT = "Retreat"
    WINTER = "Winter"


@dataclass
class Unit:
    """Represents a military unit on the board."""
    power: Power
    unit_type: UnitType
    location: str  # Province abbreviation
    coast: Optional[Coast] = None  # For fleets on multi-coast provinces
    _id_counter: int = field(default_factory=lambda: Unit._get_next_id(), init=False)
    
    # Class variable to ensure unique IDs
    _next_id = 1
    
    @classmethod
    def _get_next_id(cls) -> int:
        """Get the next unique ID."""
        current_id = cls._next_id
        cls._next_id += 1
        return current_id
    
    def __post_init__(self):
        """Validate unit configuration."""
        if self.unit_type == UnitType.ARMY and self.coast is not None:
            raise ValueError("Armies cannot have a coast specification")
    
    def get_id(self) -> str:
        """Generate a unique identifier for this unit."""
        coast_str = f"_{self.coast.value}" if self.coast else ""
        return f"{self.power.value}_{self.unit_type.value[0]}_{self.location}{coast_str}_{self._id_counter}"
    
    def __eq__(self, other) -> bool:
        """Check equality based on power, unit_type, location, and coast (excluding _id_counter)."""
        if not isinstance(other, Unit):
            return False
        return (self.power == other.power and 
                self.unit_type == other.unit_type and 
                self.location == other.location and 
                self.coast == other.coast)
    
    def __hash__(self) -> int:
        """Hash based on power, unit_type, location, and coast (excluding _id_counter)."""
        return hash((self.power, self.unit_type, self.location, self.coast))
    
    def __repr__(self) -> str:
        coast_str = f"({self.coast.value})" if self.coast else ""
        return f"{self.unit_type.value[0]} {self.location}{coast_str}"
    
    def to_dict(self) -> dict:
        """Convert unit to dictionary for serialization."""
        return {
            "power": self.power.value,
            "unit_type": self.unit_type.value,
            "location": self.location,
            "coast": self.coast.value if self.coast else None
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Unit':
        """Create unit from dictionary."""
        return Unit(
            power=Power(data["power"]),
            unit_type=UnitType(data["unit_type"]),
            location=data["location"],
            coast=Coast(data["coast"]) if data.get("coast") else None
        )


@dataclass
class DislodgedUnit:
    """Represents a unit that has been dislodged and needs to retreat."""
    unit: Unit
    dislodged_from: str  # Province abbreviation
    dislodger_origin: str  # Where the dislodging unit came from
    contested_provinces: Set[str] = field(default_factory=set)  # Provinces with bounces
    
    def get_valid_retreat_destinations(self, game_map: Map, game_state: 'GameState' = None) -> set:
        """
        Get valid provinces this unit can retreat to.
        Cannot retreat to:
        - The province the dislodger came from
        - Any contested (bounced) province
        - Any occupied province
        """
        adjacent = game_map.get_adjacent_provinces(self.dislodged_from, self.unit.coast)
        valid = set()
        
        for adj_prov in adjacent:
            # Check if this is a valid retreat destination
            if adj_prov == self.dislodger_origin:
                continue
            if adj_prov in self.contested_provinces:
                continue
            
            province = game_map.get_province(adj_prov)
            if province is None:
                continue
            
            # Check unit type compatibility
            if self.unit.unit_type == UnitType.ARMY and province.is_sea():
                continue
            if self.unit.unit_type == UnitType.FLEET and province.is_land():
                continue
            
            # Check if province is occupied (if game_state provided)
            if game_state and game_state.get_unit_at(adj_prov) is not None:
                continue
            
            valid.add(adj_prov)
        
        return valid
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "unit": self.unit.to_dict(),
            "dislodged_from": self.dislodged_from,
            "dislodger_origin": self.dislodger_origin,
            "contested_provinces": list(self.contested_provinces)
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'DislodgedUnit':
        """Create from dictionary."""
        return DislodgedUnit(
            unit=Unit.from_dict(data["unit"]),
            dislodged_from=data["dislodged_from"],
            dislodger_origin=data["dislodger_origin"],
            contested_provinces=set(data.get("contested_provinces", []))
        )


class GameState:
    """Represents the complete state of the game at a point in time."""
    
    def __init__(
        self,
        game_map: Map,
        year: int = 1901,
        season: Season = Season.SPRING
    ):
        self.game_map = game_map
        self.year = year
        self.season = season
        self.units: Dict[str, Unit] = {}  # Keyed by unit ID
        self.supply_centers: Dict[str, Power] = {}  # Province abbr -> Power
        self.dislodged_units: List[DislodgedUnit] = []
        self.previous_season: Optional[Season] = None  # Track season before retreat
    
    def add_unit(self, unit: Unit) -> None:
        """Add a unit to the game state."""
        unit_id = unit.get_id()
        self.units[unit_id] = unit
    
    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        """Remove a unit from the game state."""
        return self.units.pop(unit_id, None)
    
    def get_unit_at(self, location: str, coast: Optional[Coast] = None) -> Optional[Unit]:
        """Get the unit at a specific location."""
        for unit in self.units.values():
            if unit.location == location:
                if coast is None or unit.coast == coast:
                    return unit
        return None
    
    def get_units_by_power(self, power: Power) -> List[Unit]:
        """Get all units belonging to a specific power."""
        return [unit for unit in self.units.values() if unit.power == power]
    
    def get_sc_count(self, power: Power) -> int:
        """Get the number of supply centers controlled by a power."""
        return sum(1 for p in self.supply_centers.values() if p == power)
    
    def get_unit_count(self, power: Power) -> int:
        """Get the number of units controlled by a power."""
        return len(self.get_units_by_power(power))
    
    def set_sc_owner(self, province_abbr: str, power: Optional[Power]) -> None:
        """Set the owner of a supply center."""
        if power is None:
            self.supply_centers.pop(province_abbr, None)
        else:
            self.supply_centers[province_abbr] = power
    
    def check_victory(self) -> Optional[Power]:
        """Check if any power has achieved victory (18 SCs)."""
        for power in Power:
            if self.get_sc_count(power) >= 18:
                return power
        return None
    
    def advance_phase(self) -> None:
        """Advance to the next phase of the game."""
        if self.season == Season.SPRING:
            # Spring Movement -> Retreat (if dislodged units) or Fall Movement
            if self.dislodged_units:
                self.season = Season.RETREAT
            else:
                self.season = Season.FALL
        elif self.season == Season.RETREAT:
            # Retreat -> Fall Movement or Winter (depending on what phase we came from)
            # For simplicity, assume retreat after spring goes to fall, after fall goes to winter
            # In a full implementation, we'd track the previous phase
            if hasattr(self, '_retreat_from_spring'):
                self.season = Season.FALL
                delattr(self, '_retreat_from_spring')
            else:
                self.season = Season.WINTER
        elif self.season == Season.FALL:
            # Fall Movement -> Retreat (if dislodged units) or Winter Adjustments
            if self.dislodged_units:
                self.season = Season.RETREAT
            else:
                self.season = Season.WINTER
        elif self.season == Season.WINTER:
            # Winter Adjustments -> Spring Movement of next year
            self.season = Season.SPRING
            self.year += 1
        
        # Clear dislodged units when advancing from retreat phase
        if self.season != Season.RETREAT:
            self.dislodged_units.clear()
    
    def clone(self) -> 'GameState':
        """Create a deep copy of this game state."""
        new_state = GameState(self.game_map, self.year, self.season)
        
        # Copy units - preserve original IDs
        for unit_id, unit in self.units.items():
            new_unit = Unit(unit.power, unit.unit_type, unit.location, unit.coast)
            # Preserve the original ID by setting the internal counter
            new_unit._id_counter = unit._id_counter
            new_state.units[unit_id] = new_unit
        
        # Copy supply centers
        new_state.supply_centers = self.supply_centers.copy()
        
        # Copy dislodged units
        new_state.dislodged_units = [
            DislodgedUnit(
                Unit(du.unit.power, du.unit.unit_type, du.unit.location, du.unit.coast),
                du.dislodged_from,
                du.dislodger_origin,
                du.contested_provinces.copy()
            )
            for du in self.dislodged_units
        ]
        
        return new_state
    
    def to_dict(self) -> dict:
        """Convert game state to dictionary for serialization."""
        return {
            "year": self.year,
            "season": self.season.value,
            "previous_season": self.previous_season.value if self.previous_season else None,
            "units": [unit.to_dict() for unit in self.units.values()],
            "supply_centers": {
                abbr: power.value for abbr, power in self.supply_centers.items()
            },
            "dislodged_units": [du.to_dict() for du in self.dislodged_units]
        }
    
    def to_json(self, filepath: str) -> None:
        """Save game state to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @staticmethod
    def from_dict(data: dict, game_map: Map) -> 'GameState':
        """Create game state from dictionary."""
        state = GameState(
            game_map=game_map,
            year=data["year"],
            season=Season(data["season"])
        )
        
        # Load previous_season if present
        if data.get("previous_season"):
            state.previous_season = Season(data["previous_season"])
        
        # Load units
        for unit_data in data["units"]:
            unit = Unit.from_dict(unit_data)
            state.add_unit(unit)
        
        # Load supply centers
        for abbr, power_str in data["supply_centers"].items():
            state.supply_centers[abbr] = Power(power_str)
        
        # Load dislodged units
        for du_data in data.get("dislodged_units", []):
            state.dislodged_units.append(DislodgedUnit.from_dict(du_data))
        
        return state
    
    @staticmethod
    def from_json(filepath: str, game_map: Map) -> 'GameState':
        """Load game state from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return GameState.from_dict(data, game_map)


def create_starting_state() -> GameState:
    """Create the standard 1901 starting game state."""
    game_map = create_standard_map()
    state = GameState(game_map, year=1901, season=Season.SPRING)
    
    # Define starting units for each power
    starting_units = [
        # England
        (Power.ENGLAND, UnitType.FLEET, "Lon", None),
        (Power.ENGLAND, UnitType.FLEET, "Edi", None),
        (Power.ENGLAND, UnitType.ARMY, "Lvp", None),
        
        # France
        (Power.FRANCE, UnitType.ARMY, "Par", None),
        (Power.FRANCE, UnitType.ARMY, "Mar", None),
        (Power.FRANCE, UnitType.FLEET, "Bre", None),
        
        # Germany
        (Power.GERMANY, UnitType.ARMY, "Ber", None),
        (Power.GERMANY, UnitType.ARMY, "Mun", None),
        (Power.GERMANY, UnitType.FLEET, "Kie", None),
        
        # Italy
        (Power.ITALY, UnitType.ARMY, "Rom", None),
        (Power.ITALY, UnitType.ARMY, "Ven", None),
        (Power.ITALY, UnitType.FLEET, "Nap", None),
        
        # Austria-Hungary
        (Power.AUSTRIA, UnitType.ARMY, "Vie", None),
        (Power.AUSTRIA, UnitType.ARMY, "Bud", None),
        (Power.AUSTRIA, UnitType.FLEET, "Tri", None),
        
        # Russia
        (Power.RUSSIA, UnitType.ARMY, "Mos", None),
        (Power.RUSSIA, UnitType.FLEET, "Sev", None),
        (Power.RUSSIA, UnitType.ARMY, "War", None),
        (Power.RUSSIA, UnitType.FLEET, "StP", Coast.SOUTH),
        
        # Turkey
        (Power.TURKEY, UnitType.ARMY, "Con", None),
        (Power.TURKEY, UnitType.ARMY, "Smy", None),
        (Power.TURKEY, UnitType.FLEET, "Ank", None),
    ]
    
    # Add all starting units
    for power, unit_type, location, coast in starting_units:
        unit = Unit(power, unit_type, location, coast)
        state.add_unit(unit)
    
    # Set initial supply center ownership
    for power in Power:
        home_centers = game_map.get_home_centers(power)
        for province in home_centers:
            state.set_sc_owner(province.abbreviation, power)
    
    return state
