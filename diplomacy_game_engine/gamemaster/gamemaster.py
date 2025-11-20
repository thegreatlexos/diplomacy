"""
Main Gamemaster orchestrator for running LLM-powered Diplomacy games.
"""

import os
import logging
from typing import Dict, Optional
from diplomacy_game_engine.core.game_state import GameState, Season, create_starting_state
from diplomacy_game_engine.core.map import Power, create_standard_map
from diplomacy_game_engine.core.resolver import MovementResolver, RetreatResolver, WinterResolver
from diplomacy_game_engine.core.orders import BuildOrder, DisbandOrder
from diplomacy_game_engine.llm.bedrock_client import BedrockClient
from diplomacy_game_engine.gamemaster.llm_player import LLMPlayer
from diplomacy_game_engine.gamemaster.press_system import PressSystem
from diplomacy_game_engine.gamemaster.phase_manager import PhaseManager
from diplomacy_game_engine.gamemaster.order_writer import OrderWriter
from diplomacy_game_engine.visualization.visualizer import MapVisualizer, visualize_game
from diplomacy_game_engine.gamemaster.summarizer import SeasonSummarizer
from diplomacy_game_engine.gamemaster.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class Gamemaster:
    """Orchestrates a complete Diplomacy game with LLM players."""
    
    def __init__(
        self,
        game_id: str,
        game_folder: str,
        player_models: Dict[Power, str],
        model_platform: str = "bedrock",
        aws_region: str = "eu-west-1",
        aws_profile: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        max_years: int = 20,
        enable_visualization: bool = False,
        gunboat_mode: bool = False,
        summarizer_model: Optional[str] = None,
        press_rounds_spring_1901: int = 3,
        press_rounds_default: int = 2
    ):
        """
        Initialize Gamemaster.
        
        Args:
            game_id: Unique identifier for this game
            game_folder: Root folder for game files
            player_models: Dictionary mapping Power to model ID
            model_platform: Platform to use ("bedrock" or "openrouter")
            aws_region: AWS region for Bedrock
            aws_profile: AWS profile name (optional)
            openrouter_api_key: OpenRouter API key (required if platform is "openrouter")
            max_years: Maximum years before auto-draw
            enable_visualization: Whether to generate visualizations
            gunboat_mode: Whether to disable press/communication (gunboat Diplomacy)
            summarizer_model: Model ID for season summaries (optional)
            press_rounds_spring_1901: Number of press rounds for Spring 1901
            press_rounds_default: Number of press rounds for other seasons
        """
        self.game_id = game_id
        self.game_folder = game_folder
        self.max_years = max_years
        self.enable_visualization = enable_visualization
        self.gunboat_mode = gunboat_mode
        self.press_rounds_spring_1901 = press_rounds_spring_1901
        self.press_rounds_default = press_rounds_default
        
        # Create folder structure
        self.orders_folder = os.path.join(game_folder, "orders")
        self.states_folder = os.path.join(game_folder, "states")
        self.viz_folder = os.path.join(game_folder, "visualizations")
        self.summaries_folder = os.path.join(game_folder, "summaries")
        os.makedirs(self.orders_folder, exist_ok=True)
        os.makedirs(self.states_folder, exist_ok=True)
        if enable_visualization:
            os.makedirs(self.viz_folder, exist_ok=True)
        if summarizer_model:
            os.makedirs(self.summaries_folder, exist_ok=True)
        
        # Initialize components
        self.game_map = create_standard_map()
        self.state = create_starting_state()
        self.press_system = PressSystem(game_folder)
        self.phase_manager = PhaseManager()
        self.token_tracker = TokenTracker(game_folder)
        self.viz_counter = 0  # Global counter for visualization filenames
        
        # Create LLM client based on platform
        if model_platform.lower() == "openrouter":
            # Use OpenRouter
            if not openrouter_api_key:
                raise ValueError("OpenRouter API key required when model_platform is 'openrouter'")
            
            from diplomacy_game_engine.llm_routing import LLMClientFactory
            from diplomacy_game_engine.llm_routing.unified_client import UnifiedLLMClient
            
            # For OpenRouter, we need to create a client per model
            # For now, use the first model as default (we'll create per-player clients in LLMPlayer)
            first_model = list(player_models.values())[0]
            routing_client = LLMClientFactory.create_client(
                model_id=first_model,
                openrouter_api_key=openrouter_api_key
            )
            self.bedrock_client = UnifiedLLMClient(routing_client)
            logger.info(f"Using OpenRouter platform with model: {first_model}")
        else:
            # Use Bedrock (default, backward compatible)
            self.bedrock_client = BedrockClient(region=aws_region, profile_name=aws_profile)
            logger.info(f"Using Bedrock platform in region: {aws_region}")
        
        # Initialize summarizer
        self.summarizer = SeasonSummarizer(self.bedrock_client, summarizer_model, self.token_tracker) if summarizer_model else None
        
        # Initialize players
        self.players: Dict[Power, LLMPlayer] = {}
        for power, model_id in player_models.items():
            # For OpenRouter, create a dedicated client for each player's model
            if model_platform.lower() == "openrouter":
                from diplomacy_game_engine.llm_routing import LLMClientFactory
                from diplomacy_game_engine.llm_routing.unified_client import UnifiedLLMClient
                
                routing_client = LLMClientFactory.create_client(
                    model_id=model_id,
                    openrouter_api_key=openrouter_api_key
                )
                player_client = UnifiedLLMClient(routing_client)
            else:
                # For Bedrock, all players share the same client
                player_client = self.bedrock_client
            
            self.players[power] = LLMPlayer(
                power=power,
                model_id=model_id,
                bedrock_client=player_client,
                press_system=self.press_system,
                gunboat_mode=gunboat_mode,
                token_tracker=self.token_tracker
            )
        
        logger.info(f"Gamemaster initialized for game '{game_id}'")
        logger.info(f"Game folder: {game_folder}")
        logger.info(f"Players: {len(self.players)}")
        if gunboat_mode:
            logger.info("GUNBOAT MODE ENABLED - No press/communication allowed")
    
    def _get_viz_filename(self, step: str) -> str:
        """
        Generate visualization filename with ascending counter.
        Format: {counter:03d}_{year}_{season}_{step}.png
        Example: 001_1901_spring_01_before.png
        """
        self.viz_counter += 1
        season = self.state.season.value.lower()
        return f"{self.viz_counter:03d}_{self.state.year}_{season}_{step}.png"
    
    def run_game(self) -> Optional[Power]:
        """
        Run the complete game until victory or max years.
        
        Returns:
            The winning power, or None if game ends in draw
        """
        logger.info("="*80)
        logger.info(f"STARTING GAME: {self.game_id}")
        logger.info("="*80)
        
        # Save initial state
        initial_state_path = os.path.join(self.states_folder, "1901_00_initial.json")
        self.state.to_json(initial_state_path)
        
        # Visualize initial state (Spring 1901 only)
        if self.enable_visualization:
            base_image = os.path.join(
                os.path.dirname(__file__), "..", "assets", "europemapbw.png"
            )
            initial_viz_path = os.path.join(self.viz_folder, self._get_viz_filename("00_initial"))
            visualize_game(self.state, filename=initial_viz_path, base_image_path=base_image)
            logger.info(f"Initial state visualization saved")
        
        winner = None
        end_year = 1901 + self.max_years  # Calculate end year from start year
        
        while self.state.year < end_year and winner is None:
            logger.info(f"\n{'='*80}")
            logger.info(f"YEAR {self.state.year} - {self.state.season.value}")
            logger.info(f"{'='*80}")
            
            if self.state.season == Season.SPRING:
                winner = self.run_spring_phase()
            elif self.state.season == Season.FALL:
                winner = self.run_fall_phase()
            elif self.state.season == Season.RETREAT:
                self.run_retreat_phase()
            elif self.state.season == Season.WINTER:
                winner = self.run_winter_phase()
            
            if winner:
                logger.info(f"\n{'='*80}")
                logger.info(f"GAME OVER - {winner.value} WINS!")
                logger.info(f"{'='*80}")
                break
        
        if not winner and self.state.year >= end_year:
            logger.info(f"\n{'='*80}")
            logger.info(f"GAME ENDS IN DRAW (reached year {end_year})")
            logger.info(f"{'='*80}")
        
        # Generate token usage report
        logger.info(f"\n{'='*80}")
        logger.info("GENERATING TOKEN USAGE REPORT")
        logger.info(f"{'='*80}")
        report_path = self.token_tracker.save_report()
        logger.info(f"Token usage report saved: {report_path}")
        
        # Log summary to console
        report = self.token_tracker.generate_report()
        for line in report.split('\n')[:10]:  # Print first 10 lines
            logger.info(line)
        
        return winner
    
    def run_spring_phase(self) -> Optional[Power]:
        """Run Spring movement phase with press rounds."""
        return self._run_movement_phase()
    
    def run_fall_phase(self) -> Optional[Power]:
        """Run Fall movement phase with press rounds and SC updates."""
        winner = self._run_movement_phase()
        
        # Update supply center ownership after Fall
        if self.state.season == Season.FALL:  # Still in Fall after movement
            self.phase_manager.update_sc_ownership(self.state)
        
        return winner
    
    def _run_movement_phase(self) -> Optional[Power]:
        """Run a movement phase (Spring or Fall) with press rounds."""
        phase_name = f"{self.state.season.value} {self.state.year}"
        
        # Get base image path
        base_image = os.path.join(
            os.path.dirname(__file__), "..", "assets", "europemapbw.png"
        )
        
        # Press rounds (skip if gunboat mode)
        if self.phase_manager.needs_press_phase(self.state.season) and not self.gunboat_mode:
            # Determine number of press rounds based on year and season
            if self.state.year == 1901 and self.state.season == Season.SPRING:
                press_rounds = self.press_rounds_spring_1901
            else:
                press_rounds = self.press_rounds_default
            
            for round_num in range(1, press_rounds + 1):
                logger.info(f"\n--- Press Round {round_num}/{press_rounds} ---")
                press_count = 0
                for power in Power:
                    messages = self.players[power].send_press_messages(
                        state=self.state,
                        game_map=self.game_map,
                        round_number=round_num
                    )
                    press_count += len(messages)
                logger.info(f"Total messages sent: {press_count}")
        elif self.gunboat_mode:
            logger.info("\n--- Gunboat Mode: Skipping Press Phase ---")
        
        # Collect orders from all players
        logger.info(f"\n--- Collecting Orders ---")
        all_orders = []
        order_summary = {}
        for power in Power:
            orders = self.players[power].get_movement_orders(
                state=self.state,
                game_map=self.game_map
            )
            all_orders.extend(orders)
            order_summary[power] = len(orders)
        
        logger.info(f"Collected {len(all_orders)} total orders from {len(order_summary)} powers")
        
        # Save orders to YAML
        order_filename = OrderWriter.get_phase_filename(self.state)
        order_path = os.path.join(self.orders_folder, order_filename)
        OrderWriter.save_orders_to_yaml(all_orders, self.state, self.game_id, order_path)
        logger.info(f"Orders saved: {order_filename}")
        
        # Save original state for visualization
        original_state = self.state.clone()
        
        # Resolve orders
        logger.info(f"\n--- Resolving Orders ---")
        # Match orders to actual game state units by location
        order_dict = {}
        for order in all_orders:
            # Find the actual unit in game state that matches this order's location
            actual_unit = original_state.get_unit_at(order.unit.location, order.unit.coast)
            if actual_unit:
                # Replace the order's unit with the actual game state unit
                order.unit = actual_unit
                order_dict[actual_unit.get_id()] = order
            else:
                logger.warning(f"Could not find unit for order: {order}")
        
        logger.info(f"Matched {len(order_dict)} orders to game state units")
        resolver = MovementResolver(original_state, order_dict)
        result = resolver.resolve()
        
        # Log resolution results
        successful = sum(1 for r in result.move_results.values() if 'Successfully' in r)
        bounced = sum(1 for r in result.move_results.values() if 'Bounced' in r)
        logger.info(f"Resolution complete: {successful} successful, {bounced} bounced")
        if result.dislodged_units:
            logger.info(f"Dislodgements: {len(result.dislodged_units)}")
        
        # If there are dislodged units, collect retreat orders for visualization
        retreat_orders_for_viz = []
        if result.dislodged_units:
            # Group dislodged units by power
            dislodged_by_power = {}
            for du in result.dislodged_units:
                power = du.unit.power
                if power not in dislodged_by_power:
                    dislodged_by_power[power] = []
                dislodged_by_power[power].append(du)
            
            # Collect retreat orders from players
            for power, dislodged_units in dislodged_by_power.items():
                orders = self.players[power].get_retreat_orders(
                    state=result.new_state,
                    game_map=self.game_map,
                    dislodged_units=dislodged_units
                )
                retreat_orders_for_viz.extend(orders)
        
        # Visualize with orders and results (including retreat arrows if any)
        if self.enable_visualization:
            orders_path = os.path.join(self.viz_folder, self._get_viz_filename("02_orders"))
            visualizer = MapVisualizer(original_state, base_image_path=base_image)
            visualizer.draw_map_with_results(
                orders=all_orders,
                move_results=result.move_results,
                dislodged_units=result.dislodged_units,
                original_state=original_state,
                invalid_supports=result.invalid_supports,
                cut_supports=result.cut_supports,
                retreat_orders=retreat_orders_for_viz if retreat_orders_for_viz else None
            )
            visualizer.save(orders_path)
        
        # Apply resolution result
        self.state = result.new_state
        
        # Save state after resolution (before setting previous_season)
        state_filename = f"{self.state.year}_{self.state.season.value.lower()}_after.json"
        state_path = os.path.join(self.states_folder, state_filename)
        self.state.to_json(state_path)
        
        # Note: "after" visualization will be generated after retreat phase if there are dislodgements
        # Otherwise generate it now
        if not result.dislodged_units and self.enable_visualization:
            after_path = os.path.join(self.viz_folder, self._get_viz_filename("03_after"))
            visualize_game(self.state, filename=after_path, base_image_path=base_image)
        
        # Generate season summary
        if self.summarizer:
            logger.info(f"\n--- Generating Season Summary ---")
            # Get all press threads
            all_press = {}
            for p1 in Power:
                for p2 in Power:
                    if p1 != p2:
                        thread_key = f"{p1.value.lower()}_{p2.value.lower()}"
                        content = self.press_system.get_thread_content(p1, p2)
                        if content:
                            all_press[thread_key] = content
            
            summary = self.summarizer.generate_summary(
                phase_name=phase_name,
                press_threads=all_press,
                orders=all_orders,
                resolution_result=result,
                state_before=original_state,
                state_after=self.state
            )
            
            # Save summary
            summary_filename = f"{self.state.year}_{self.state.season.value.lower()}_summary.md"
            summary_path = os.path.join(self.summaries_folder, summary_filename)
            with open(summary_path, 'w') as f:
                f.write(summary)
            logger.info(f"Summary saved: {summary_filename}")
        
        # Check for dislodged units
        has_dislodged = len(self.state.dislodged_units) > 0
        if has_dislodged:
            logger.info(f"⚠ {len(self.state.dislodged_units)} units dislodged - retreat phase needed")
        
        logger.info(f"DEBUG: Before advance_phase - Season: {self.state.season.value}, previous_season: {self.state.previous_season}")
        
        # Advance phase (this changes season to RETREAT if needed)
        self.phase_manager.advance_phase(self.state, has_dislodged)
        
        logger.info(f"DEBUG: After advance_phase - Season: {self.state.season.value}, previous_season: {self.state.previous_season}")
        
        # NOW set previous_season AFTER advance_phase if we entered retreat
        if self.state.season == Season.RETREAT and has_dislodged:
            logger.info(f"DEBUG: Setting previous_season to {original_state.season.value}")
            self.state.previous_season = original_state.season
            logger.info(f"DEBUG: previous_season is now: {self.state.previous_season.value}")
            
            # SAVE STATE AGAIN with correct previous_season
            state_filename = f"{self.state.year}_retreat_after.json"
            state_path = os.path.join(self.states_folder, state_filename)
            self.state.to_json(state_path)
            logger.info(f"DEBUG: Saved retreat state to {state_filename} with previous_season = {self.state.previous_season.value}")
        
        # Check victory
        return self.phase_manager.check_victory(self.state)
    
    def run_retreat_phase(self) -> None:
        """Run retreat phase for dislodged units."""
        logger.info(f"\n--- Retreat Phase ---")
        logger.info(f"DEBUG: Retreat phase starting - Season: {self.state.season.value}, previous_season: {self.state.previous_season.value if self.state.previous_season else 'None'}")
        
        # Group dislodged units by power
        dislodged_by_power = {}
        for du in self.state.dislodged_units:
            power = du.unit.power
            if power not in dislodged_by_power:
                dislodged_by_power[power] = []
            dislodged_by_power[power].append(du)
        
        # Collect retreat orders
        all_orders = []
        for power, dislodged_units in dislodged_by_power.items():
            orders = self.players[power].get_retreat_orders(
                state=self.state,
                game_map=self.game_map,
                dislodged_units=dislodged_units
            )
            all_orders.extend(orders)
        
        # Save retreat orders
        if all_orders:
            order_filename = OrderWriter.get_phase_filename(self.state)
            order_path = os.path.join(self.orders_folder, order_filename)
            OrderWriter.save_orders_to_yaml(all_orders, self.state, self.game_id, order_path)
        
        # Resolve retreats
        # Match retreat orders to actual dislodged units by location
        order_dict = {}
        for order in all_orders:
            # Find the dislodged unit at this location
            for dislodged in self.state.dislodged_units:
                if dislodged.unit.location == order.unit.location and dislodged.unit.power == order.unit.power:
                    # Use the actual dislodged unit's ID
                    order.unit = dislodged.unit
                    order_dict[dislodged.unit.get_id()] = order
                    break
        
        logger.info(f"Matched {len(order_dict)} retreat orders to dislodged units")
        
        # CRITICAL: Save previous_season before resolve() overwrites it
        old_previous_season = self.state.previous_season
        logger.info(f"DEBUG: Saving previous_season before resolve: {old_previous_season.value if old_previous_season else 'None'}")
        
        resolver = RetreatResolver(self.state, order_dict)
        self.state = resolver.resolve()
        
        # CRITICAL: Restore previous_season after resolve()
        self.state.previous_season = old_previous_season
        logger.info(f"DEBUG: Restored previous_season after resolve: {self.state.previous_season.value if self.state.previous_season else 'None'}")
        
        # Save state
        state_filename = f"{self.state.year}_retreat_after.json"
        state_path = os.path.join(self.states_folder, state_filename)
        self.state.to_json(state_path)
        logger.info(f"DEBUG: Saved retreat state with previous_season = {self.state.previous_season.value if self.state.previous_season else 'None'}")
        
        # Visualize after retreats (this is the "after" image for the movement phase)
        if self.enable_visualization:
            base_image = os.path.join(
                os.path.dirname(__file__), "..", "assets", "europemapbw.png"
            )
            # Use the previous season name for the filename since this completes that phase
            prev_season = self.state.previous_season.value.lower() if self.state.previous_season else "retreat"
            # Properly increment counter before using it
            self.viz_counter += 1
            after_path = os.path.join(self.viz_folder, f"{self.viz_counter:03d}_{self.state.year}_{prev_season}_03_after.png")
            visualize_game(self.state, filename=after_path, base_image_path=base_image)
            logger.info(f"After-retreat visualization saved")
        
        # Advance phase
        self.phase_manager.advance_phase(self.state, False)
    
    def run_winter_phase(self) -> Optional[Power]:
        """Run winter adjustment phase."""
        logger.info(f"\n--- Winter Adjustments ---")
        
        # Get base image path
        base_image = os.path.join(
            os.path.dirname(__file__), "..", "assets", "europemapbw.png"
        )
        
        # Calculate adjustments
        adjustments = self.phase_manager.calculate_adjustments(self.state)
        
        if not adjustments:
            logger.info("No adjustments needed")
        else:
            # Collect build/disband orders
            all_orders = []
            for power, adjustment in adjustments.items():
                orders = self.players[power].get_build_disband_orders(
                    state=self.state,
                    game_map=self.game_map,
                    adjustment=adjustment
                )
                all_orders.extend(orders)
            
            # Save orders
            if all_orders:
                order_filename = OrderWriter.get_phase_filename(self.state)
                order_path = os.path.join(self.orders_folder, order_filename)
                OrderWriter.save_orders_to_yaml(all_orders, self.state, self.game_id, order_path)
            
            # Visualize orders (dotted circles for builds, red X for disbands)
            if self.enable_visualization and all_orders:
                orders_path = os.path.join(self.viz_folder, self._get_viz_filename("02_orders"))
                
                # Separate build orders and disband unit IDs
                build_orders_list = [order for order in all_orders if isinstance(order, BuildOrder)]
                disband_unit_ids = [order.unit.get_id() for order in all_orders if isinstance(order, DisbandOrder)]
                
                visualize_game(
                    self.state,
                    filename=orders_path,
                    base_image_path=base_image,
                    orders=build_orders_list,
                    disband_unit_ids=disband_unit_ids
                )
            
            # Resolve adjustments
            # Group build orders by power
            build_dict = {}
            disband_dict = {}
            for order in all_orders:
                if isinstance(order, BuildOrder):
                    power_name = order.power.value
                    if power_name not in build_dict:
                        build_dict[power_name] = []
                    build_dict[power_name].append(order)
                elif isinstance(order, DisbandOrder):
                    power_name = order.unit.power.value
                    if power_name not in disband_dict:
                        disband_dict[power_name] = []
                    disband_dict[power_name].append(order.unit.get_id())
            
            resolver = WinterResolver(self.state, build_dict, disband_dict)
            self.state = resolver.resolve()
        
        # Visualize after adjustments
        if self.enable_visualization:
            after_path = os.path.join(self.viz_folder, self._get_viz_filename("03_after"))
            visualize_game(self.state, filename=after_path, base_image_path=base_image)
        
        # Save state
        state_filename = f"{self.state.year}_winter_after.json"
        state_path = os.path.join(self.states_folder, state_filename)
        self.state.to_json(state_path)
        
        # Check victory before advancing
        winner = self.phase_manager.check_victory(self.state)
        
        # Advance to next year
        self.phase_manager.advance_phase(self.state, False)
        
        return winner
