#!/usr/bin/env python3
"""
Test the specific F Rum -> Sev retreat issue from gunboat_test_006.
"""

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, DislodgedUnit, Season
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.orders import RetreatOrder
from diplomacy_game_engine.core.resolver import RetreatResolver

def test_rum_sev_retreat():
    """Test F Rum retreating to Sev after being dislodged from Rum."""
    
    print("="*60)
    print("TESTING F RUM -> SEV RETREAT")
    print("="*60)
    
    # Create game state
    game_map = create_standard_map()
    state = GameState(game_map, year=1902, season=Season.RETREAT)
    
    # Add units from Fall 1902 after state (simplified - just the relevant ones)
    state.add_unit(Unit(Power.AUSTRIA, UnitType.ARMY, "Rum", None))  # Dislodger at Rum
    state.add_unit(Unit(Power.RUSSIA, UnitType.ARMY, "Ukr", None))
    # Sev is EMPTY
    
    # Create dislodged unit
    dislodged_fleet = Unit(Power.RUSSIA, UnitType.FLEET, "Rum", None)
    dislodged = DislodgedUnit(
        unit=dislodged_fleet,
        dislodged_from="Rum",
        dislodger_origin="Bud",
        contested_provinces={"Bel", "Bul", "Spa", "Nwy", "Gre", "Gal"}
    )
    state.dislodged_units = [dislodged]
    
    print(f"✓ Created Fall 1902 state with dislodged F Rum")
    print(f"  - Dislodged from: Rum")
    print(f"  - Dislodger origin: Bud")
    print(f"  - Contested provinces: {dislodged.contested_provinces}")
    
    # Check valid retreat destinations
    print(f"\n--- Checking Valid Retreat Destinations ---")
    valid_dests = dislodged.get_valid_retreat_destinations(game_map, state)
    print(f"Valid destinations: {valid_dests}")
    print(f"Is Sev in valid destinations? {('Sev' in valid_dests)}")
    
    # Check adjacency
    adjacent = game_map.get_adjacent_provinces("Rum", None)
    print(f"\nProvinces adjacent to Rum: {adjacent}")
    print(f"Is Sev adjacent to Rum? {('Sev' in adjacent)}")
    
    # Check if Sev is occupied
    unit_at_sev = state.get_unit_at("Sev")
    print(f"Unit at Sev: {unit_at_sev}")
    
    # Check province type
    sev_province = game_map.get_province("Sev")
    print(f"Sev province type: {sev_province.province_type.value if sev_province else 'NOT FOUND'}")
    
    # Create retreat order
    retreat_order = RetreatOrder(dislodged_fleet, "Sev", None)
    print(f"\n--- Creating Retreat Order ---")
    print(f"Order: {retreat_order}")
    
    # Resolve retreat
    print(f"\n--- Resolving Retreat ---")
    retreat_orders = {dislodged_fleet.get_id(): retreat_order}
    resolver = RetreatResolver(state, retreat_orders)
    new_state = resolver.resolve()
    
    # Check result
    print(f"\n--- Checking Result ---")
    unit_at_sev_after = new_state.get_unit_at("Sev")
    if unit_at_sev_after:
        print(f"✓ SUCCESS: F Rum retreated to Sev")
        print(f"  Unit at Sev: {unit_at_sev_after.power.value} {unit_at_sev_after.unit_type.value}")
    else:
        print(f"✗ FAILED: F Rum was disbanded (not at Sev)")
        print(f"  Units in new state: {len(new_state.units)}")
        for unit in new_state.units.values():
            if unit.power == Power.RUSSIA:
                print(f"    Russia {unit.unit_type.value[0]} {unit.location}")
    
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_rum_sev_retreat()
