"""
Comprehensive test for all visualization features:
- Support orders (dashed lines)
- Cut support (red dashed lines)
- Convoy orders (wavy lines)
- Dislodged units (red circles)
- Hold orders (black circles)
- Successful moves (black arrows)
- Bounced moves (red arrows)
"""

import sys
sys.path.insert(0, '.')

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, DislodgedUnit, Season
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.orders import MoveOrder, SupportOrder, HoldOrder, ConvoyOrder
from diplomacy_game_engine.visualization.visualizer import MapVisualizer

def create_test_scenario():
    """Create a custom game state with various order types."""
    print("Creating test scenario...")
    
    game_map = create_standard_map()
    state = GameState(game_map, year=1901, season=Season.SPRING)
    
    # Add units for testing different scenarios
    units = {
        # France - for support scenario
        'France_A_Par_1': Unit(Power.FRANCE, UnitType.ARMY, 'Par'),
        'France_A_Mar_2': Unit(Power.FRANCE, UnitType.ARMY, 'Mar'),
        'France_A_Bur_3': Unit(Power.FRANCE, UnitType.ARMY, 'Bur'),
        
        # Germany - for cutting support
        'Germany_A_Pic_1': Unit(Power.GERMANY, UnitType.ARMY, 'Pic'),
        
        # England - for convoy
        'England_F_ENG_1': Unit(Power.ENGLAND, UnitType.FLEET, 'ENG'),
        'England_A_Lon_2': Unit(Power.ENGLAND, UnitType.ARMY, 'Lon'),
        
        # Italy - for hold
        'Italy_F_Nap_1': Unit(Power.ITALY, UnitType.FLEET, 'Nap'),
        
        # Russia - for bounce scenario
        'Russia_A_War_1': Unit(Power.RUSSIA, UnitType.ARMY, 'War'),
        'Austria_A_Gal_1': Unit(Power.AUSTRIA, UnitType.ARMY, 'Gal'),
    }
    
    state.units = units
    
    # Create orders
    orders = [
        # Support move: A Par supports A Mar → Bur
        SupportOrder(
            unit=units['France_A_Par_1'],
            supported_unit_location='Mar',
            supported_unit_coast=None,
            destination='Bur',
            dest_coast=None
        ),
        
        # Supported move: A Mar → Bur
        MoveOrder(
            unit=units['France_A_Mar_2'],
            destination='Bur'
        ),
        
        # Unit being attacked (will be dislodged)
        HoldOrder(unit=units['France_A_Bur_3']),
        
        # Cut support: A Pic → Par (cuts the support)
        MoveOrder(
            unit=units['Germany_A_Pic_1'],
            destination='Par'
        ),
        
        # Convoy: F ENG convoys A Lon → Pic
        ConvoyOrder(
            unit=units['England_F_ENG_1'],
            convoyed_army_location='Lon',
            destination='Pic'
        ),
        
        # Convoyed army
        MoveOrder(
            unit=units['England_A_Lon_2'],
            destination='Pic',
            via_convoy=True
        ),
        
        # Hold order: F Nap holds
        HoldOrder(unit=units['Italy_F_Nap_1']),
        
        # Bounce scenario: A War → Gal
        MoveOrder(
            unit=units['Russia_A_War_1'],
            destination='Gal'
        ),
        
        # Bounce scenario: A Gal → War
        MoveOrder(
            unit=units['Austria_A_Gal_1'],
            destination='War'
        ),
    ]
    
    # Create mock resolution results
    move_results = {
        'France_A_Par_1': 'Held position',  # Support was cut
        'France_A_Mar_2': 'Successfully moved to Bur',
        'France_A_Bur_3': 'Held position',  # Will be dislodged
        'Germany_A_Pic_1': 'Bounced from Par',
        'England_F_ENG_1': 'Convoyed A Lon to Pic',
        'England_A_Lon_2': 'Successfully moved to Pic',
        'Italy_F_Nap_1': 'Held position',
        'Russia_A_War_1': 'Bounced from Gal',
        'Austria_A_Gal_1': 'Bounced from War',
    }
    
    # Create dislodged unit
    dislodged_units = [
        DislodgedUnit(
            unit=units['France_A_Bur_3'],
            dislodged_from='Bur',
            dislodger_origin='Mar'
        )
    ]
    
    # Cut supports
    cut_supports = {'France_A_Par_1'}
    
    return state, orders, move_results, dislodged_units, cut_supports

def test_all_visualizations():
    """Test all visualization features."""
    print("="*60)
    print("COMPREHENSIVE VISUALIZATION TEST")
    print("="*60)
    
    # Create test scenario
    state, orders, move_results, dislodged_units, cut_supports = create_test_scenario()
    print(f"✓ Created test scenario")
    print(f"  - {len(orders)} orders")
    print(f"  - {len(dislodged_units)} dislodged units")
    print(f"  - {len(cut_supports)} cut supports")
    
    # Create visualization
    base_image = 'diplomacy_game_engine/assets/europemapbw.png'
    visualizer = MapVisualizer(state, base_image_path=base_image)
    
    # Draw with all features
    visualizer.draw_map_with_results(
        orders=orders,
        move_results=move_results,
        dislodged_units=dislodged_units,
        original_state=state,
        invalid_supports=set(),
        cut_supports=cut_supports
    )
    
    # Save visualization
    output_path = 'test_all_features.png'
    visualizer.save(output_path)
    print(f"✓ Saved visualization to {output_path}")
    
    print(f"\nCheck {output_path} for:")
    print("  ✓ Black circles: Hold orders (F Nap)")
    print("  ✓ Black dashed lines: Support orders (A Par → A Mar → Bur)")
    print("  ✓ Red dashed lines: Cut support (A Par, attacked by A Pic)")
    print("  ✓ Wavy lines: Convoy indicator (F ENG)")
    print("  ✓ Black arrows: Successful moves (A Mar → Bur, A Lon → Pic)")
    print("  ✓ Red arrows: Bounced moves (A War ↔ A Gal, A Pic → Par)")
    print("  ✓ Red circles: Dislodged units (A Bur)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_all_visualizations()
        if success:
            print("\n" + "="*60)
            print("ALL VISUALIZATION FEATURES TESTED ✓")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("TEST FAILED ✗")
            print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
