"""
Test to reproduce the retreat bug where F Rum cannot retreat to Sev.

Scenario:
- Spring 1901: Russia F Sev -> Rum (successful)
- Fall 1901: Russia F Rum -> Bul, Russia A Gal -> Rum (with support)
- F Rum is dislodged
- F Rum tries to retreat to Sev (should be valid but fails)
"""

import sys
sys.path.insert(0, '.')

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, Season
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.orders import MoveOrder, SupportOrder, RetreatOrder
from diplomacy_game_engine.core.resolver import MovementResolver, RetreatResolver


def test_retreat_to_origin():
    """Test that a unit can retreat to the province it came from."""
    print("="*60)
    print("TESTING RETREAT BUG")
    print("="*60)
    
    # Create game state after Spring 1901
    game_map = create_standard_map()
    state = GameState(game_map, year=1901, season=Season.FALL)
    
    # Set up units as they would be after Spring 1901
    # Russia F Rum (moved from Sev in Spring)
    # Russia A Gal
    # Russia A Ukr
    # Turkey A Bul (moving to Gre)
    # Austria A Ser (moving to Bul to create standoff)
    # Austria F Alb (moving to Gre to create standoff)
    units = {
        'Russia_F_Rum_1': Unit(Power.RUSSIA, UnitType.FLEET, 'Rum'),
        'Russia_A_Gal_2': Unit(Power.RUSSIA, UnitType.ARMY, 'Gal'),
        'Russia_A_Ukr_3': Unit(Power.RUSSIA, UnitType.ARMY, 'Ukr'),
        'Turkey_A_Bul_4': Unit(Power.TURKEY, UnitType.ARMY, 'Bul'),
        'Austria_A_Ser_5': Unit(Power.AUSTRIA, UnitType.ARMY, 'Ser'),
        'Austria_F_Alb_6': Unit(Power.AUSTRIA, UnitType.FLEET, 'Alb'),
    }
    
    state.units = units
    
    print(f"✓ Created Fall 1901 state")
    print(f"  - Russia F Rum at Rumania")
    print(f"  - Russia A Gal at Galicia")
    print(f"  - Russia A Ukr at Ukraine")
    print(f"  - Turkey A Bul at Bulgaria")
    print(f"  - Austria A Ser at Serbia")
    print(f"  - Austria F Alb at Albania")
    print(f"  - Sevastopol is EMPTY")
    
    # Create Fall 1901 orders
    # Make F Rum hold so it gets dislodged by A Gal
    f_rum = units['Russia_F_Rum_1']
    a_gal = units['Russia_A_Gal_2']
    a_ukr = units['Russia_A_Ukr_3']
    
    orders = {
        # F Rum holds (will be dislodged)
        a_gal.get_id(): MoveOrder(a_gal, 'Rum'),
        a_ukr.get_id(): SupportOrder(a_ukr, 'Gal', None, 'Rum'),  # Fixed: coast=None, dest='Rum'
    }
    
    print(f"\n✓ Created Fall 1901 orders")
    print(f"  - F Rum holds")
    print(f"  - A Gal -> Rum (supported by A Ukr)")
    
    # Resolve movement
    print(f"\n--- Resolving Movement ---")
    resolver = MovementResolver(state, orders)
    
    # Add debug output for move attempts
    print(f"\n--- Move Attempts (Before Resolution) ---")
    resolver._identify_moves()
    resolver._build_convoy_routes()
    
    # Debug support validation
    print(f"\n--- Support Validation ---")
    for unit_id, order in orders.items():
        if isinstance(order, SupportOrder):
            unit = state.units.get(unit_id)
            is_valid = resolver._is_support_valid(order)
            print(f"  {unit.power.value} {unit.unit_type.value} at {unit.location}")
            print(f"    Supporting: {order.supported_unit_location} -> {order.destination}")
            print(f"    Valid: {is_valid}")
            if not is_valid:
                print(f"    INVALID SUPPORT!")
    
    resolver._calculate_strengths()
    resolver._apply_support_cutting()
    resolver._calculate_strengths()  # Recalculate after support cutting
    
    for dest, attempts in resolver.moves_to_province.items():
        print(f"\n  Destination: {dest}")
        for attempt in attempts:
            print(f"    {attempt.unit.power.value} {attempt.unit.unit_type.value} from {attempt.origin}")
            print(f"      Strength: {attempt.strength}")
            print(f"      Supports: {[s.location for s in attempt.supports]}")
        
        # Check defender
        defender = state.get_unit_at(dest)
        if defender:
            print(f"    Defender: {defender.power.value} {defender.unit_type.value}")
            defender_order = orders.get(defender.get_id())
            if defender_order:
                print(f"      Defender order: {type(defender_order).__name__}")
            else:
                print(f"      Defender order: None (holding)")
    
    result = resolver.resolve()
    
    print(f"✓ Movement resolved")
    print(f"  - Dislodged units: {len(result.dislodged_units)}")
    
    # Debug: Print move results
    print(f"\n--- Move Results ---")
    for unit_id, move_result in result.move_results.items():
        print(f"  {unit_id}: {move_result}")
    
    print(f"\n--- Contested Provinces ---")
    print(f"  {result.contested_provinces}")
    
    if result.dislodged_units:
        dislodged = result.dislodged_units[0]
        print(f"  - Dislodged: {dislodged.unit.unit_type.value} at {dislodged.dislodged_from}")
        print(f"  - Dislodger origin: {dislodged.dislodger_origin}")
        print(f"  - Contested provinces: {dislodged.contested_provinces}")
        
        # Check valid retreat destinations
        print(f"\n--- Checking Valid Retreat Destinations ---")
        valid_dests = dislodged.get_valid_retreat_destinations(game_map, result.new_state)
        print(f"✓ Valid retreat destinations: {valid_dests}")
        
        # Check if Sev is in valid destinations
        if 'Sev' in valid_dests:
            print(f"✓ Sev IS in valid destinations (CORRECT)")
        else:
            print(f"✗ Sev is NOT in valid destinations (BUG!)")
            
            # Debug why Sev is not valid
            print(f"\n--- Debugging Why Sev is Invalid ---")
            
            # Check adjacency
            adjacent = game_map.get_adjacent_provinces('Rum')
            print(f"  Adjacent to Rum: {adjacent}")
            print(f"  Is Sev adjacent? {'Sev' in adjacent}")
            
            # Check if Sev is occupied
            unit_at_sev = result.new_state.get_unit_at('Sev')
            print(f"  Unit at Sev: {unit_at_sev}")
            
            # Check if Sev is dislodger's origin
            print(f"  Dislodger origin: {dislodged.dislodger_origin}")
            print(f"  Is Sev dislodger origin? {'Sev' == dislodged.dislodger_origin}")
            
            # Check if Sev is contested
            print(f"  Contested provinces: {dislodged.contested_provinces}")
            print(f"  Is Sev contested? {'Sev' in dislodged.contested_provinces}")
        
        # Try to apply retreat
        print(f"\n--- Applying Retreat ---")
        retreat_order = RetreatOrder(dislodged.unit, 'Sev')
        retreat_orders = {dislodged.unit.get_id(): retreat_order}
        
        retreat_resolver = RetreatResolver(result.new_state, retreat_orders)
        final_state = retreat_resolver.resolve()
        
        # Check if F Rum is at Sev
        unit_at_sev_after = final_state.get_unit_at('Sev')
        if unit_at_sev_after:
            print(f"✓ F Rum successfully retreated to Sev")
            print(f"  Unit at Sev: {unit_at_sev_after.power.value} {unit_at_sev_after.unit_type.value}")
        else:
            print(f"✗ F Rum was disbanded (BUG!)")
            print(f"  No unit at Sev after retreat")
    else:
        print(f"✗ No units were dislodged (unexpected!)")
    
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        test_retreat_to_origin()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
