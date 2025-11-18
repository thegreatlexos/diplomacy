"""
Test script to verify OrderWriter handles BuildOrder and DisbandOrder correctly.
"""

from diplomacy_game_engine.core.orders import BuildOrder, DisbandOrder
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.game_state import UnitType, create_starting_state
from diplomacy_game_engine.gamemaster.order_writer import OrderWriter

def test_build_order():
    """Test that BuildOrder can be converted to dict."""
    print("Testing BuildOrder...")
    
    # Create a BuildOrder
    build_order = BuildOrder(
        power=Power.RUSSIA,
        unit_type=UnitType.ARMY,
        location="Mos"
    )
    
    # Convert to dict
    try:
        order_dict = OrderWriter._order_to_dict(build_order)
        print(f"✓ BuildOrder converted successfully: {order_dict}")
        assert order_dict['action'] == 'build'
        assert 'A Mos' in order_dict['unit']
        print("✓ BuildOrder test PASSED")
        return True
    except Exception as e:
        print(f"✗ BuildOrder test FAILED: {e}")
        return False

def test_disband_order():
    """Test that DisbandOrder can be converted to dict."""
    print("\nTesting DisbandOrder...")
    
    # Create a game state and get a unit
    state = create_starting_state()
    game_map = create_standard_map()
    
    # Get Russia's army in Moscow
    unit = state.get_unit_at("Mos")
    
    if not unit:
        print("✗ Could not find unit for test")
        return False
    
    # Create a DisbandOrder
    disband_order = DisbandOrder(unit=unit)
    
    # Convert to dict
    try:
        order_dict = OrderWriter._order_to_dict(disband_order)
        print(f"✓ DisbandOrder converted successfully: {order_dict}")
        assert order_dict['action'] == 'disband'
        assert 'A Mos' in order_dict['unit']
        print("✓ DisbandOrder test PASSED")
        return True
    except Exception as e:
        print(f"✗ DisbandOrder test FAILED: {e}")
        return False

def test_save_to_yaml():
    """Test that build/disband orders can be saved to YAML."""
    print("\nTesting YAML save...")
    
    state = create_starting_state()
    
    # Create test orders
    build_order = BuildOrder(
        power=Power.RUSSIA,
        unit_type=UnitType.FLEET,
        location="StP"
    )
    
    unit = state.get_unit_at("War")
    disband_order = DisbandOrder(unit=unit)
    
    orders = [build_order, disband_order]
    
    # Try to save
    try:
        OrderWriter.save_orders_to_yaml(
            orders,
            state,
            "test_game",
            "test_winter_orders.yaml"
        )
        print("✓ YAML save successful")
        print("✓ Check test_winter_orders.yaml for output")
        return True
    except Exception as e:
        print(f"✗ YAML save FAILED: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("TESTING ORDER WRITER FIX")
    print("="*60)
    
    results = []
    results.append(test_build_order())
    results.append(test_disband_order())
    results.append(test_save_to_yaml())
    
    print("\n" + "="*60)
    if all(results):
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("="*60)
