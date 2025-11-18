"""
Diplomacy Game Engine
A complete engine for simulating Diplomacy board game from YAML order files.
"""

from diplomacy_game_engine.core.map import Power, Coast, create_standard_map
from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType, Season
from diplomacy_game_engine.core.game import Game
from diplomacy_game_engine.core.orders import (
    Order, HoldOrder, MoveOrder, SupportOrder, ConvoyOrder,
    RetreatOrder, DisbandOrder, BuildOrder
)
from diplomacy_game_engine.core.resolver import (
    resolve_movement_phase, resolve_retreat_phase, resolve_winter_phase
)
from diplomacy_game_engine.io.yaml_orders import YAMLOrderLoader
from diplomacy_game_engine.visualization.visualizer import visualize_game

__version__ = "1.0.0"
__all__ = [
    'Power', 'Coast', 'create_standard_map',
    'GameState', 'Unit', 'UnitType', 'Season',
    'Game',
    'Order', 'HoldOrder', 'MoveOrder', 'SupportOrder', 'ConvoyOrder',
    'RetreatOrder', 'DisbandOrder', 'BuildOrder',
    'resolve_movement_phase', 'resolve_retreat_phase', 'resolve_winter_phase',
    'YAMLOrderLoader',
    'visualize_game'
]
