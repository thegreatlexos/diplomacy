"""
Map module for Diplomacy game engine.
Defines provinces, adjacencies, and the standard 1901 Europe map.
"""

from enum import Enum
from typing import Dict, List, Set, Optional, Tuple


class ProvinceType(Enum):
    """Type of province."""
    LAND = "land"
    SEA = "sea"
    COASTAL = "coastal"


class Power(Enum):
    """The seven great powers."""
    ENGLAND = "England"
    FRANCE = "France"
    GERMANY = "Germany"
    ITALY = "Italy"
    AUSTRIA = "Austria-Hungary"
    RUSSIA = "Russia"
    TURKEY = "Turkey"


class Coast(Enum):
    """Coast specifications for provinces with multiple coasts."""
    NORTH_COAST = "nc"
    SOUTH_COAST = "sc"
    EAST_COAST = "ec"
    WEST_COAST = "wc"
    
    # Keep old names for backward compatibility
    NORTH = "nc"
    SOUTH = "sc"
    EAST = "ec"
    WEST = "wc"


class Province:
    """Represents a single province on the map."""
    
    def __init__(
        self,
        name: str,
        full_name: str = None,
        province_type: ProvinceType = None,
        is_supply_center: bool = False,
        home_center_of: Optional[Power] = None,
        coasts: Optional[List[Coast]] = None
    ):
        # Handle different constructor patterns
        if full_name is not None and province_type is not None:
            # Test pattern: Province("Par", "Paris", ProvinceType.LAND, ...)
            # Tests expect name to be the abbreviation
            self.name = name  # This should be the abbreviation like "Par"
            self.full_name = full_name  # This should be full name like "Paris"
            self.abbreviation = name
        else:
            # Map creation pattern: Province(full_name, abbr, type, ...)
            # Used in create_standard_map where first param is full name
            self.name = full_name or name  # For map creation, use abbreviation as name
            self.full_name = name  # Full name
            self.abbreviation = full_name or name
        
        self.province_type = province_type
        self.is_supply_center = is_supply_center
        self.home_center_of = home_center_of
        self.coasts = coasts or []
    
    def is_land(self) -> bool:
        return self.province_type == ProvinceType.LAND
    
    def is_sea(self) -> bool:
        return self.province_type == ProvinceType.SEA
    
    def is_coastal(self) -> bool:
        return self.province_type == ProvinceType.COASTAL
    
    def has_multiple_coasts(self) -> bool:
        return len(self.coasts) > 0
    
    def is_home_center(self) -> bool:
        """Check if this province is a home supply center."""
        return self.is_supply_center and self.home_center_of is not None
    
    def __repr__(self) -> str:
        return f"Province({self.name}, {self.full_name})"


class Map:
    """The Diplomacy game board with provinces and adjacencies."""
    
    def __init__(self):
        self.provinces: Dict[str, Province] = {}
        self.adjacencies: Dict[str, Dict[str, List[Optional[Coast]]]] = {}
    
    def add_province(self, province: Province) -> None:
        """Add a province to the map."""
        self.provinces[province.abbreviation] = province
        self.adjacencies[province.abbreviation] = {}
    
    def add_adjacency(
        self,
        from_abbr: str,
        to_abbr: str,
        from_coast: Optional[Coast] = None,
        to_coast: Optional[Coast] = None
    ) -> None:
        """
        Add an adjacency between two provinces.
        For provinces with multiple coasts, specify which coasts are adjacent.
        """
        if from_abbr not in self.adjacencies:
            self.adjacencies[from_abbr] = {}
        if to_abbr not in self.adjacencies:
            self.adjacencies[to_abbr] = {}
        
        # Store adjacency with coast information
        if to_abbr not in self.adjacencies[from_abbr]:
            self.adjacencies[from_abbr][to_abbr] = []
        self.adjacencies[from_abbr][to_abbr].append((from_coast, to_coast))
        
        # Add reverse adjacency
        if from_abbr not in self.adjacencies[to_abbr]:
            self.adjacencies[to_abbr][from_abbr] = []
        self.adjacencies[to_abbr][from_abbr].append((to_coast, from_coast))
    
    def is_adjacent(
        self,
        from_abbr: str,
        to_abbr: str,
        from_coast: Optional[Coast] = None,
        to_coast: Optional[Coast] = None
    ) -> bool:
        """Check if two provinces are adjacent, considering coasts if specified."""
        if from_abbr not in self.adjacencies:
            return False
        if to_abbr not in self.adjacencies[from_abbr]:
            return False
        
        adjacency_list = self.adjacencies[from_abbr][to_abbr]
        
        # If no coasts specified, just check if any adjacency exists
        if from_coast is None and to_coast is None:
            return len(adjacency_list) > 0
        
        # Check if the specific coast combination exists
        return (from_coast, to_coast) in adjacency_list
    
    def get_adjacent_provinces(
        self,
        abbr: str,
        from_coast: Optional[Coast] = None
    ) -> List[str]:
        """
        Get all provinces adjacent to the given province.
        Returns list of province abbreviations (simplified for test compatibility).
        """
        if abbr not in self.adjacencies:
            return []
        
        result = []
        for adj_abbr, coast_pairs in self.adjacencies[abbr].items():
            for fc, tc in coast_pairs:
                if from_coast is None or fc == from_coast:
                    if adj_abbr not in result:  # Avoid duplicates
                        result.append(adj_abbr)
        
        return result
    
    def get_adjacent_provinces_with_coasts(
        self,
        abbr: str,
        from_coast: Optional[Coast] = None
    ) -> List[Tuple[str, Optional[Coast]]]:
        """
        Get all provinces adjacent to the given province with coast information.
        Returns list of (province_abbr, coast) tuples.
        """
        if abbr not in self.adjacencies:
            return []
        
        result = []
        for adj_abbr, coast_pairs in self.adjacencies[abbr].items():
            for fc, tc in coast_pairs:
                if from_coast is None or fc == from_coast:
                    result.append((adj_abbr, tc))
        
        return result
    
    def get_province(self, abbr: str) -> Optional[Province]:
        """Get a province by its abbreviation."""
        return self.provinces.get(abbr)
    
    def get_all_provinces(self) -> List[Province]:
        """Get all provinces in the map."""
        return list(self.provinces.values())
    
    def get_supply_centers(self) -> List[Province]:
        """Get all supply center provinces."""
        return [p for p in self.provinces.values() if p.is_supply_center]
    
    def get_home_centers(self, power: Power) -> List[Province]:
        """Get all home supply centers for a given power."""
        return [p for p in self.provinces.values() if p.home_center_of == power]


def create_standard_map() -> Map:
    """Create the standard 1901 Diplomacy map."""
    game_map = Map()
    
    # Define all provinces
    # Format: (name, abbr, type, is_sc, home_of, coasts)
    
    provinces_data = [
        # England
        ("London", "Lon", ProvinceType.COASTAL, True, Power.ENGLAND, []),
        ("Edinburgh", "Edi", ProvinceType.COASTAL, True, Power.ENGLAND, []),
        ("Liverpool", "Lvp", ProvinceType.COASTAL, True, Power.ENGLAND, []),
        ("Wales", "Wal", ProvinceType.COASTAL, False, None, []),
        ("Yorkshire", "Yor", ProvinceType.COASTAL, False, None, []),
        ("Clyde", "Cly", ProvinceType.COASTAL, False, None, []),
        
        # France
        ("Paris", "Par", ProvinceType.LAND, True, Power.FRANCE, []),
        ("Marseilles", "Mar", ProvinceType.COASTAL, True, Power.FRANCE, []),
        ("Brest", "Bre", ProvinceType.COASTAL, True, Power.FRANCE, []),
        ("Burgundy", "Bur", ProvinceType.LAND, False, None, []),
        ("Gascony", "Gas", ProvinceType.COASTAL, False, None, []),
        ("Picardy", "Pic", ProvinceType.COASTAL, False, None, []),
        
        # Germany
        ("Berlin", "Ber", ProvinceType.COASTAL, True, Power.GERMANY, []),
        ("Munich", "Mun", ProvinceType.LAND, True, Power.GERMANY, []),
        ("Kiel", "Kie", ProvinceType.COASTAL, True, Power.GERMANY, []),
        ("Prussia", "Pru", ProvinceType.COASTAL, False, None, []),
        ("Ruhr", "Ruh", ProvinceType.LAND, False, None, []),
        ("Silesia", "Sil", ProvinceType.LAND, False, None, []),
        
        # Italy
        ("Rome", "Rom", ProvinceType.COASTAL, True, Power.ITALY, []),
        ("Venice", "Ven", ProvinceType.COASTAL, True, Power.ITALY, []),
        ("Naples", "Nap", ProvinceType.COASTAL, True, Power.ITALY, []),
        ("Apulia", "Apu", ProvinceType.COASTAL, False, None, []),
        ("Piedmont", "Pie", ProvinceType.COASTAL, False, None, []),
        ("Tuscany", "Tus", ProvinceType.COASTAL, False, None, []),
        
        # Austria-Hungary
        ("Vienna", "Vie", ProvinceType.LAND, True, Power.AUSTRIA, []),
        ("Budapest", "Bud", ProvinceType.LAND, True, Power.AUSTRIA, []),
        ("Trieste", "Tri", ProvinceType.COASTAL, True, Power.AUSTRIA, []),
        ("Bohemia", "Boh", ProvinceType.LAND, False, None, []),
        ("Galicia", "Gal", ProvinceType.LAND, False, None, []),
        ("Tyrolia", "Tyr", ProvinceType.LAND, False, None, []),
        
        # Russia
        ("Moscow", "Mos", ProvinceType.LAND, True, Power.RUSSIA, []),
        ("Sevastopol", "Sev", ProvinceType.COASTAL, True, Power.RUSSIA, []),
        ("Warsaw", "War", ProvinceType.LAND, True, Power.RUSSIA, []),
        ("St Petersburg", "StP", ProvinceType.COASTAL, True, Power.RUSSIA, [Coast.NORTH, Coast.SOUTH]),
        ("Livonia", "Lvn", ProvinceType.COASTAL, False, None, []),
        ("Ukraine", "Ukr", ProvinceType.LAND, False, None, []),
        ("Finland", "Fin", ProvinceType.COASTAL, False, None, []),
        
        # Turkey
        ("Constantinople", "Con", ProvinceType.COASTAL, True, Power.TURKEY, []),
        ("Smyrna", "Smy", ProvinceType.COASTAL, True, Power.TURKEY, []),
        ("Ankara", "Ank", ProvinceType.COASTAL, True, Power.TURKEY, []),
        ("Armenia", "Arm", ProvinceType.COASTAL, False, None, []),
        ("Syria", "Syr", ProvinceType.COASTAL, False, None, []),
        
        # Neutral supply centers
        ("Belgium", "Bel", ProvinceType.COASTAL, True, None, []),
        ("Holland", "Hol", ProvinceType.COASTAL, True, None, []),
        ("Denmark", "Den", ProvinceType.COASTAL, True, None, []),
        ("Sweden", "Swe", ProvinceType.COASTAL, True, None, []),
        ("Norway", "Nwy", ProvinceType.COASTAL, True, None, []),
        ("Spain", "Spa", ProvinceType.COASTAL, True, None, [Coast.NORTH, Coast.SOUTH]),
        ("Portugal", "Por", ProvinceType.COASTAL, True, None, []),
        ("Tunis", "Tun", ProvinceType.COASTAL, True, None, []),
        ("Serbia", "Ser", ProvinceType.LAND, True, None, []),
        ("Bulgaria", "Bul", ProvinceType.COASTAL, True, None, [Coast.EAST, Coast.SOUTH]),
        ("Rumania", "Rum", ProvinceType.COASTAL, True, None, []),
        ("Greece", "Gre", ProvinceType.COASTAL, True, None, []),
        
        # Other land provinces
        ("Albania", "Alb", ProvinceType.COASTAL, False, None, []),
        
        # Sea provinces
        ("North Sea", "NTH", ProvinceType.SEA, False, None, []),
        ("Norwegian Sea", "NWG", ProvinceType.SEA, False, None, []),
        ("Barents Sea", "BAR", ProvinceType.SEA, False, None, []),
        ("English Channel", "ENG", ProvinceType.SEA, False, None, []),
        ("Irish Sea", "IRI", ProvinceType.SEA, False, None, []),
        ("Mid-Atlantic Ocean", "MAO", ProvinceType.SEA, False, None, []),
        ("North Atlantic Ocean", "NAO", ProvinceType.SEA, False, None, []),
        ("Heligoland Bight", "HEL", ProvinceType.SEA, False, None, []),
        ("Skagerrak", "SKA", ProvinceType.SEA, False, None, []),
        ("Baltic Sea", "BAL", ProvinceType.SEA, False, None, []),
        ("Gulf of Bothnia", "BOT", ProvinceType.SEA, False, None, []),
        ("Western Mediterranean", "WES", ProvinceType.SEA, False, None, []),
        ("Gulf of Lyon", "LYO", ProvinceType.SEA, False, None, []),
        ("Tyrrhenian Sea", "TYS", ProvinceType.SEA, False, None, []),
        ("Ionian Sea", "ION", ProvinceType.SEA, False, None, []),
        ("Adriatic Sea", "ADR", ProvinceType.SEA, False, None, []),
        ("Aegean Sea", "AEG", ProvinceType.SEA, False, None, []),
        ("Eastern Mediterranean", "EAS", ProvinceType.SEA, False, None, []),
        ("Black Sea", "BLA", ProvinceType.SEA, False, None, []),
    ]
    
    # Add all provinces to the map
    for full_name, abbr, ptype, is_sc, home_of, coasts in provinces_data:
        # Create province with abbreviation as name (for test compatibility)
        province = Province(abbr, full_name, ptype, is_sc, home_of, coasts)
        game_map.add_province(province)
    
    # Define adjacencies (this is a large dataset)
    # Format: (from, to, from_coast, to_coast)
    # None for coast means no specific coast requirement
    
    adjacencies = [
        # England connections
        ("Lon", "Wal", None, None),
        ("Lon", "Yor", None, None),
        ("Lon", "NTH", None, None),
        ("Lon", "ENG", None, None),
        ("Edi", "Yor", None, None),
        ("Edi", "Cly", None, None),
        ("Edi", "NTH", None, None),
        ("Edi", "NWG", None, None),
        ("Lvp", "Wal", None, None),
        ("Lvp", "Yor", None, None),
        ("Lvp", "Cly", None, None),
        ("Lvp", "IRI", None, None),
        ("Lvp", "NAO", None, None),
        ("Wal", "Yor", None, None),
        ("Wal", "IRI", None, None),
        ("Wal", "ENG", None, None),
        ("Yor", "Wal", None, None),
        ("Yor", "NTH", None, None),
        ("Cly", "NAO", None, None),
        ("Cly", "NWG", None, None),
        
        # France connections
        ("Par", "Pic", None, None),
        ("Par", "Bur", None, None),
        ("Par", "Gas", None, None),
        ("Par", "Bre", None, None),  # Add missing Paris-Brest adjacency
        ("Bre", "Pic", None, None),
        ("Bre", "Gas", None, None),
        ("Bre", "MAO", None, None),
        ("Bre", "ENG", None, None),
        ("Mar", "Bur", None, None),
        ("Mar", "Gas", None, None),
        ("Mar", "Pie", None, None),
        ("Mar", "Spa", None, Coast.SOUTH),
        ("Mar", "LYO", None, None),
        ("Pic", "Bel", None, None),
        ("Pic", "Bur", None, None),
        ("Pic", "ENG", None, None),
        ("Bur", "Bel", None, None),
        ("Bur", "Ruh", None, None),
        ("Bur", "Mun", None, None),
        ("Bur", "Gas", None, None),
        ("Bur", "Mar", None, None),
        ("Gas", "Spa", None, None),
        ("Gas", "MAO", None, None),
        
        # Germany connections
        ("Ber", "Kie", None, None),
        ("Ber", "Pru", None, None),
        ("Ber", "Sil", None, None),
        ("Ber", "Mun", None, None),
        ("Ber", "BAL", None, None),
        ("Mun", "Kie", None, None),
        ("Mun", "Ruh", None, None),
        ("Mun", "Bur", None, None),
        ("Mun", "Tyr", None, None),
        ("Mun", "Boh", None, None),
        ("Mun", "Sil", None, None),
        ("Kie", "Ruh", None, None),
        ("Kie", "Hol", None, None),
        ("Kie", "Den", None, None),
        ("Kie", "HEL", None, None),
        ("Kie", "BAL", None, None),
        ("Ruh", "Bel", None, None),
        ("Ruh", "Hol", None, None),
        ("Pru", "Sil", None, None),
        ("Pru", "War", None, None),
        ("Pru", "Lvn", None, None),
        ("Pru", "BAL", None, None),
        ("Sil", "Boh", None, None),
        ("Sil", "Gal", None, None),
        ("Sil", "War", None, None),
        
        # Italy connections
        ("Rom", "Tus", None, None),
        ("Rom", "Nap", None, None),
        ("Rom", "Apu", None, None),
        ("Rom", "Ven", None, None),
        ("Rom", "TYS", None, None),
        ("Ven", "Tus", None, None),
        ("Ven", "Pie", None, None),
        ("Ven", "Tyr", None, None),
        ("Ven", "Tri", None, None),
        ("Ven", "ADR", None, None),
        ("Nap", "Apu", None, None),
        ("Nap", "Rom", None, None),
        ("Nap", "TYS", None, None),
        ("Nap", "ION", None, None),
        ("Apu", "ADR", None, None),
        ("Apu", "ION", None, None),
        ("Pie", "Tus", None, None),
        ("Pie", "Tyr", None, None),
        ("Pie", "Mar", None, None),
        ("Pie", "LYO", None, None),
        ("Tus", "LYO", None, None),
        ("Tus", "TYS", None, None),
        
        # Austria connections
        ("Vie", "Boh", None, None),
        ("Vie", "Gal", None, None),
        ("Vie", "Bud", None, None),
        ("Vie", "Tyr", None, None),
        ("Vie", "Tri", None, None),
        ("Bud", "Gal", None, None),
        ("Bud", "Rum", None, None),
        ("Bud", "Ser", None, None),
        ("Bud", "Tri", None, None),
        ("Tri", "Tyr", None, None),
        ("Tri", "Alb", None, None),
        ("Tri", "Ser", None, None),
        ("Tri", "ADR", None, None),
        ("Boh", "Tyr", None, None),
        ("Boh", "Gal", None, None),
        ("Gal", "Ukr", None, None),
        ("Gal", "Rum", None, None),
        ("Gal", "War", None, None),
        ("Tyr", "Pie", None, None),
        
        # Russia connections
        ("Mos", "War", None, None),
        ("Mos", "Ukr", None, None),
        ("Mos", "Sev", None, None),
        ("Mos", "Lvn", None, None),
        ("Mos", "StP", None, None),
        ("War", "Ukr", None, None),
        ("War", "Lvn", None, None),
        ("Sev", "Ukr", None, None),
        ("Sev", "Rum", None, None),
        ("Sev", "Arm", None, None),
        ("Sev", "BLA", None, None),
        ("StP", "Mos", Coast.SOUTH, None),
        ("StP", "Lvn", Coast.SOUTH, None),
        ("StP", "Fin", Coast.SOUTH, None),
        ("StP", "Fin", Coast.NORTH, None),
        ("StP", "Nwy", Coast.NORTH, None),
        ("StP", "BAR", Coast.NORTH, None),
        ("StP", "BOT", Coast.SOUTH, None),
        ("Lvn", "War", None, None),
        ("Lvn", "Fin", None, None),
        ("Lvn", "BOT", None, None),
        ("Lvn", "BAL", None, None),
        ("Ukr", "Rum", None, None),
        ("Fin", "Swe", None, None),
        ("Fin", "Nwy", None, None),
        ("Fin", "BOT", None, None),
        
        # Turkey connections
        ("Con", "Bul", None, Coast.SOUTH),
        ("Con", "Bul", None, Coast.EAST),
        ("Con", "Ank", None, None),
        ("Con", "Smy", None, None),
        ("Con", "BLA", None, None),
        ("Con", "AEG", None, None),
        ("Ank", "Arm", None, None),
        ("Ank", "Smy", None, None),
        ("Ank", "BLA", None, None),
        ("Smy", "Arm", None, None),
        ("Smy", "Syr", None, None),
        ("Smy", "AEG", None, None),
        ("Smy", "EAS", None, None),
        ("Arm", "Sev", None, None),
        ("Arm", "Syr", None, None),
        ("Arm", "BLA", None, None),
        ("Syr", "EAS", None, None),
        
        # Neutral territories
        ("Bel", "Hol", None, None),
        ("Bel", "NTH", None, None),
        ("Bel", "ENG", None, None),
        ("Hol", "NTH", None, None),
        ("Hol", "HEL", None, None),
        ("Den", "Swe", None, None),
        ("Den", "HEL", None, None),
        ("Den", "SKA", None, None),
        ("Den", "BAL", None, None),
        ("Swe", "Nwy", None, None),
        ("Swe", "SKA", None, None),
        ("Swe", "BAL", None, None),
        ("Swe", "BOT", None, None),
        ("Nwy", "NWG", None, None),
        ("Nwy", "NTH", None, None),
        ("Nwy", "SKA", None, None),
        ("Nwy", "BAR", None, None),
        ("Spa", "Por", None, None),
        ("Spa", "Gas", None, None),
        ("Spa", "MAO", Coast.NORTH, None),
        ("Spa", "MAO", Coast.SOUTH, None),
        ("Spa", "WES", Coast.SOUTH, None),
        ("Spa", "LYO", Coast.SOUTH, None),
        ("Por", "MAO", None, None),
        ("Tun", "WES", None, None),
        ("Tun", "TYS", None, None),
        ("Tun", "ION", None, None),
        ("Ser", "Alb", None, None),
        ("Ser", "Gre", None, None),
        ("Ser", "Bul", None, None),
        ("Ser", "Rum", None, None),
        ("Bul", "Gre", Coast.SOUTH, None),
        ("Bul", "Rum", None, None),
        ("Bul", "AEG", Coast.SOUTH, None),
        ("Bul", "BLA", Coast.EAST, None),
        ("Rum", "BLA", None, None),
        ("Gre", "Alb", None, None),
        ("Gre", "AEG", None, None),
        ("Gre", "ION", None, None),
        ("Alb", "ADR", None, None),
        ("Alb", "ION", None, None),
        
        # Sea connections
        ("NTH", "NWG", None, None),
        ("NTH", "SKA", None, None),
        ("NTH", "HEL", None, None),
        ("NTH", "ENG", None, None),
        ("NTH", "Den", None, None),
        ("NWG", "NAO", None, None),
        ("NWG", "BAR", None, None),
        ("ENG", "IRI", None, None),
        ("ENG", "MAO", None, None),
        ("IRI", "NAO", None, None),
        ("IRI", "MAO", None, None),
        ("MAO", "NAO", None, None),
        ("MAO", "WES", None, None),
        ("HEL", "SKA", None, None),
        ("HEL", "BAL", None, None),
        ("SKA", "BAL", None, None),
        ("BAL", "BOT", None, None),
        ("WES", "LYO", None, None),
        ("WES", "TYS", None, None),
        ("LYO", "TYS", None, None),
        ("TYS", "ION", None, None),
        ("ION", "ADR", None, None),
        ("ION", "AEG", None, None),
        ("ION", "EAS", None, None),
        ("AEG", "EAS", None, None),
        ("AEG", "BLA", None, None),
    ]
    
    # Add all adjacencies
    for adj in adjacencies:
        if len(adj) == 2:
            game_map.add_adjacency(adj[0], adj[1])
        elif len(adj) == 4:
            game_map.add_adjacency(adj[0], adj[1], adj[2], adj[3])
    
    return game_map
