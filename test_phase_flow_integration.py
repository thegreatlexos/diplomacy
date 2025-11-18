#!/usr/bin/env python3
"""
Integration test that simulates the exact flow of the game.
Tests state saving/loading and previous_season persistence.
"""

import os
import tempfile
from diplomacy_game_engine.core.game_state import GameState, Season, Unit, UnitType, DislodgedUnit
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.gamemaster.phase_manager import PhaseManager

def test_spring_retreat_fall_with_save_load():
    """
    Test the complete flow: Spring → Retreat → Fall
    Including state saving and loading to catch serialization issues
    """
    print("="*80)
    print("INTEGRATION TEST: Spring → Retreat → Fall (with save/load)")
    print("="*80)
    
    # Create temporary directory for state files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Create Spring state with dislodgements
        print("\n--- STEP 1: Spring Movement with Dislodgements ---")
        game_map = create_standard_map()
        state = GameState(game_map, year=1903, season=Season.SPRING)
        
        # Add dislodged unit
        dislodged_unit = Unit(Power.RUSSIA, UnitType.FLEET, "Rum", None)
        dislodged = DislodgedUnit(
            unit=dislodged_unit,
            dislodged_from="Rum",
            dislodger_origin="Bud",
            contested_provinces=set()
        )
        state.dislodged_units = [dislodged]
        
        print(f"✓ State: {state.season.value} {state.year}")
        print(f"  previous_season: {state.previous_season}")
        print(f"  Dislodged units: {len(state.dislodged_units)}")
        
        # Step 2: Save state (like gamemaster does after movement)
        print("\n--- STEP 2: Save State After Movement ---")
        state_path = os.path.join(temp_dir, "1903_spring_after.json")
        state.to_json(state_path)
        print(f"✓ Saved to: {state_path}")
        print(f"  Season in saved state: {state.season.value}")
        print(f"  previous_season in saved state: {state.previous_season}")
        
        # Step 3: Advance phase (changes season to RETREAT)
        print("\n--- STEP 3: Advance Phase (Spring → Retreat) ---")
        phase_manager = PhaseManager()
        has_dislodged = len(state.dislodged_units) > 0
        
        print(f"  has_dislodged: {has_dislodged}")
        phase_manager.advance_phase(state, has_dislodged)
        
        print(f"✓ After advance_phase:")
        print(f"  Season: {state.season.value}")
        print(f"  previous_season: {state.previous_season}")
        
        # Step 4: Set previous_season (like our fix does)
        print("\n--- STEP 4: Set previous_season and Save State ---")
        if state.season == Season.RETREAT and has_dislodged:
            state.previous_season = Season.SPRING
            print(f"✓ Set previous_season to Spring")
            
            # CRITICAL: Save state AGAIN with correct previous_season
            retreat_path = os.path.join(temp_dir, "1903_retreat_after.json")
            state.to_json(retreat_path)
            print(f"✓ Saved retreat state with previous_season")
        else:
            print(f"✗ ERROR: Season is {state.season.value}, not Retreat!")
            return False
        
        print(f"  previous_season: {state.previous_season.value}")
        
        # Step 5: Verify saved state has correct previous_season
        print("\n--- STEP 5: Verify Saved State ---")
        # Read the file back to verify
        with open(retreat_path, 'r') as f:
            import json
            saved_data = json.load(f)
            saved_prev_season = saved_data.get('previous_season')
            
        print(f"✓ Checking saved file:")
        print(f"  previous_season in file: {saved_prev_season}")
        
        if saved_prev_season != 'Spring':
            print(f"\n✗✗ BUG: previous_season not saved correctly!")
            print(f"  Expected: 'Spring', Got: {saved_prev_season}")
            return False
        
        print(f"✓ previous_season correctly saved to file")
        
        # Step 6: Load retreat state (simulating retreat phase start)
        print("\n--- STEP 6: Load Retreat State (simulating phase start) ---")
        loaded_state = GameState.from_json(retreat_path, game_map)
        
        print(f"✓ Loaded state:")
        print(f"  Season: {loaded_state.season.value}")
        print(f"  previous_season: {loaded_state.previous_season.value if loaded_state.previous_season else 'None'}")
        
        if not loaded_state.previous_season:
            print(f"\n✗✗ BUG FOUND: previous_season is None after loading!")
            print(f"  This means it's not being saved/loaded correctly")
            return False
        
        if loaded_state.previous_season != Season.SPRING:
            print(f"\n✗✗ BUG FOUND: previous_season is {loaded_state.previous_season.value}, not Spring!")
            return False
        
        print(f"✓ previous_season correctly preserved: {loaded_state.previous_season.value}")
        
        # Step 7: Advance to next phase (should go to FALL)
        print("\n--- STEP 7: Advance Phase (Retreat → Fall) ---")
        phase_manager.advance_phase(loaded_state, has_dislodged_units=False)
        
        print(f"✓ After advance_phase:")
        print(f"  Season: {loaded_state.season.value}")
        print(f"  previous_season: {loaded_state.previous_season}")
        
        # Step 8: Verify we're in Fall
        print("\n--- STEP 8: Verify Result ---")
        if loaded_state.season == Season.FALL:
            print(f"✓✓ SUCCESS: Correctly advanced to Fall!")
            return True
        else:
            print(f"✗✗ FAILED: Advanced to {loaded_state.season.value} instead of Fall!")
            return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PHASE FLOW INTEGRATION TEST")
    print("="*80)
    
    success = test_spring_retreat_fall_with_save_load()
    
    print("\n" + "="*80)
    print("TEST RESULT")
    print("="*80)
    
    if success:
        print("✓✓ TEST PASSED - Fix is working correctly! ✓✓")
    else:
        print("✗✗ TEST FAILED - Bug still exists ✗✗")
    
    print("="*80)
