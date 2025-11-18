"""
Test that YAML parser correctly handles 'supporting' field name.
"""

import sys
sys.path.insert(0, '.')

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, Season
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.io.yaml_orders import YAMLOrderLoader
from diplomacy_game_engine.core.orders import SupportOrder


def test_yaml_support_parsing():
    """Test that YAML parser handles 'supporting' field."""
    print("="*60)
    print("TESTING YAML SUPPORT PARSING")
    print("="*60)
    
    # Create game state
    game_map = create_standard_map()
    state = GameState(game_map, year=1901, season=Season.FALL)
    
    # Add test units
    units = {
        'Russia_A_Gal_1': Unit(Power.RUSSIA, UnitType.ARMY, 'Gal'),
        'Russia_A_Ukr_2': Unit(Power.RUSSIA, UnitType.ARMY, 'Ukr'),
    }
    state.units = units
    
    # Create YAML data with 'supporting' field
    yaml_data = {
        'phase': 'Fall 1901',
        'orders': [
            {
                'unit': 'A Gal',
                'action': 'move',
                'destination': 'Rum'
            },
            {
                'unit': 'A Ukr',
                'action': 'support',
                'supporting': 'A Gal',  # Using 'supporting' instead of 'supports'
                'destination': 'Rum'
            }
        ]
    }
    
    # Parse orders
    loader = YAMLOrderLoader(state)
    orders = loader.parse_orders(yaml_data)
    
    print(f"✓ Parsed {len(orders)} orders")
    
    # Check if support order was created correctly
    a_ukr_id = units['Russia_A_Ukr_2'].get_id()
    if a_ukr_id in orders:
        order = orders[a_ukr_id]
        if isinstance(order, SupportOrder):
            print(f"✓ Support order created")
            print(f"  Supported location: {order.supported_unit_location}")
            print(f"  Destination: {order.destination}")
            
            if order.destination == 'Rum':
                print(f"✓ Support order has correct destination (Rum)")
            else:
                print(f"✗ Support order has wrong destination: {order.destination}")
        else:
            print(f"✗ Order is not a SupportOrder: {type(order)}")
    else:
        print(f"✗ No order found for A Ukr")
    
    # Check for warnings
    if loader.get_warnings():
        print(f"\nWarnings:")
        for warning in loader.get_warnings():
            print(f"  {warning}")
    
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        test_yaml_support_parsing()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
