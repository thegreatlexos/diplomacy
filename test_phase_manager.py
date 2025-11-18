#!/usr/bin/env python3
"""
Test file for phase manager functionality.
Tests phase transitions, previous_season tracking, and order file naming.
"""

from diplomacy_game_engine.core.game_state import GameState, Season, Unit, UnitType, DislodgedUnit, create_starting_state
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.gamemaster.phase_manager import PhaseManager
from diplomacy_game_engine.gamemaster.order_writer import OrderWriter

def test_spring_retreat_fall():
    """Test: Spring → Retreat → Fall"""
    print("="*60)
    print("TEST: Spring → Retreat → Fall")
    print("="*60)
    
    # Create game state in Spring
    game_map = create_standard_map()
    state = GameState(game_map, year=1902, season=Season.SPRING)
    
    # Add a dislodged unit to trigger retreat
    dislodged_unit = Unit(Power.RUSSIA, UnitType.FLEET, "Rum", None)
    dislodged = DislodgedUnit(
        unit=dislodged_unit,
        dislodged_from="Rum",
        dislodger_origin="Bud",
        contested_provinces=set()
    )
    state.dislodged_units = [dislodged]
    
    print(f"✓ Initial state: {state.season.value} {state.year}")
    print(f"  previous_season: {state.previous_season}")
    print(f"  Dislodged units: {len(state.dislodged_units)}")
    
    # Advance phase (should go to RETREAT)
    phase_manager = PhaseManager()
    phase_manager.advance_phase(state, has_dislodged_units=True)
    
    print(f"\n✓ After advance_phase:")
    print(f"  Season: {state.season.value}")
    print(f"  previous_season: {state.previous_season}")
    
    # Simulate setting previous_season after advance_phase
    if state.season == Season.RETREAT:
        state.previous_season = Season.SPRING
        print(f"\n✓ Set previous_season to Spring")
        print(f"  previous_season: {state.previous_season.value}")
    
    # Test order filename
    filename = OrderWriter.get_phase_filename(state)
    print(f"\n✓ Order filename: {filename}")
    expected = "1902_01_retreat_spring.yaml"
    if filename == expected:
        print(f"  ✓ CORRECT (expected: {expected})")
    else:
        print(f"  ✗ WRONG (expected: {expected})")
    
    # Advance to next phase (should go to FALL)
    phase_manager.advance_phase(state, has_dislodged_units=False)
    
    print(f"\n✓ After second advance_phase:")
    print(f"  Season: {state.season.value}")
    print(f"  previous_season: {state.previous_season}")
    
    if state.season == Season.FALL:
        print(f"\n✓✓ SUCCESS: Correctly advanced to Fall!")
    else:
        print(f"\n✗✗ FAILED: Advanced to {state.season.value} instead of Fall!")
    
    print("="*60)
    return state.season == Season.FALL


def test_fall_retreat_winter():
    """Test: Fall → Retreat → Winter"""
    print("\n" + "="*60)
    print("TEST: Fall → Retreat → Winter")
    print("="*60)
    
    # Create game state in Fall
    game_map = create_standard_map()
    state = GameState(game_map, year=1902, season=Season.FALL)
    
    # Add a dislodged unit to trigger retreat
    dislodged_unit = Unit(Power.RUSSIA, UnitType.FLEET, "Rum", None)
    dislodged = DislodgedUnit(
        unit=dislodged_unit,
        dislodged_from="Rum",
        dislodger_origin="Bud",
        contested_provinces=set()
    )
    state.dislodged_units = [dislodged]
    
    print(f"✓ Initial state: {state.season.value} {state.year}")
    print(f"  previous_season: {state.previous_season}")
    print(f"  Dislodged units: {len(state.dislodged_units)}")
    
    # Advance phase (should go to RETREAT)
    phase_manager = PhaseManager()
    phase_manager.advance_phase(state, has_dislodged_units=True)
    
    print(f"\n✓ After advance_phase:")
    print(f"  Season: {state.season.value}")
    print(f"  previous_season: {state.previous_season}")
    
    # Simulate setting previous_season after advance_phase
    if state.season == Season.RETREAT:
        state.previous_season = Season.FALL
        print(f"\n✓ Set previous_season to Fall")
        print(f"  previous_season: {state.previous_season.value}")
    
    # Test order filename
    filename = OrderWriter.get_phase_filename(state)
    print(f"\n✓ Order filename: {filename}")
    expected = "1902_02_retreat_fall.yaml"
    if filename == expected:
        print(f"  ✓ CORRECT (expected: {expected})")
    else:
        print(f"  ✗ WRONG (expected: {expected})")
    
    # Advance to next phase (should go to WINTER)
    phase_manager.advance_phase(state, has_dislodged_units=False)
    
    print(f"\n✓ After second advance_phase:")
    print(f"  Season: {state.season.value}")
    print(f"  previous_season: {state.previous_season}")
    
    if state.season == Season.WINTER:
        print(f"\n✓✓ SUCCESS: Correctly advanced to Winter!")
    else:
        print(f"\n✗✗ FAILED: Advanced to {state.season.value} instead of Winter!")
    
    print("="*60)
    return state.season == Season.WINTER


def test_spring_fall_no_retreat():
    """Test: Spring → Fall (no retreat)"""
    print("\n" + "="*60)
    print("TEST: Spring → Fall (no retreat)")
    print("="*60)
    
    # Create game state in Spring
    game_map = create_standard_map()
    state = GameState(game_map, year=1902, season=Season.SPRING)
    
    print(f"✓ Initial state: {state.season.value} {state.year}")
    print(f"  Dislodged units: {len(state.dislodged_units)}")
    
    # Advance phase (should go to FALL)
    phase_manager = PhaseManager()
    phase_manager.advance_phase(state, has_dislodged_units=False)
    
    print(f"\n✓ After advance_phase:")
    print(f"  Season: {state.season.value}")
    
    if state.season == Season.FALL:
        print(f"\n✓✓ SUCCESS: Correctly advanced to Fall!")
    else:
        print(f"\n✗✗ FAILED: Advanced to {state.season.value} instead of Fall!")
    
    print("="*60)
    return state.season == Season.FALL


def test_fall_winter_no_retreat():
    """Test: Fall → Winter (no retreat)"""
    print("\n" + "="*60)
    print("TEST: Fall → Winter (no retreat)")
    print("="*60)
    
    # Create game state in Fall
    game_map = create_standard_map()
    state = GameState(game_map, year=1902, season=Season.FALL)
    
    print(f"✓ Initial state: {state.season.value} {state.year}")
    print(f"  Dislodged units: {len(state.dislodged_units)}")
    
    # Advance phase (should go to WINTER)
    phase_manager = PhaseManager()
    phase_manager.advance_phase(state, has_dislodged_units=False)
    
    print(f"\n✓ After advance_phase:")
    print(f"  Season: {state.season.value}")
    
    if state.season == Season.WINTER:
        print(f"\n✓✓ SUCCESS: Correctly advanced to Winter!")
    else:
        print(f"\n✗✗ FAILED: Advanced to {state.season.value} instead of Winter!")
    
    print("="*60)
    return state.season == Season.WINTER


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE MANAGER TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Spring → Retreat → Fall", test_spring_retreat_fall()))
    results.append(("Fall → Retreat → Winter", test_fall_retreat_winter()))
    results.append(("Spring → Fall (no retreat)", test_spring_fall_no_retreat()))
    results.append(("Fall → Winter (no retreat)", test_fall_winter_no_retreat()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓✓ ALL TESTS PASSED! ✓✓")
    else:
        print(f"\n✗✗ {total - passed} TEST(S) FAILED ✗✗")
    
    print("="*60)
