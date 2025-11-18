"""
Resolution engine for Diplomacy game engine.
Handles order adjudication and conflict resolution.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

from diplomacy_game_engine.core.map import Map, Coast
from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, DislodgedUnit, Season
from diplomacy_game_engine.core.orders import (
    Order, HoldOrder, MoveOrder, SupportOrder, ConvoyOrder,
    RetreatOrder, DisbandOrder, BuildOrder
)


@dataclass
class MoveAttempt:
    """Represents a unit attempting to move to a province."""
    unit: Unit
    origin: str
    destination: str
    dest_coast: Optional[Coast]
    via_convoy: bool
    strength: int = 1
    supports: List[Unit] = field(default_factory=list)
    is_successful: bool = False
    is_bounced: bool = False


@dataclass
class ResolutionResult:
    """Result of resolving a movement phase."""
    new_state: GameState
    dislodged_units: List[DislodgedUnit]
    move_results: Dict[str, str]  # unit_id -> result description
    contested_provinces: Set[str]  # Provinces with bounces
    invalid_supports: Set[str]  # unit_ids of units with invalid support orders
    cut_supports: Set[str]  # unit_ids of units whose support was cut
    illegal_orders: List[str] = field(default_factory=list)  # Descriptions of illegal orders


class MovementResolver:
    """Resolves movement phase orders."""
    
    def __init__(self, game_state: GameState, orders: Dict[str, Order]):
        self.game_state = game_state
        self.orders = orders
        self.game_map = game_state.game_map
        
        # Track move attempts by destination
        self.moves_to_province: Dict[str, List[MoveAttempt]] = {}
        
        # Track which supports have been cut
        self.cut_supports: Set[str] = set()  # unit_ids
        
        # Track convoy chains
        self.convoy_routes: Dict[str, List[Unit]] = {}  # army_unit_id -> list of fleets
        
        # Track illegal orders
        self.illegal_orders: List[str] = []
    
    def resolve(self) -> ResolutionResult:
        """
        Main resolution method following the standard Diplomacy adjudication process.
        """
        # Phase 1: Identify all move attempts
        self._identify_moves()
        
        # Phase 2: Build convoy routes
        self._build_convoy_routes()
        
        # Phase 3: Calculate initial strengths
        self._calculate_strengths()
        
        # Phase 4: Apply support cutting
        self._apply_support_cutting()
        
        # Phase 5: Recalculate strengths after support cuts
        self._calculate_strengths()
        
        # Phase 6: Determine move outcomes
        self._determine_outcomes()
        
        # Phase 7: Apply successful moves and identify dislodged units
        return self._apply_moves()
    
    def _identify_moves(self) -> None:
        """Identify all move attempts from orders."""
        for unit_id, order in self.orders.items():
            unit = self.game_state.units.get(unit_id)
            if unit is None:
                continue
            
            if isinstance(order, MoveOrder):
                # Validate the move before creating attempt
                if self._is_move_legal(unit, order):
                    attempt = MoveAttempt(
                        unit=unit,
                        origin=unit.location,
                        destination=order.destination,
                        dest_coast=order.dest_coast,
                        via_convoy=order.via_convoy
                    )
                    
                    if order.destination not in self.moves_to_province:
                        self.moves_to_province[order.destination] = []
                    self.moves_to_province[order.destination].append(attempt)
                else:
                    # Track illegal move order
                    reason = self._get_illegal_move_reason(unit, order)
                    self.illegal_orders.append(f"{unit.power.value} {unit.unit_type.value[0]} {unit.location} → {order.destination}: {reason}")
    
    def _is_move_legal(self, unit: Unit, order: MoveOrder) -> bool:
        """
        Check if a move order is legal according to Diplomacy rules.
        Illegal moves are treated as hold orders.
        """
        # Check for move to same location (illegal)
        if unit.location == order.destination:
            return False
        
        # Get destination province
        dest_province = self.game_map.get_province(order.destination)
        if dest_province is None:
            return False
        
        # Check unit type compatibility with destination
        if unit.unit_type == UnitType.ARMY:
            # Armies cannot move to sea provinces unless via convoy
            if dest_province.is_sea() and not order.via_convoy:
                return False
        elif unit.unit_type == UnitType.FLEET:
            # Fleets can move to sea provinces and coastal provinces, but not pure land provinces
            if dest_province.is_land() and not dest_province.is_coastal():
                return False
        
        # If not via convoy, check adjacency
        if not order.via_convoy:
            if not self.game_map.is_adjacent(
                unit.location,
                order.destination,
                unit.coast,
                order.dest_coast
            ):
                return False
        
        return True
    
    def _get_illegal_move_reason(self, unit: Unit, order: MoveOrder) -> str:
        """Get a human-readable reason why a move is illegal."""
        # Check for move to same location
        if unit.location == order.destination:
            return "Cannot move to same location"
        
        # Get destination province
        dest_province = self.game_map.get_province(order.destination)
        if dest_province is None:
            return f"Destination province '{order.destination}' does not exist"
        
        # Check unit type compatibility
        if unit.unit_type == UnitType.ARMY:
            if dest_province.is_sea() and not order.via_convoy:
                return f"Army cannot move to sea province {order.destination} (no convoy specified)"
        elif unit.unit_type == UnitType.FLEET:
            if dest_province.is_land() and not dest_province.is_coastal():
                return f"Fleet cannot move to inland province {order.destination}"
        
        # Check adjacency
        if not order.via_convoy:
            if not self.game_map.is_adjacent(unit.location, order.destination, unit.coast, order.dest_coast):
                return f"Not adjacent: {unit.location} and {order.destination}"
        
        return "Unknown reason"
    
    def _build_convoy_routes(self) -> None:
        """Build convoy routes for armies moving via convoy."""
        for unit_id, order in self.orders.items():
            if isinstance(order, ConvoyOrder):
                fleet = order.unit
                army_loc = order.convoyed_army_location
                
                # Find the army being convoyed
                army_unit_id = None
                for uid, u in self.game_state.units.items():
                    if u.location == army_loc and u.unit_type == UnitType.ARMY:
                        army_unit_id = uid
                        break
                
                if army_unit_id:
                    if army_unit_id not in self.convoy_routes:
                        self.convoy_routes[army_unit_id] = []
                    self.convoy_routes[army_unit_id].append(fleet)
    
    def _calculate_strengths(self) -> None:
        """Calculate attack/defense strengths for all moves."""
        # Reset strengths
        for attempts in self.moves_to_province.values():
            for attempt in attempts:
                attempt.strength = 1
                attempt.supports = []
        
        # Add support strengths
        for unit_id, order in self.orders.items():
            if isinstance(order, SupportOrder):
                supporting_unit = order.unit
                
                # Skip if support has been cut
                if unit_id in self.cut_supports:
                    continue
                
                # Validate support before applying
                if not self._is_support_valid(order):
                    continue
                
                # Find the move being supported
                target_dest = order.destination if order.destination else order.supported_unit_location
                
                if target_dest in self.moves_to_province:
                    for attempt in self.moves_to_province[target_dest]:
                        if attempt.origin == order.supported_unit_location:
                            # This support applies to this move
                            attempt.strength += 1
                            attempt.supports.append(supporting_unit)
                            break
                else:
                    # Support to hold - add strength to defender
                    # This is handled in _determine_outcomes
                    pass
    
    def _is_support_valid(self, order: SupportOrder) -> bool:
        """
        Check if a support order is valid according to Diplomacy rules.
        A support is invalid if the supporting unit cannot reach the destination.
        """
        supporting_unit = order.unit
        
        # Check for self-support (invalid)
        if order.is_support_hold():
            # Support hold: can't support yourself
            if supporting_unit.location == order.supported_unit_location:
                return False
        else:
            # Support move: can't support a move to your own location
            if supporting_unit.location == order.destination:
                return False
            
            # CRITICAL: Verify the supported unit is actually moving to the destination
            # Find the unit at the supported location
            supported_unit = self.game_state.get_unit_at(order.supported_unit_location)
            if supported_unit:
                supported_unit_id = supported_unit.get_id()
                supported_order = self.orders.get(supported_unit_id)
                
                # Check if the supported unit has a move order to the claimed destination
                if isinstance(supported_order, MoveOrder):
                    if supported_order.destination != order.destination:
                        # Unit is moving, but not to the destination claimed in support
                        return False
                # If no move order, the unit is holding - this is valid for support to hold
                # (support to hold doesn't specify a destination)
            else:
                # No unit at the supported location
                return False
        
        # Determine the target location (destination for move support, supported location for hold support)
        target_location = order.destination if order.destination else order.supported_unit_location
        target_coast = order.dest_coast if order.destination else order.supported_unit_coast
        
        # Check if supporting unit can reach the target
        if not self.game_map.is_adjacent(
            supporting_unit.location,
            target_location,
            supporting_unit.coast,
            target_coast
        ):
            return False
        
        # Check unit type compatibility with target
        target_province = self.game_map.get_province(target_location)
        if target_province is None:
            return False
        
        # Army cannot support moves to sea provinces (unless the army could theoretically move there via convoy)
        if supporting_unit.unit_type == UnitType.ARMY and target_province.is_sea():
            return False
        
        # Fleet cannot support moves to pure inland provinces (but CAN support coastal provinces)
        if supporting_unit.unit_type == UnitType.FLEET and target_province.is_land() and not target_province.is_coastal():
            return False
        
        return True
    
    def _apply_support_cutting(self) -> None:
        """
        Apply support cutting rules.
        A support is cut if the supporting unit is attacked by any unit,
        UNLESS the attack comes from the province being supported to.
        """
        for unit_id, order in self.orders.items():
            if isinstance(order, SupportOrder):
                supporting_unit = order.unit
                support_location = supporting_unit.location
                
                # Check if this location is being attacked
                if support_location in self.moves_to_province:
                    for attack in self.moves_to_province[support_location]:
                        # Support is cut unless attack is from the supported destination
                        if order.destination and attack.origin == order.destination:
                            # Attack from supported destination doesn't cut (self-attack exception)
                            continue
                        
                        # If we reach here, the attack cuts the support
                        # (The attack must be legal since it was added to moves_to_province)
                        self.cut_supports.add(unit_id)
                        break
    
    def _determine_outcomes(self) -> None:
        """Determine which moves succeed, fail, or bounce."""
        # First pass: determine outcomes for non-convoy moves
        # We need to resolve moves iteratively because head-to-head situations
        # require knowing if the defender's move succeeds
        
        # Track which moves we've already resolved
        resolved_destinations = set()
        
        # Keep iterating until all moves are resolved
        max_iterations = 100  # Safety limit
        iteration = 0
        
        while len(resolved_destinations) < len(self.moves_to_province) and iteration < max_iterations:
            iteration += 1
            made_progress = False
            
            for destination, attempts in self.moves_to_province.items():
                if destination in resolved_destinations:
                    continue
                
                if len(attempts) == 0:
                    resolved_destinations.add(destination)
                    continue
                
                # Skip convoy moves in first pass
                if all(a.via_convoy for a in attempts):
                    continue
                
                # Get the defending unit (if any)
                defender = self.game_state.get_unit_at(destination)
                defense_strength = 0  # Default to 0 if no defender
                
                # Check if defender is moving out successfully
                defender_moving_out_successfully = False
                if defender:
                    defender_id = defender.get_id()
                    defender_order = self.orders.get(defender_id)
                    if isinstance(defender_order, MoveOrder) and self._is_move_legal(defender, defender_order):
                        # Defender has a legal move order - check if destination is resolved
                        defender_dest = defender_order.destination
                        if defender_dest in self.moves_to_province:
                            # Check if defender's destination has been resolved
                            if defender_dest not in resolved_destinations:
                                # Can't resolve this yet - need to know if defender's move succeeds
                                continue
                            
                            # Check if defender's move succeeded
                            for defender_attempt in self.moves_to_province[defender_dest]:
                                if defender_attempt.unit.get_id() == defender_id:
                                    if defender_attempt.is_successful:
                                        defender_moving_out_successfully = True
                                    break
                        else:
                            # Defender moving to uncontested location - succeeds
                            defender_moving_out_successfully = True
                
                # Calculate defense strength
                if defender and not defender_moving_out_successfully:
                    defense_strength = 1  # Base defense strength
                    for unit_id, order in self.orders.items():
                        if isinstance(order, SupportOrder) and order.is_support_hold():
                            if order.supported_unit_location == destination:
                                if unit_id not in self.cut_supports and self._is_support_valid(order):
                                    defense_strength += 1
                
                # Find the strongest attacker(s)
                if len(attempts) == 1:
                    # Single attacker
                    attempt = attempts[0]
                    
                    # Skip convoy validation for now - will do in second pass
                    if attempt.via_convoy:
                        continue
                    
                    # Compare strength
                    if attempt.strength > defense_strength:
                        attempt.is_successful = True
                    else:
                        attempt.is_bounced = True
                    
                    resolved_destinations.add(destination)
                    made_progress = True
                else:
                    # Multiple attackers - find max strength
                    max_strength = max(a.strength for a in attempts if not a.via_convoy)
                    strongest = [a for a in attempts if a.strength == max_strength and not a.via_convoy]
                    
                    if len(strongest) == 1 and strongest[0].strength > defense_strength:
                        # Single strongest attacker wins
                        strongest[0].is_successful = True
                        for a in attempts:
                            if a != strongest[0] and not a.via_convoy:
                                a.is_bounced = True
                    else:
                        # Tie or not strong enough - all bounce
                        for a in attempts:
                            if not a.via_convoy:
                                a.is_bounced = True
                    
                    resolved_destinations.add(destination)
                    made_progress = True
            
            if not made_progress:
                # No progress made - resolve remaining as bounces to avoid infinite loop
                for destination, attempts in self.moves_to_province.items():
                    if destination not in resolved_destinations:
                        for a in attempts:
                            if not a.via_convoy and not a.is_successful and not a.is_bounced:
                                a.is_bounced = True
                        resolved_destinations.add(destination)
        
        # Second pass: validate convoys and determine convoy move outcomes
        for destination, attempts in self.moves_to_province.items():
            for attempt in attempts:
                if attempt.via_convoy and not attempt.is_successful and not attempt.is_bounced:
                    # Check convoy validity NOW (after other moves are resolved)
                    if not self._is_convoy_valid(attempt):
                        attempt.is_bounced = True
                        continue
                    
                    # Get defender info
                    defender = self.game_state.get_unit_at(destination)
                    defense_strength = 0
                    
                    if defender:
                        defense_strength = 1
                        for unit_id, order in self.orders.items():
                            if isinstance(order, SupportOrder) and order.is_support_hold():
                                if order.supported_unit_location == destination:
                                    if unit_id not in self.cut_supports and self._is_support_valid(order):
                                        defense_strength += 1
                    
                    # Check if defender is moving out
                    if defender:
                        defender_id = defender.get_id()
                        defender_order = self.orders.get(defender_id)
                        if isinstance(defender_order, MoveOrder) and self._is_move_legal(defender, defender_order):
                            defense_strength = 0
                    
                    # Determine outcome
                    # If defender is moving out (defense_strength = 0), attacker succeeds
                    # If defender is holding, attacker needs > defender strength
                    if defense_strength == 0 or attempt.strength > defense_strength:
                        attempt.is_successful = True
                    else:
                        attempt.is_bounced = True
    
    def _find_convoy_path(self, origin: str, destination: str, convoy_fleets: List[Unit]) -> bool:
        """
        Check if convoy fleets form a valid connected path from origin to destination.
        Uses BFS to traverse through adjacent sea zones where convoying fleets are located.
        """
        from collections import deque
        
        # Get the set of sea zones where we have convoying fleets
        fleet_zones = {fleet.location for fleet in convoy_fleets}
        
        # BFS to find path from origin to destination through fleet zones
        queue = deque([origin])
        visited = {origin}
        
        while queue:
            current = queue.popleft()
            
            # Check if we reached the destination
            if current == destination:
                return True
            
            # Get adjacent provinces
            adjacent = self.game_map.get_adjacent_provinces(current, None)
            
            for adj in adjacent:
                if adj in visited:
                    continue
                
                # Can move to destination directly if adjacent
                if adj == destination:
                    return True
                
                # Can move through sea zones where we have convoying fleets
                adj_province = self.game_map.get_province(adj)
                if adj_province and adj_province.is_sea() and adj in fleet_zones:
                    visited.add(adj)
                    queue.append(adj)
        
        return False
    
    def _is_convoy_valid(self, attempt: MoveAttempt) -> bool:
        """
        Check if a convoy route is valid.
        1. Fleets must form a connected path from origin to destination
        2. At least one fleet in the path must not be dislodged
        """
        army_id = attempt.unit.get_id()
        
        if army_id not in self.convoy_routes:
            return False
        
        convoy_fleets = self.convoy_routes[army_id]
        
        if len(convoy_fleets) == 0:
            return False
        
        # Check if fleets form a valid connected path
        if not self._find_convoy_path(attempt.origin, attempt.destination, convoy_fleets):
            return False
        
        # Check if at least one fleet in the path is not dislodged
        for fleet in convoy_fleets:
            fleet_location = fleet.location
            
            # Check if fleet location is being successfully attacked
            is_dislodged = False
            if fleet_location in self.moves_to_province:
                for attack in self.moves_to_province[fleet_location]:
                    if attack.is_successful:
                        is_dislodged = True
                        break
            
            # If at least one fleet survives, convoy succeeds
            if not is_dislodged:
                return True
        
        # All fleets dislodged - convoy fails
        return False
    
    def _apply_moves(self) -> ResolutionResult:
        """Apply successful moves and create new game state."""
        new_state = self.game_state.clone()
        dislodged_units = []
        move_results = {}
        contested_provinces = set()
        invalid_supports = set()
        
        # Track which supports are invalid
        for unit_id, order in self.orders.items():
            if isinstance(order, SupportOrder):
                if not self._is_support_valid(order):
                    invalid_supports.add(unit_id)
        
        # Track which provinces had bounces
        for destination, attempts in self.moves_to_province.items():
            if any(a.is_bounced for a in attempts):
                contested_provinces.add(destination)
        
        # Apply successful moves
        for destination, attempts in self.moves_to_province.items():
            for attempt in attempts:
                unit_id = attempt.unit.get_id()
                
                if attempt.is_successful:
                    # Check if we're dislodging a defender
                    defender = self.game_state.get_unit_at(destination)
                    if defender and defender.get_id() != unit_id:
                        # Check if defender is moving out
                        defender_id = defender.get_id()
                        defender_order = self.orders.get(defender_id)
                        defender_moving_out = False
                        
                        if isinstance(defender_order, MoveOrder) and self._is_move_legal(defender, defender_order):
                            # Defender is moving out - check if their move succeeded
                            defender_dest = defender_order.destination
                            if defender_dest in self.moves_to_province:
                                for defender_attempt in self.moves_to_province[defender_dest]:
                                    if defender_attempt.unit.get_id() == defender_id and defender_attempt.is_successful:
                                        defender_moving_out = True
                                        break
                        
                        # Only dislodge if defender is NOT moving out
                        if not defender_moving_out:
                            # Defender is dislodged
                            dislodged = DislodgedUnit(
                                unit=defender,
                                dislodged_from=destination,
                                dislodger_origin=attempt.origin,
                                contested_provinces=contested_provinces
                            )
                            dislodged_units.append(dislodged)
                            new_state.remove_unit(defender.get_id())
                    
                    # Move the unit
                    new_state.remove_unit(unit_id)
                    new_unit = Unit(
                        attempt.unit.power,
                        attempt.unit.unit_type,
                        destination,
                        attempt.dest_coast
                    )
                    new_state.add_unit(new_unit)
                    
                    move_results[unit_id] = f"Successfully moved to {destination}"
                    
                    # Update supply center ownership if applicable (only in Fall)
                    if self.game_state.season == Season.FALL:
                        province = self.game_map.get_province(destination)
                        if province and province.is_supply_center:
                            new_state.set_sc_owner(destination, attempt.unit.power)
                
                elif attempt.is_bounced:
                    move_results[unit_id] = f"Bounced from {destination}"
        
        # Units that didn't move stay in place
        for unit_id, unit in self.game_state.units.items():
            if unit_id not in move_results:
                move_results[unit_id] = "Held position"
        
        # Update SC ownership for ALL units on supply centers at end of Fall
        if self.game_state.season == Season.FALL:
            for unit in new_state.units.values():
                province = self.game_map.get_province(unit.location)
                if province and province.is_supply_center:
                    new_state.set_sc_owner(unit.location, unit.power)
        
        new_state.dislodged_units = dislodged_units
        
        return ResolutionResult(
            new_state=new_state,
            dislodged_units=dislodged_units,
            move_results=move_results,
            contested_provinces=contested_provinces,
            invalid_supports=invalid_supports,
            cut_supports=self.cut_supports,
            illegal_orders=self.illegal_orders
        )


class RetreatResolver:
    """Resolves retreat phase orders."""
    
    def __init__(self, game_state: GameState, retreat_orders: Dict[str, Order]):
        self.game_state = game_state
        self.retreat_orders = retreat_orders
    
    def resolve(self) -> GameState:
        """Resolve retreat orders."""
        new_state = self.game_state.clone()
        
        # Track retreat destinations to detect conflicts
        retreat_destinations: Dict[str, List[DislodgedUnit]] = {}
        
        for dislodged in self.game_state.dislodged_units:
            unit_id = dislodged.unit.get_id()
            order = self.retreat_orders.get(unit_id)
            
            if isinstance(order, RetreatOrder):
                dest = order.destination
                
                # Validate retreat destination
                valid_dests = dislodged.get_valid_retreat_destinations(self.game_state.game_map, self.game_state)
                
                # Check if destination is valid (occupied check is now done in get_valid_retreat_destinations)
                if dest in valid_dests:
                    if dest not in retreat_destinations:
                        retreat_destinations[dest] = []
                    retreat_destinations[dest].append(dislodged)
                else:
                    # Invalid retreat or occupied destination - unit is disbanded
                    pass
            else:
                # No retreat order or disband order - unit is disbanded
                pass
        
        # Apply retreats, disbanding units that conflict
        for dest, units in retreat_destinations.items():
            if len(units) == 1:
                # Single unit retreats successfully
                dislodged = units[0]
                new_unit = Unit(
                    dislodged.unit.power,
                    dislodged.unit.unit_type,
                    dest,
                    None  # TODO: Handle coast for retreats
                )
                new_state.add_unit(new_unit)
            else:
                # Multiple units trying to retreat to same place - all disbanded
                # Explicitly do nothing - units are not added to new_state
                pass
        
        # Clear dislodged units list
        new_state.dislodged_units = []
        
        return new_state


class WinterResolver:
    """Resolves winter adjustment phase."""
    
    def __init__(self, game_state: GameState, build_orders: Dict[str, List[BuildOrder]], 
                 disband_orders: Optional[Dict[str, List[str]]] = None):
        self.game_state = game_state
        self.build_orders = build_orders  # power -> list of build orders
        self.disband_orders = disband_orders or {}  # power -> list of unit_ids to disband
    
    def resolve(self) -> GameState:
        """Resolve winter adjustments."""
        new_state = self.game_state.clone()
        
        from diplomacy_game_engine.core.map import Power
        
        for power in Power:
            sc_count = new_state.get_sc_count(power)
            unit_count = new_state.get_unit_count(power)
            
            if unit_count < sc_count:
                # Can build units
                builds_needed = sc_count - unit_count
                power_builds = self.build_orders.get(power.value, [])
                
                builds_applied = 0
                for build_order in power_builds:
                    if builds_applied >= builds_needed:
                        break
                    
                    if build_order.is_valid(new_state):
                        new_unit = Unit(
                            build_order.power,
                            build_order.unit_type,
                            build_order.location,
                            build_order.coast
                        )
                        new_state.add_unit(new_unit)
                        builds_applied += 1
            
            elif unit_count > sc_count:
                # Must disband units
                disbands_needed = unit_count - sc_count
                power_units = new_state.get_units_by_power(power)
                
                # Use specified disband orders if available
                power_disband_orders = self.disband_orders.get(power.value, [])
                
                units_to_disband = []
                # First, disband units specified in orders
                for unit_id in power_disband_orders:
                    unit = new_state.units.get(unit_id)
                    if unit and len(units_to_disband) < disbands_needed:
                        units_to_disband.append(unit)
                
                # If not enough disband orders, arbitrarily select remaining units
                if len(units_to_disband) < disbands_needed:
                    for unit in power_units:
                        if unit not in units_to_disband and len(units_to_disband) < disbands_needed:
                            units_to_disband.append(unit)
                
                # Disband the selected units
                for unit in units_to_disband:
                    new_state.remove_unit(unit.get_id())
        
        return new_state


def resolve_movement_phase(game_state: GameState, orders: Dict[str, Order]) -> ResolutionResult:
    """Convenience function to resolve a movement phase."""
    resolver = MovementResolver(game_state, orders)
    return resolver.resolve()


def resolve_retreat_phase(game_state: GameState, retreat_orders: Dict[str, Order]) -> GameState:
    """Convenience function to resolve a retreat phase."""
    resolver = RetreatResolver(game_state, retreat_orders)
    return resolver.resolve()


def resolve_winter_phase(game_state: GameState, build_orders: Dict[str, List[BuildOrder]], 
                        disband_orders: Optional[Dict[str, List[str]]] = None) -> GameState:
    """Convenience function to resolve a winter phase."""
    resolver = WinterResolver(game_state, build_orders, disband_orders)
    return resolver.resolve()
