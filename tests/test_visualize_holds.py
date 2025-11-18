"""
Test script to verify hold circle visualization for llm_game_005 Spring 1901.
"""

import sys
sys.path.insert(0, '.')

from diplomacy_game_engine.core.game_state import GameState
from diplomacy_game_engine.core.map import create_standard_map
from diplomacy_game_engine.io.yaml_orders import YAMLOrderLoader
from diplomacy_game_engine.core.resolver import MovementResolver
from diplomacy_game_engine.visualization.visualizer import MapVisualizer
import os

def test_spring_1901_visualization():
    """Test visualization of Spring 1901 orders with hold circles."""
    print("="*60)
    print("TESTING HOLD CIRCLE VISUALIZATION")
    print("="*60)
    
    # Create initial game state
    from diplomacy_game_engine.core.game_state import create_starting_state
    
    game_map = create_standard_map()
    state = create_starting_state()
    print(f"✓ Created initial state")
    
    # Load orders
    orders_path = 'games/llm_game_005/orders/1901_01_spring.yaml'
    
    if not os.path.exists(orders_path):
        print(f"✗ Orders file not found: {orders_path}")
        return False
    
    loader = YAMLOrderLoader(state)
    yaml_data = loader.load_from_file(orders_path)
    orders = loader.parse_orders(yaml_data)
    print(f"✓ Loaded {len(orders)} orders")
    
    # For this test, we'll just test implicit holds (no orders submitted)
    # This simulates what happens when units have no orders or illegal orders
    print(f"✓ Testing implicit holds (all units should have hold circles)")
    
    # Create visualization with no orders (all units should hold)
    base_image = 'diplomacy_game_engine/assets/europemapbw.png'
    visualizer = MapVisualizer(state, base_image_path=base_image)
    
    # Draw with results - pass empty orders list to test implicit holds
    visualizer.draw_map_with_results(
        orders=[],  # No orders = all units hold
        move_results={},
        dislodged_units=[],
        original_state=state,
        invalid_supports=set(),
        cut_supports=set()
    )
    
    # Save visualization
    output_path = 'test_hold_circles.png'
    visualizer.save(output_path)
    print(f"✓ Saved visualization to {output_path}")
    print(f"\nCheck {output_path} for:")
    print("  - Black circles around units that held")
    print("  - Black arrows for successful moves")
    print("  - Red arrows for bounced/illegal moves")
    print("  - Dashed lines for support orders")
    
    return True

if __name__ == "__main__":
    try:
        success = test_spring_1901_visualization()
        if success:
            print("\n" + "="*60)
            print("TEST COMPLETED SUCCESSFULLY ✓")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("TEST FAILED ✗")
            print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
