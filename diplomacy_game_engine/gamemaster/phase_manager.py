"""
Phase manager for handling game phase transitions and logic.
"""

from typing import Dict, Optional
from diplomacy_game_engine.core.game_state import GameState, Season
from diplomacy_game_engine.core.map import Power
import logging

logger = logging.getLogger(__name__)


class PhaseManager:
    """Manages phase transitions and game flow logic."""
    
    @staticmethod
    def determine_next_phase(state: GameState, has_dislodged_units: bool) -> Season:
        """
        Determine the next phase based on current state.
        
        Args:
            state: Current game state
            has_dislodged_units: Whether there are dislodged units needing retreat
            
        Returns:
            The next season/phase
        """
        if state.season == Season.SPRING:
            if has_dislodged_units:
                return Season.RETREAT
            else:
                return Season.FALL
        
        elif state.season == Season.FALL:
            if has_dislodged_units:
                return Season.RETREAT
            else:
                return Season.WINTER
        
        elif state.season == Season.RETREAT:
            # After retreat, use previous_season to determine next phase
            if state.previous_season == Season.SPRING:
                return Season.FALL
            elif state.previous_season == Season.FALL:
                return Season.WINTER
            else:
                # Fallback: assume Fall if previous_season not set
                logger.warning("Retreat phase without previous_season set, defaulting to Winter")
                return Season.WINTER
        
        elif state.season == Season.WINTER:
            return Season.SPRING
        
        return Season.SPRING  # Default fallback
    
    @staticmethod
    def advance_phase(state: GameState, has_dislodged_units: bool) -> None:
        """
        Advance the game state to the next phase.
        
        Args:
            state: Game state to advance
            has_dislodged_units: Whether there are dislodged units
        """
        logger.info(f"DEBUG advance_phase: Current season: {state.season.value}, previous_season: {state.previous_season}, has_dislodged: {has_dislodged_units}")
        
        next_season = PhaseManager.determine_next_phase(state, has_dislodged_units)
        
        logger.info(f"DEBUG advance_phase: determine_next_phase returned: {next_season.value}")
        logger.info(f"Advancing from {state.season.value} {state.year} to {next_season.value}")
        
        # Update season
        state.season = next_season
        
        # Increment year if moving to Spring
        if next_season == Season.SPRING:
            state.year += 1
            logger.info(f"New year: {state.year}")
        
        # Clear dislodged units and previous_season when leaving retreat phase
        if next_season != Season.RETREAT:
            state.dislodged_units.clear()
            if state.previous_season:
                logger.info(f"Leaving retreat phase, was from {state.previous_season.value}")
            state.previous_season = None
    
    @staticmethod
    def calculate_adjustments(state: GameState) -> Dict[Power, int]:
        """
        Calculate build/disband adjustments for each power.
        
        Returns:
            Dictionary mapping Power to adjustment count
            Positive = builds needed, Negative = disbands needed, 0 = no adjustment
        """
        adjustments = {}
        
        for power in Power:
            sc_count = state.get_sc_count(power)
            unit_count = state.get_unit_count(power)
            adjustment = sc_count - unit_count
            
            if adjustment != 0:
                adjustments[power] = adjustment
                logger.info(f"{power.value}: {sc_count} SCs, {unit_count} units, adjustment: {adjustment:+d}")
        
        return adjustments
    
    @staticmethod
    def update_sc_ownership(state: GameState) -> None:
        """
        Update supply center ownership based on unit positions.
        Only called after Fall movement phase.
        """
        logger.info("Updating supply center ownership")
        
        changes = []
        
        for province in state.game_map.get_supply_centers():
            abbr = province.abbreviation
            unit = state.get_unit_at(abbr)
            
            if unit:
                # Unit occupies this SC
                current_owner = state.supply_centers.get(abbr)
                if current_owner != unit.power:
                    changes.append((abbr, current_owner, unit.power))
                    state.set_sc_owner(abbr, unit.power)
            # If no unit, ownership doesn't change
        
        if changes:
            logger.info(f"Supply center ownership changes:")
            for abbr, old_owner, new_owner in changes:
                old_str = old_owner.value if old_owner else "Neutral"
                logger.info(f"  {abbr}: {old_str} -> {new_owner.value}")
        else:
            logger.info("No supply center ownership changes")
    
    @staticmethod
    def check_victory(state: GameState) -> Optional[Power]:
        """
        Check if any power has achieved victory (18 SCs).
        
        Returns:
            The winning power, or None if no winner yet
        """
        for power in Power:
            sc_count = state.get_sc_count(power)
            if sc_count >= 18:
                logger.info(f"VICTORY: {power.value} has {sc_count} supply centers!")
                return power
        
        return None
    
    @staticmethod
    def needs_press_phase(season: Season) -> bool:
        """
        Determine if the current season includes press rounds.
        
        Args:
            season: The current season
            
        Returns:
            True if press rounds should occur, False otherwise
        """
        return season in [Season.SPRING, Season.FALL]
    
    @staticmethod
    def get_press_round_count() -> int:
        """Get the number of press rounds per movement phase."""
        return 3
