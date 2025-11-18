"""
LLM player that uses AWS Bedrock to play Diplomacy.
"""

from typing import List, Dict, Optional
from diplomacy_game_engine.core.map import Power
from diplomacy_game_engine.core.game_state import GameState
from diplomacy_game_engine.core.orders import Order
from diplomacy_game_engine.llm.bedrock_client import BedrockClient
from diplomacy_game_engine.llm.order_parser import OrderParser
from diplomacy_game_engine.llm.prompts import PromptBuilder
from diplomacy_game_engine.gamemaster.press_system import PressSystem
import logging

logger = logging.getLogger(__name__)


class LLMPlayer:
    """Represents an LLM-powered player in a Diplomacy game."""
    
    def __init__(
        self,
        power: Power,
        model_id: str,
        bedrock_client: BedrockClient,
        press_system: PressSystem,
        gunboat_mode: bool = False,
        token_tracker=None
    ):
        """
        Initialize LLM player.
        
        Args:
            power: The power this player controls
            model_id: AWS Bedrock model identifier
            bedrock_client: Bedrock client for API calls
            press_system: Press system for diplomatic messages
            gunboat_mode: Whether to disable press context in prompts
            token_tracker: Optional TokenTracker for logging token usage
        """
        self.power = power
        self.model_id = model_id
        self.bedrock_client = bedrock_client
        self.press_system = press_system
        self.gunboat_mode = gunboat_mode
        self.token_tracker = token_tracker
        
        logger.info(f"LLM Player initialized: {power.value} using {model_id}")
    
    def send_press_messages(
        self,
        state: GameState,
        game_map,
        round_number: int
    ) -> Dict[str, str]:
        """
        Generate and send press messages for this round.
        
        Args:
            state: Current game state
            game_map: Game map
            round_number: Press round number (1, 2, or 3)
            
        Returns:
            Dictionary of messages sent (recipient -> message)
        """
        try:
            # Get press history
            press_threads = self.press_system.get_all_threads_for_power(self.power)
            
            # Build prompt
            prompt = PromptBuilder.build_press_round_prompt(
                state=state,
                power=self.power,
                game_map=game_map,
                press_threads=press_threads,
                round_number=round_number
            )
            
            # Get LLM response
            logger.info(f"{self.power.value}: Generating press messages (round {round_number})")
            response, token_usage = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                prompt=prompt,
                max_tokens=1024,
                temperature=0.8
            )
            
            # Log token usage
            if self.token_tracker:
                phase_str = f"{state.season.value} {state.year}"
                self.token_tracker.log_usage(
                    phase=phase_str,
                    call_type=f"press_round_{round_number}",
                    power=self.power.value,
                    model_id=self.model_id,
                    token_usage=token_usage
                )
            
            # Parse messages
            messages = OrderParser.parse_press_messages(response, self.power)
            
            # Send messages through press system
            phase_str = f"{state.season.value} {state.year}"
            self.press_system.send_messages(
                from_power=self.power,
                messages=messages,
                phase=phase_str,
                round_number=round_number
            )
            
            logger.info(f"{self.power.value}: Sent {len(messages)} press messages")
            return messages
            
        except Exception as e:
            logger.error(f"{self.power.value}: Error generating press messages: {e}")
            return {}
    
    def get_movement_orders(
        self,
        state: GameState,
        game_map
    ) -> List[Order]:
        """
        Generate movement orders for this turn.
        
        Args:
            state: Current game state
            game_map: Game map
            
        Returns:
            List of Order objects
        """
        try:
            # Get press history (skip if gunboat mode)
            press_threads = {} if self.gunboat_mode else self.press_system.get_all_threads_for_power(self.power)
            
            # Build prompt
            prompt = PromptBuilder.build_movement_orders_prompt(
                state=state,
                power=self.power,
                game_map=game_map,
                press_threads=press_threads
            )
            
            # Get LLM response
            logger.info(f"{self.power.value}: Generating movement orders")
            response, token_usage = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                prompt=prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            # Log token usage
            if self.token_tracker:
                phase_str = f"{state.season.value} {state.year}"
                self.token_tracker.log_usage(
                    phase=phase_str,
                    call_type="movement_orders",
                    power=self.power.value,
                    model_id=self.model_id,
                    token_usage=token_usage
                )
            
            # Parse orders
            orders = OrderParser.parse_orders(response, self.power)
            
            # Auto-hold for units without orders
            your_units = state.get_units_by_power(self.power)
            units_with_orders = {order.unit.location for order in orders}
            
            for unit in your_units:
                if unit.location not in units_with_orders:
                    from diplomacy_game_engine.core.orders import HoldOrder
                    hold_order = HoldOrder(unit)
                    orders.append(hold_order)
                    logger.warning(f"{self.power.value}: Auto-hold for {unit}")
            
            logger.info(f"{self.power.value}: Generated {len(orders)} orders")
            return orders
            
        except Exception as e:
            logger.error(f"{self.power.value}: Error generating orders: {e}")
            # Return hold orders for all units as fallback
            from diplomacy_game_engine.core.orders import HoldOrder
            return [
                HoldOrder(unit)
                for unit in state.get_units_by_power(self.power)
            ]
    
    def get_retreat_orders(
        self,
        state: GameState,
        game_map,
        dislodged_units: List
    ) -> List[Order]:
        """
        Generate retreat orders for dislodged units.
        
        Args:
            state: Current game state
            game_map: Game map
            dislodged_units: List of DislodgedUnit objects for this power
            
        Returns:
            List of RetreatOrder objects
        """
        if not dislodged_units:
            return []
        
        try:
            # Build prompt
            prompt = PromptBuilder.build_retreat_orders_prompt(
                state=state,
                power=self.power,
                game_map=game_map,
                dislodged_units=dislodged_units
            )
            
            # Get LLM response
            logger.info(f"{self.power.value}: Generating retreat orders for {len(dislodged_units)} units")
            response, token_usage = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                prompt=prompt,
                max_tokens=1024,
                temperature=0.7
            )
            
            # Log token usage
            if self.token_tracker:
                phase_str = f"{state.season.value} {state.year}"
                self.token_tracker.log_usage(
                    phase=phase_str,
                    call_type="retreat_orders",
                    power=self.power.value,
                    model_id=self.model_id,
                    token_usage=token_usage
                )
            
            # Parse retreat orders
            orders = OrderParser.parse_retreat_orders(response, self.power)
            
            logger.info(f"{self.power.value}: Generated {len(orders)} retreat orders")
            return orders
            
        except Exception as e:
            logger.error(f"{self.power.value}: Error generating retreat orders: {e}")
            return []  # Units will be disbanded
    
    def get_build_disband_orders(
        self,
        state: GameState,
        game_map,
        adjustment: int
    ) -> List[Order]:
        """
        Generate build or disband orders for winter adjustments.
        
        Args:
            state: Current game state
            game_map: Game map
            adjustment: Number of builds (positive) or disbands (negative) needed
            
        Returns:
            List of BuildOrder or DisbandOrder objects
        """
        if adjustment == 0:
            return []
        
        try:
            # Build prompt
            prompt = PromptBuilder.build_build_disband_prompt(
                state=state,
                power=self.power,
                game_map=game_map,
                adjustment=adjustment
            )
            
            # Get LLM response
            logger.info(f"{self.power.value}: Generating adjustment orders (adjustment: {adjustment:+d})")
            response, token_usage = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                prompt=prompt,
                max_tokens=1024,
                temperature=0.7
            )
            
            # Log token usage
            if self.token_tracker:
                phase_str = f"{state.season.value} {state.year}"
                self.token_tracker.log_usage(
                    phase=phase_str,
                    call_type="build_disband_orders",
                    power=self.power.value,
                    model_id=self.model_id,
                    token_usage=token_usage
                )
            
            # Parse orders
            orders = OrderParser.parse_build_disband_orders(response, self.power)
            
            logger.info(f"{self.power.value}: Generated {len(orders)} adjustment orders")
            return orders
            
        except Exception as e:
            logger.error(f"{self.power.value}: Error generating adjustment orders: {e}")
            return []
