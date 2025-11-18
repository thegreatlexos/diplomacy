"""
Game manager for Diplomacy game engine.
Orchestrates game flow and phase progression.
"""

from typing import Dict, List, Optional
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.game_state import GameState, Season, create_starting_state
from diplomacy_game_engine.core.orders import Order, BuildOrder, OrderSet
from diplomacy_game_engine.core.resolver import (
    resolve_movement_phase,
    resolve_retreat_phase,
    resolve_winter_phase,
    ResolutionResult
)


class Game:
    """Main game controller for Diplomacy."""
    
    def __init__(self, game_state: Optional[GameState] = None):
        """
        Initialize a new game.
        
        Args:
            game_state: Optional existing game state. If None, creates standard 1901 start.
        """
        if game_state is None:
            self.state = create_starting_state()
        else:
            self.state = game_state
        
        self.pending_orders: Dict[str, Order] = {}
        self.last_resolution_result: Optional[ResolutionResult] = None
        self.game_history: List[GameState] = [self.state.clone()]
    
    def get_current_state(self) -> GameState:
        """Get the current game state."""
        return self.state
    
    def get_current_season(self) -> Season:
        """Get the current season."""
        return self.state.season
    
    def get_current_year(self) -> int:
        """Get the current year."""
        return self.state.year
    
    def submit_order(self, unit_id: str, order: Order) -> bool:
        """
        Submit an order for a unit.
        
        Args:
            unit_id: The ID of the unit
            order: The order to submit
            
        Returns:
            True if order was accepted, False otherwise
        """
        # Verify unit exists
        if unit_id not in self.state.units:
            return False
        
        # Verify order is valid for current phase
        if self.state.season in [Season.SPRING, Season.FALL]:
            # Movement phase - accept movement orders
            self.pending_orders[unit_id] = order
            return True
        elif self.state.season == Season.RETREAT:
            # Retreat phase - accept retreat/disband orders
            self.pending_orders[unit_id] = order
            return True
        
        return False
    
    def submit_build_order(self, power: Power, build_order: BuildOrder) -> bool:
        """
        Submit a build order during winter phase.
        
        Args:
            power: The power submitting the order
            build_order: The build order
            
        Returns:
            True if order was accepted, False otherwise
        """
        if self.state.season != Season.WINTER:
            return False
        
        # Store build orders by power
        power_key = power.value
        if power_key not in self.pending_orders:
            self.pending_orders[power_key] = []
        self.pending_orders[power_key].append(build_order)
        return True
    
    def get_pending_orders(self) -> Dict[str, Order]:
        """Get all pending orders."""
        return self.pending_orders.copy()
    
    def clear_orders(self) -> None:
        """Clear all pending orders."""
        self.pending_orders.clear()
    
    def advance_phase(self) -> Dict[str, str]:
        """
        Advance to the next phase, resolving current orders.
        
        Returns:
            Dictionary with resolution results and messages
        """
        results = {}
        
        if self.state.season == Season.SPRING or self.state.season == Season.FALL:
            # Remember which season we're in before resolving
            current_season = self.state.season
            
            # Resolve movement phase
            resolution = resolve_movement_phase(self.state, self.pending_orders)
            self.last_resolution_result = resolution
            self.state = resolution.new_state
            
            # Check if there are dislodged units
            if len(resolution.dislodged_units) > 0:
                self.state.season = Season.RETREAT
                results["phase"] = "Retreat phase - dislodged units must retreat or disband"
            else:
                # No retreats needed, advance to next season
                if current_season == Season.SPRING:
                    self.state.season = Season.FALL
                    results["phase"] = "Fall movement phase"
                else:
                    self.state.season = Season.WINTER
                    results["phase"] = "Winter adjustment phase"
            
            results.update(resolution.move_results)
            
        elif self.state.season == Season.RETREAT:
            # Resolve retreat phase
            self.state = resolve_retreat_phase(self.state, self.pending_orders)
            
            # After retreats, check which season we came from
            # Retreats after Spring -> Fall, Retreats after Fall -> Winter
            if self.state.year == 1901 and self.state.season == Season.RETREAT:
                # This is a bit tricky - we need to track which movement phase we came from
                # For now, assume Spring retreats -> Fall, Fall retreats -> Winter
                # TODO: Track this more explicitly
                self.state.season = Season.FALL
                results["phase"] = "Fall movement phase"
            else:
                self.state.season = Season.WINTER
                results["phase"] = "Winter adjustment phase"
        
        elif self.state.season == Season.WINTER:
            # Resolve winter adjustments
            self.state = resolve_winter_phase(self.state, self.pending_orders)
            
            # Advance to next year
            self.state.year += 1
            self.state.season = Season.SPRING
            results["phase"] = f"Spring {self.state.year} movement phase"
        
        # Clear pending orders
        self.clear_orders()
        
        # Save state to history
        self.game_history.append(self.state.clone())
        
        # Check for victory
        winner = self.state.check_victory()
        if winner:
            results["winner"] = f"{winner.value} has won the game!"
        
        return results
    
    def get_units_for_power(self, power: Power) -> List[str]:
        """Get all unit IDs for a specific power."""
        units = self.state.get_units_by_power(power)
        return [unit.get_id() for unit in units]
    
    def get_supply_center_count(self, power: Power) -> int:
        """Get the number of supply centers controlled by a power."""
        return self.state.get_sc_count(power)
    
    def get_game_summary(self) -> Dict[str, any]:
        """Get a summary of the current game state."""
        summary = {
            "year": self.state.year,
            "season": self.state.season.value,
            "powers": {}
        }
        
        for power in Power:
            summary["powers"][power.value] = {
                "supply_centers": self.get_supply_center_count(power),
                "units": len(self.get_units_for_power(power))
            }
        
        return summary
    
    def save_game(self, filepath: str) -> None:
        """Save the current game state to a file."""
        self.state.to_json(filepath)
    
    @staticmethod
    def load_game(filepath: str) -> 'Game':
        """Load a game from a file."""
        game_map = create_standard_map()
        state = GameState.from_json(filepath, game_map)
        return Game(state)
    
    def get_valid_orders_for_unit(self, unit_id: str) -> List[str]:
        """
        Get a list of valid order descriptions for a unit.
        Useful for testing and UI.
        """
        unit = self.state.units.get(unit_id)
        if unit is None:
            return []
        
        valid_orders = []
        
        # Always can hold
        valid_orders.append(f"{unit} H")
        
        # Get adjacent provinces for moves
        adjacent = self.state.game_map.get_adjacent_provinces(unit.location, unit.coast)
        for adj_prov, adj_coast in adjacent:
            province = self.state.game_map.get_province(adj_prov)
            if province is None:
                continue
            
            # Check if unit can move there
            from diplomacy_game_engine.core.game_state import UnitType
            if unit.unit_type == UnitType.ARMY and province.is_sea():
                continue
            if unit.unit_type == UnitType.FLEET and province.is_land():
                continue
            
            coast_str = f" ({adj_coast.value})" if adj_coast else ""
            valid_orders.append(f"{unit} -> {adj_prov}{coast_str}")
        
        # TODO: Add support and convoy order suggestions
        
        return valid_orders
    
    def get_phase_description(self) -> str:
        """Get a human-readable description of the current phase."""
        season_name = self.state.season.value
        
        if self.state.season == Season.SPRING:
            return f"Spring {self.state.year} - Movement Phase"
        elif self.state.season == Season.FALL:
            return f"Fall {self.state.year} - Movement Phase"
        elif self.state.season == Season.RETREAT:
            return f"{self.state.year} - Retreat Phase"
        elif self.state.season == Season.WINTER:
            return f"Winter {self.state.year} - Adjustment Phase"
        
        return f"{season_name} {self.state.year}"
    
    def needs_orders_from(self) -> List[Power]:
        """
        Determine which powers still need to submit orders.
        Returns list of powers that have units but haven't submitted all orders.
        """
        powers_needing_orders = []
        
        if self.state.season in [Season.SPRING, Season.FALL]:
            # Check which powers have units without orders
            for power in Power:
                units = self.state.get_units_by_power(power)
                for unit in units:
                    if unit.get_id() not in self.pending_orders:
                        if power not in powers_needing_orders:
                            powers_needing_orders.append(power)
                        break
        
        elif self.state.season == Season.RETREAT:
            # Check which powers have dislodged units without orders
            for dislodged in self.state.dislodged_units:
                if dislodged.unit.get_id() not in self.pending_orders:
                    if dislodged.unit.power not in powers_needing_orders:
                        powers_needing_orders.append(dislodged.unit.power)
        
        elif self.state.season == Season.WINTER:
            # Check which powers need to build/disband
            for power in Power:
                sc_count = self.state.get_sc_count(power)
                unit_count = self.state.get_unit_count(power)
                
                if sc_count != unit_count:
                    # This power needs to adjust
                    if power.value not in self.pending_orders:
                        powers_needing_orders.append(power)
        
        return powers_needing_orders
    
    def can_advance(self) -> bool:
        """Check if the game can advance to the next phase."""
        # For now, allow advancing even if not all orders are submitted
        # Missing orders will be treated as holds
        return True
    
    def get_board_state_string(self) -> str:
        """Get a simple string representation of the board state."""
        lines = []
        lines.append(f"\n{self.get_phase_description()}")
        lines.append("=" * 50)
        
        for power in Power:
            units = self.state.get_units_by_power(power)
            sc_count = self.get_supply_center_count(power)
            lines.append(f"\n{power.value}: {sc_count} SCs, {len(units)} units")
            for unit in units:
                lines.append(f"  {unit}")
        
        if self.state.dislodged_units:
            lines.append("\nDislodged Units:")
            for dislodged in self.state.dislodged_units:
                lines.append(f"  {dislodged.unit} (from {dislodged.dislodged_from})")
        
        return "\n".join(lines)
