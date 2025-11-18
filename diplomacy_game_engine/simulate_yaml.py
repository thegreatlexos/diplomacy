#!/usr/bin/env python3
"""
Simulate Diplomacy games from YAML order files.
Generates visualizations, saves states, and creates summary reports.
"""

import os
import sys

# Add parent directory to path so we can import diplomacy_game_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from datetime import datetime
from diplomacy_game_engine.core.game import Game
from diplomacy_game_engine.core.game_state import GameState, Season
from diplomacy_game_engine.io.yaml_orders import YAMLOrderLoader
from diplomacy_game_engine.core.resolver import resolve_movement_phase, resolve_retreat_phase, resolve_winter_phase
from diplomacy_game_engine.visualization.visualizer import visualize_game, MapVisualizer
from diplomacy_game_engine.core.map import create_standard_map


class GameSimulator:
    """Simulates a game from YAML order files."""
    
    def __init__(self, game_folder: str):
        self.game_folder = game_folder
        self.game_info = None
        self.current_state = None
        self.phase_results = []
        self.winner = None
    
    def load_game_info(self):
        """Load game_info.yaml from game folder."""
        info_path = os.path.join(self.game_folder, 'game_info.yaml')
        
        if not os.path.exists(info_path):
            raise FileNotFoundError(f"game_info.yaml not found in {self.game_folder}")
        
        with open(info_path, 'r') as f:
            self.game_info = yaml.safe_load(f)
        
        print(f"📋 Loaded game: {self.game_info.get('name', 'Unnamed Game')}")
        print(f"   Description: {self.game_info.get('description', 'No description')}")
    
    def _update_phase_from_name(self, phase_name: str):
        """Parse phase name and update game state year and season."""
        import re
        
        # Parse phase name like "Spring 1903" or "Fall 1902" or "Winter 1901"
        match = re.match(r'(Spring|Fall|Winter)\s+(\d{4})', phase_name, re.IGNORECASE)
        if match:
            season_str = match.group(1).capitalize()
            year = int(match.group(2))
            
            # Update game state
            self.current_state.year = year
            if season_str == 'Spring':
                self.current_state.season = Season.SPRING
            elif season_str == 'Fall':
                self.current_state.season = Season.FALL
            elif season_str == 'Winter':
                self.current_state.season = Season.WINTER
    
    def initialize_game(self):
        """Initialize or load the starting game state."""
        initial_state_path = self.game_info.get('initial_state')
        
        if initial_state_path:
            # Load from file
            full_path = os.path.join(self.game_folder, initial_state_path)
            if os.path.exists(full_path):
                game_map = create_standard_map()
                self.current_state = GameState.from_json(full_path, game_map)
                print(f"✅ Loaded initial state from {initial_state_path}")
            else:
                print(f"⚠️  Initial state file not found, starting fresh game")
                game = Game()
                self.current_state = game.get_current_state()
        else:
            # Start fresh
            game = Game()
            self.current_state = game.get_current_state()
            print("✅ Started fresh game (1901 Spring)")
    
    def simulate_phase(self, order_file: str):
        """Simulate a single phase from YAML order file."""
        print(f"\n{'='*60}")
        print(f"📄 Processing: {order_file}")
        print(f"{'='*60}")
        
        # Load YAML file
        full_path = os.path.join(self.game_folder, order_file)
        loader = YAMLOrderLoader(self.current_state)
        yaml_data = loader.load_from_file(full_path)
        
        phase_name = yaml_data.get('phase', 'Unknown Phase')
        print(f"Phase: {phase_name}")
        
        # Update game state year and season from phase name
        self._update_phase_from_name(phase_name)
        
        # Create output folder
        output_folder = yaml_data.get('output_folder', f"visualizations/{phase_name.replace(' ', '_').lower()}")
        full_output = os.path.join(self.game_folder, output_folder)
        os.makedirs(full_output, exist_ok=True)
        
        # Get base image path relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_image = os.path.join(script_dir, "assets", "europemapbw.png")
        if not os.path.exists(base_image):
            base_image = None
        
        # Step 1: Visualize before state
        print("  📸 Generating 'before' visualization...")
        visualize_game(
            self.current_state,
            filename=f"{full_output}/01_before.png",
            base_image_path=base_image
        )
        
        # Step 2: Parse orders
        print("  📝 Parsing orders...")
        orders = loader.parse_orders(yaml_data)
        
        # Show corrections and warnings
        if loader.get_corrections():
            print(f"  ✏️  Auto-corrections made: {len(loader.get_corrections())}")
            for correction in loader.get_corrections():
                print(f"     • {correction}")
        
        if loader.get_warnings():
            print(f"  ⚠️  Warnings: {len(loader.get_warnings())}")
            for warning in loader.get_warnings():
                print(f"     • {warning}")
        
        print(f"  ✅ Parsed {len(orders)} valid orders")
        
        # Step 3: Determine phase type first
        phase_lower = phase_name.lower()
        is_winter = 'winter' in phase_lower or self.current_state.season == Season.WINTER
        
        # Parse build orders if winter phase
        build_orders_list = []
        if is_winter:
            build_orders_dict = loader.parse_builds(yaml_data)
            # Flatten build orders dict to list for visualization
            for power_builds in build_orders_dict.values():
                build_orders_list.extend(power_builds)
        
        # Step 4: Resolve phase FIRST (before generating orders visualization)
        
        if is_winter:
            # Winter phase - parse orders first
            build_orders = loader.parse_builds(yaml_data)
            disband_orders = loader.parse_disbands(yaml_data)
            
            # Flatten disband orders to list of unit IDs
            disband_unit_ids = []
            if disband_orders:
                for power_disbands in disband_orders.values():
                    disband_unit_ids.extend(power_disbands)
            
            # Generate orders visualization BEFORE resolution (shows units being disbanded with red X)
            print("  📸 Generating 'orders' visualization...")
            visualize_game(
                self.current_state,
                filename=f"{full_output}/02_orders.png",
                base_image_path=base_image,
                orders=build_orders_list,
                disband_unit_ids=disband_unit_ids
            )
            
            # Now resolve winter phase
            print("  🏗️  Resolving winter phase (builds/disbands)...")
            if build_orders or disband_orders:
                self.current_state = resolve_winter_phase(self.current_state, build_orders, disband_orders)
                print(f"     • Processed builds for {len(build_orders)} powers")
                if disband_orders:
                    total_disbands = sum(len(units) for units in disband_orders.values())
                    print(f"     • Processed {total_disbands} disband orders")
            else:
                print("     • No build/disband orders specified")
            
            # Visualize after builds and disbands
            print("  📸 Generating 'after' visualization...")
            visualize_game(
                self.current_state,
                filename=f"{full_output}/03_after.png",
                base_image_path=base_image
            )
            
            # Store phase result
            self.phase_results.append({
                'phase': phase_name,
                'orders_count': len(build_orders) if build_orders else 0,
                'dislodgements': 0,
                'output_folder': output_folder
            })
        else:
            # Movement phase
            print("  ⚙️  Resolving movement phase...")
            result = resolve_movement_phase(self.current_state, orders)
            
            # Print results
            print(f"     • Successful moves: {sum(1 for r in result.move_results.values() if 'Successfully' in r)}")
            print(f"     • Bounces: {sum(1 for r in result.move_results.values() if 'Bounced' in r)}")
            print(f"     • Dislodgements: {len(result.dislodged_units)}")
            
            # Step 5: Generate orders visualization with results (red arrows for failed)
            print("  📸 Generating 'orders' visualization...")
            
            # Parse retreat orders if there are dislodged units
            retreat_orders = None
            if result.dislodged_units:
                retreat_orders = loader.parse_retreats(yaml_data)
            
            viz_orders = MapVisualizer(self.current_state, base_image_path=base_image)
            viz_orders.draw_map_with_results(
                orders=list(orders.values()),
                move_results=result.move_results,
                dislodged_units=result.dislodged_units,
                original_state=self.current_state,
                invalid_supports=result.invalid_supports,
                cut_supports=result.cut_supports,
                retreat_orders=retreat_orders
            )
            viz_orders.save(f"{full_output}/02_orders.png")
            
            # Step 6: Visualize after state (clean, no indicators)
            print("  📸 Generating 'after' visualization...")
            self.current_state = result.new_state
            visualize_game(
                self.current_state,
                filename=f"{full_output}/03_after.png",
                base_image_path=base_image
            )
            
            # Step 7: Handle retreats if needed
            if result.dislodged_units:
                print(f"  🔄 {len(result.dislodged_units)} unit(s) dislodged, processing retreats...")
                retreat_orders = loader.parse_retreats(yaml_data)
                
                if retreat_orders:
                    self.current_state = resolve_retreat_phase(self.current_state, retreat_orders)
                    print(f"     • Processed {len(retreat_orders)} retreat orders")
                    
                    # Visualize after retreats
                    visualize_game(
                        self.current_state,
                        filename=f"{full_output}/04_after_retreats.png",
                        base_image_path=base_image
                    )
            
            # Store phase result
            self.phase_results.append({
                'phase': phase_name,
                'orders_count': len(orders),
                'dislodgements': len(result.dislodged_units),
                'output_folder': output_folder
            })
        
        # Save state
        output_state = yaml_data.get('output_state')
        if output_state:
            state_path = os.path.join(self.game_folder, output_state)
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            self.current_state.to_json(state_path)
            print(f"  💾 Saved state to {output_state}")
        
        # Check for victory condition
        winner = self.current_state.check_victory()
        if winner:
            print(f"\n  🏆 VICTORY DETECTED! {winner.value} has won the game with {self.current_state.get_sc_count(winner)} supply centers!")
            self.winner = winner
        
        print(f"  ✅ Phase complete!")
    
    def generate_summary_report(self):
        """Generate a summary report for the entire game simulation."""
        report_path = os.path.join(self.game_folder, 'SIMULATION_REPORT.md')
        
        with open(report_path, 'w') as f:
            f.write(f"# Game Simulation Report\n\n")
            f.write(f"**Game:** {self.game_info.get('name', 'Unnamed')}\n")
            f.write(f"**Description:** {self.game_info.get('description', 'No description')}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"---\n\n")
            
            f.write(f"## Phases Simulated\n\n")
            for i, phase in enumerate(self.phase_results, 1):
                f.write(f"### {i}. {phase['phase']}\n\n")
                f.write(f"- Orders processed: {phase['orders_count']}\n")
                f.write(f"- Dislodgements: {phase['dislodgements']}\n")
                f.write(f"- Visualizations: `{phase['output_folder']}/`\n\n")
            
            f.write(f"---\n\n")
            f.write(f"## Final State\n\n")
            f.write(f"- Year: {self.current_state.year}\n")
            f.write(f"- Season: {self.current_state.season.value}\n")
            f.write(f"- Total units: {len(self.current_state.units)}\n\n")
            
            f.write(f"### Supply Center Count\n\n")
            from diplomacy_game_engine.core.map import Power
            for power in Power:
                sc_count = self.current_state.get_sc_count(power)
                unit_count = self.current_state.get_unit_count(power)
                f.write(f"- **{power.value}**: {sc_count} SCs, {unit_count} units\n")
            
            # Add victory information if game was won
            if self.winner:
                f.write(f"\n---\n\n")
                f.write(f"## 🏆 GAME RESULT\n\n")
                f.write(f"**WINNER: {self.winner.value}**\n\n")
                f.write(f"Victory achieved with {self.current_state.get_sc_count(self.winner)} supply centers (18+ required)\n")
        
        print(f"\n📊 Summary report saved to SIMULATION_REPORT.md")
    
    def run(self):
        """Run the complete game simulation."""
        print("\n" + "="*60)
        print("🎮 DIPLOMACY GAME SIMULATOR")
        print("="*60)
        
        # Load game info
        self.load_game_info()
        
        # Initialize game
        self.initialize_game()
        
        # Process each order file
        order_files = self.game_info.get('order_files', [])
        
        if not order_files:
            print("\n⚠️  No order files specified in game_info.yaml")
            return
        
        for order_file in order_files:
            self.simulate_phase(order_file)
        
        # Generate summary report
        self.generate_summary_report()
        
        print("\n" + "="*60)
        print("✅ SIMULATION COMPLETE!")
        print("="*60)
        print(f"\nResults saved in: {self.game_folder}/")
        print(f"  • Visualizations in visualizations/ subfolders")
        print(f"  • Game states in states/ folder")
        print(f"  • Summary report: SIMULATION_REPORT.md")
        print("="*60 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python simulate_yaml.py <game_folder>")
        print("\nExample: python simulate_yaml.py games/game_001_tutorial")
        sys.exit(1)
    
    game_folder = sys.argv[1]
    
    if not os.path.exists(game_folder):
        print(f"Error: Game folder not found: {game_folder}")
        sys.exit(1)
    
    simulator = GameSimulator(game_folder)
    simulator.run()


if __name__ == "__main__":
    main()
