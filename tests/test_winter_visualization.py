"""
Test Winter phase visualization with builds and disbands.
"""

import sys
sys.path.insert(0, '.')

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, Season
from diplomacy_game_engine.core.map import Power, Coast, create_standard_map
from diplomacy_game_engine.core.orders import BuildOrder, DisbandOrder
from diplomacy_game_engine.core.resolver import WinterResolver
from diplomacy_game_engine.visualization.visualizer import MapVisualizer
import os

def test_winter_visualization():
    """Test Winter phase visualization with builds."""
    print("="*60)
    print("TESTING WINTER VISUALIZATION")
    print("="*60)
    
    # Create a game state after Fall (some powers gained/lost SCs)
    game_map = create_standard_map()
    state = GameState(game_map, year=1901, season=Season.WINTER)
    
    # Add units (Russia has 4 units but will have 5 SCs after Fall)
    units = {
        'Russia_A_Mos_1': Unit(Power.RUSSIA, UnitType.ARMY, 'Mos'),
        'Russia_F_Sev_2': Unit(Power.RUSSIA, UnitType.FLEET, 'Sev'),
        'Russia_A_War_3': Unit(Power.RUSSIA, UnitType.ARMY, 'War'),
        'Russia_F_StP_4': Unit(Power.RUSSIA, UnitType.FLEET, 'StP', coast=Coast.SOUTH),
        
        # England has 3 units but only 2 SCs (needs to disband)
        'England_F_Lon_1': Unit(Power.ENGLAND, UnitType.FLEET, 'Lon'),
        'England_F_Edi_2': Unit(Power.ENGLAND, UnitType.FLEET, 'Edi'),
        'England_A_Lvp_3': Unit(Power.ENGLAND, UnitType.ARMY, 'Lvp'),
    }
    
    state.units = units
    
    # Set supply centers (Russia gained Swe, England lost Edi)
    state.supply_centers = {
        'Mos': Power.RUSSIA,
        'Sev': Power.RUSSIA,
        'War': Power.RUSSIA,
        'StP': Power.RUSSIA,
        'Swe': Power.RUSSIA,  # Gained
        'Lon': Power.ENGLAND,
        'Lvp': Power.ENGLAND,
        # Edi lost
    }
    
    print(f"✓ Created Winter state")
    print(f"  - Russia: 4 units, 5 SCs (can build 1)")
    print(f"  - England: 3 units, 2 SCs (must disband 1)")
    
    # Create build/disband orders
    build_order = BuildOrder(
        power=Power.RUSSIA,
        unit_type=UnitType.ARMY,
        location="Mos"
    )
    
    disband_order = DisbandOrder(
        unit=units['England_A_Lvp_3']
    )
    
    orders = [build_order, disband_order]
    print(f"✓ Created {len(orders)} adjustment orders")
    
    # Visualize BEFORE adjustments
    base_image = 'diplomacy_game_engine/assets/europemapbw.png'
    
    print("\n--- Visualizing Before State ---")
    visualizer_before = MapVisualizer(state, base_image_path=base_image)
    visualizer_before.draw_map()
    visualizer_before.save('test_winter_before.png')
    print("✓ Saved test_winter_before.png")
    
    # Visualize orders (dotted circles for builds, red X for disbands)
    print("\n--- Visualizing Orders ---")
    from diplomacy_game_engine.visualization.visualizer import visualize_game
    
    # Separate build orders and disband unit IDs
    build_orders_list = [order for order in orders if isinstance(order, BuildOrder)]
    disband_unit_ids = [order.unit.get_id() for order in orders if isinstance(order, DisbandOrder)]
    
    visualize_game(
        state,
        filename='test_winter_orders.png',
        base_image_path=base_image,
        orders=build_orders_list,
        disband_unit_ids=disband_unit_ids
    )
    print("✓ Saved test_winter_orders.png")
    print("  - Should show dotted circle at Mos (build)")
    print("  - Should show red X at Lvp (disband)")
    
    # Resolve Winter adjustments
    build_dict = {'Russia': [build_order]}
    disband_dict = {'England': [units['England_A_Lvp_3'].get_id()]}
    
    resolver = WinterResolver(state, build_dict, disband_dict)
    new_state = resolver.resolve()
    print(f"✓ Resolved Winter adjustments")
    
    # Visualize AFTER adjustments
    print("\n--- Visualizing After State ---")
    visualizer_after = MapVisualizer(new_state, base_image_path=base_image)
    visualizer_after.draw_map()
    visualizer_after.save('test_winter_after.png')
    print("✓ Saved test_winter_after.png")
    
    print(f"\nCheck visualizations:")
    print(f"  - test_winter_before.png: Russia 4 units, England 3 units")
    print(f"  - test_winter_orders.png: Dotted circle at Mos, Red X at Lvp")
    print(f"  - test_winter_after.png: Russia 5 units (built), England 2 units (disbanded)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_winter_visualization()
        if success:
            print("\n" + "="*60)
            print("WINTER VISUALIZATION TEST PASSED ✓")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("TEST FAILED ✗")
            print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
