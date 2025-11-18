"""
Utility for writing orders to YAML format compatible with the game engine.
"""

import yaml
from typing import List
from diplomacy_game_engine.core.orders import (
    Order, MoveOrder, HoldOrder, SupportOrder, ConvoyOrder,
    RetreatOrder, DisbandOrder, BuildOrder
)
from diplomacy_game_engine.core.game_state import GameState
import logging

logger = logging.getLogger(__name__)


class OrderWriter:
    """Converts Order objects to YAML format for the game engine."""
    
    @staticmethod
    def orders_to_yaml_dict(orders: List[Order], state: GameState, game_id: str) -> dict:
        """
        Convert a list of Order objects to a YAML-compatible dictionary.
        
        Args:
            orders: List of Order objects
            state: Current game state
            game_id: Game identifier
            
        Returns:
            Dictionary in YAML order file format
        """
        # Determine phase name
        if state.season.value == 'Retreat' and state.previous_season:
            # Include which season the retreat is after
            phase_name = f"Retreat after {state.previous_season.value} {state.year}"
        else:
            phase_name = f"{state.season.value} {state.year}"
        
        # Build order list
        order_dicts = []
        for order in orders:
            order_dict = OrderWriter._order_to_dict(order)
            if order_dict:
                order_dicts.append(order_dict)
        
        # Build complete YAML structure
        yaml_dict = {
            'phase': phase_name,
            'game_id': game_id,
            'orders': order_dicts
        }
        
        return yaml_dict
    
    @staticmethod
    def _order_to_dict(order: Order) -> dict:
        """Convert a single Order object to dictionary format."""
        
        # Handle BuildOrder separately (no unit attribute)
        if isinstance(order, BuildOrder):
            unit_type = order.unit_type.value[0]  # 'A' or 'F'
            unit_str = f"{unit_type} {order.location}"
            return {
                'unit': unit_str,
                'action': 'build'
            }
        
        # Handle DisbandOrder separately
        if isinstance(order, DisbandOrder):
            unit_type = order.unit.unit_type.value[0]  # 'A' or 'F'
            location = order.unit.location
            if order.unit.coast:
                location = f"{location}/{order.unit.coast.value}"
            unit_str = f"{unit_type} {location}"
            return {
                'unit': unit_str,
                'action': 'disband'
            }
        
        # Build unit string for other order types
        unit_type = order.unit.unit_type.value[0]  # 'A' or 'F'
        location = order.unit.location
        if order.unit.coast:
            location = f"{location}/{order.unit.coast.value}"
        unit_str = f"{unit_type} {location}"
        
        if isinstance(order, MoveOrder):
            order_dict = {
                'unit': unit_str,
                'action': 'move',
                'destination': order.destination
            }
            if order.via_convoy:
                order_dict['via_convoy'] = True
            return order_dict
        
        elif isinstance(order, HoldOrder):
            return {
                'unit': unit_str,
                'action': 'hold'
            }
        
        elif isinstance(order, SupportOrder):
            # SupportOrder has: supported_unit_location, supported_unit_coast, destination, dest_coast
            supported_unit = f"A {order.supported_unit_location}"  # Assume army, will be corrected by engine
            
            order_dict = {
                'unit': unit_str,
                'action': 'support',
                'supporting': supported_unit
            }
            
            # If destination is provided, it's a support move
            if order.destination:
                order_dict['destination'] = order.destination
            
            return order_dict
        
        elif isinstance(order, ConvoyOrder):
            return {
                'unit': unit_str,
                'action': 'convoy',
                'convoying': f"A {order.convoyed_army_location}",
                'destination': order.destination
            }
        
        elif isinstance(order, RetreatOrder):
            return {
                'unit': unit_str,
                'action': 'retreat',
                'destination': order.destination
            }
        
        else:
            logger.warning(f"Unknown order type: {type(order)}")
            return None
    
    @staticmethod
    def save_orders_to_yaml(
        orders: List[Order],
        state: GameState,
        game_id: str,
        filepath: str
    ) -> None:
        """
        Save orders to a YAML file.
        
        Args:
            orders: List of Order objects
            state: Current game state
            game_id: Game identifier
            filepath: Path to save YAML file
        """
        yaml_dict = OrderWriter.orders_to_yaml_dict(orders, state, game_id)
        
        with open(filepath, 'w') as f:
            yaml.dump(yaml_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved {len(orders)} orders to {filepath}")
    
    @staticmethod
    def get_phase_filename(state: GameState) -> str:
        """
        Generate standard filename for a phase's orders.
        
        Args:
            state: Current game state
            
        Returns:
            Filename string (e.g., "1901_01_spring.yaml")
        """
        # Map season to number
        season_map = {
            'Spring': '01',
            'Fall': '02',
            'Winter': '03'
        }
        
        # Handle retreat phase specially - check which season it came from
        if state.season.value == 'Retreat':
            if state.previous_season:
                # Use previous season to determine number
                if state.previous_season.value == 'Spring':
                    season_num = '01'
                    season_name = 'retreat_spring'
                else:  # Fall
                    season_num = '02'
                    season_name = 'retreat_fall'
            else:
                # Fallback if previous_season not set
                season_num = '02'
                season_name = 'retreat'
        else:
            season_num = season_map.get(state.season.value, '01')
            season_name = state.season.value.lower()
        
        return f"{state.year}_{season_num}_{season_name}.yaml"
