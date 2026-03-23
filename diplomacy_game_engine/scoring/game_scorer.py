"""
Game scorer for evaluating LLM model performance.
"""

import json
import os
import re
from typing import Dict, List, Optional
from diplomacy_game_engine.core.map import Power
import logging

logger = logging.getLogger(__name__)


class GameScorer:
    """
    Comprehensive scoring system for LLM Diplomacy games.
    
    Tracks and scores:
    - Model performance (wins, SC count, growth)
    - LLM precision (invalid orders, complex orders)
    - Press evaluation (from LLM summaries)
    """
    
    # Scoring weights
    VICTORY_POINTS = 100
    SC_POINTS = 10
    SC_GROWTH_POINTS = 5
    SURVIVAL_POINTS = 20
    INVALID_ORDER_PENALTY = -10
    BOUNCED_MOVE_PENALTY = -2
    SUCCESSFUL_CONVOY_POINTS = 15
    SUCCESSFUL_SUPPORT_OWN_POINTS = 5
    SUCCESSFUL_SUPPORT_OTHER_POINTS = 10
    SUCCESSFUL_SUPPORT_HOLD_POINTS = 3
    SUCCESSFUL_SUPPORT_ATTACK_POINTS = 8
    # New penalty weights
    SELF_ATTACK_PENALTY = -8  # Attacking own units
    SELF_BLOCK_PENALTY = -5   # Multiple units to same destination
    
    def __init__(self, game_folder: str):
        """
        Initialize game scorer.
        
        Args:
            game_folder: Root folder containing game files
        """
        self.game_folder = game_folder
        self.states_folder = os.path.join(game_folder, "states")
        self.orders_folder = os.path.join(game_folder, "orders")
        self.summaries_folder = os.path.join(game_folder, "summaries")
        
        # Load model assignments
        self.model_assignments = self._load_model_assignments()
        
        # Initialize score tracking
        self.performance_scores = {power.value: 0 for power in Power}
        self.precision_scores = {power.value: 0 for power in Power}
        self.press_scores = {power.value: {} for power in Power}
        self.sc_details = {power.value: {} for power in Power}

        # Per-year tracking
        self.yearly_sc_counts = {}  # year -> power -> sc_count
        self.yearly_precision = {}  # year -> power -> metrics

        # New derived metrics
        self.strategic_metrics = {}  # power -> {peak_sc, survival_years, etc}
        self.complexity_scores = {}  # power -> complexity (0-1)
        self.error_rates = {}  # power -> error_rate (0-1)

        logger.info(f"GameScorer initialized for {game_folder}")
    
    def _load_model_assignments(self) -> Optional[Dict]:
        """Load model assignments from JSON file."""
        assignments_path = os.path.join(self.game_folder, "model_assignments.json")
        if os.path.exists(assignments_path):
            with open(assignments_path, 'r') as f:
                return json.load(f)
        return None
    
    def _load_game_states(self) -> List[Dict]:
        """Load all game states in chronological order."""
        states = []
        if not os.path.exists(self.states_folder):
            return states

        # Get all state files
        state_files = sorted([f for f in os.listdir(self.states_folder) if f.endswith('.json')])

        for filename in state_files:
            filepath = os.path.join(self.states_folder, filename)
            with open(filepath, 'r') as f:
                states.append(json.load(f))

        return states

    def _calculate_yearly_sc_counts(self, states: List[Dict]):
        """Extract per-year SC counts from game states."""
        for state in states:
            year = state.get('year', 0)
            season = state.get('season', '').lower()

            # Only use winter states for end-of-year SC counts (or fall if no winter)
            if season not in ['winter', 'fall']:
                continue

            # Skip if we already have winter for this year
            if year in self.yearly_sc_counts and season == 'fall':
                continue

            self.yearly_sc_counts[year] = {}
            for power in Power:
                sc_count = sum(
                    1 for sc_power in state['supply_centers'].values()
                    if sc_power == power.value
                )
                self.yearly_sc_counts[year][power.value] = sc_count
    
    def calculate_performance_scores(self) -> Dict[str, int]:
        """
        Calculate model performance scores based on game outcomes.

        Returns:
            Dict mapping power name to performance score
        """
        states = self._load_game_states()
        if not states:
            logger.warning("No game states found")
            return self.performance_scores

        # Calculate yearly SC counts for per-year tracking
        self._calculate_yearly_sc_counts(states)

        initial_state = states[0]
        final_state = states[-1]
        
        # Get initial SC counts
        initial_sc_counts = {}
        for power in Power:
            initial_sc_counts[power.value] = sum(
                1 for sc_power in initial_state['supply_centers'].values() 
                if sc_power == power.value
            )
        
        # Get final SC counts
        final_sc_counts = {}
        for power in Power:
            final_sc_counts[power.value] = sum(
                1 for sc_power in final_state['supply_centers'].values() 
                if sc_power == power.value
            )
        
        # Calculate scores for each power
        for power in Power:
            power_name = power.value
            score = 0
            
            initial_scs = initial_sc_counts[power_name]
            final_scs = final_sc_counts[power_name]
            sc_growth = final_scs - initial_scs
            
            # Store details for reporting
            self.sc_details[power_name] = {
                'initial': initial_scs,
                'final': final_scs,
                'growth': sc_growth,
                'sc_points': final_scs * self.SC_POINTS,
                'growth_points': sc_growth * self.SC_GROWTH_POINTS if sc_growth > 0 else 0,
                'survival_points': self.SURVIVAL_POINTS if final_scs > 0 else 0,
                'victory_points': self.VICTORY_POINTS if final_scs >= 18 else 0
            }
            
            # Final SC count (10 points per SC)
            score += final_scs * self.SC_POINTS
            
            # SC growth (5 points per SC gained)
            if sc_growth > 0:
                score += sc_growth * self.SC_GROWTH_POINTS
            
            # Survival bonus (20 points if not eliminated)
            if final_scs > 0:
                score += self.SURVIVAL_POINTS
            
            # Victory bonus (100 points)
            if final_scs >= 18:  # Victory condition
                score += self.VICTORY_POINTS
            
            self.performance_scores[power_name] = score
        
        logger.info("Performance scores calculated")
        return self.performance_scores
    
    def calculate_precision_scores(self) -> Dict[str, int]:
        """
        Calculate LLM precision scores based on order quality.

        Analyzes:
        - Invalid orders
        - Successful convoys
        - Successful supports (own/other/hold/attack)
        - Bounced moves
        - Self-attacks (attacking own units)
        - Self-blocks (multiple units to same destination)

        Returns:
            Dict mapping power name to precision score
        """
        from .order_analyzer import OrderAnalyzer

        # Analyze orders
        analyzer = OrderAnalyzer(self.game_folder)
        counts = analyzer.analyze_all_orders()

        # Store counts for reporting
        self.precision_counts = counts

        # Store yearly precision counts
        self.yearly_precision = analyzer.get_yearly_metrics()

        # Store strategic metrics
        self.strategic_metrics = analyzer.get_strategic_metrics()

        # Store derived metrics
        self.complexity_scores = analyzer.compute_order_complexity()
        self.error_rates = analyzer.compute_error_rate()

        # Calculate scores
        for power in Power:
            power_name = power.value
            score = 0

            metrics = counts.get(power_name, {})

            # Apply scoring weights
            score += metrics.get('invalid_orders', 0) * self.INVALID_ORDER_PENALTY
            score += metrics.get('convoys', 0) * self.SUCCESSFUL_CONVOY_POINTS
            score += metrics.get('support_own', 0) * self.SUCCESSFUL_SUPPORT_OWN_POINTS
            score += metrics.get('support_other', 0) * self.SUCCESSFUL_SUPPORT_OTHER_POINTS
            score += metrics.get('support_hold', 0) * self.SUCCESSFUL_SUPPORT_HOLD_POINTS
            score += metrics.get('support_attack', 0) * self.SUCCESSFUL_SUPPORT_ATTACK_POINTS
            score += metrics.get('bounces', 0) * self.BOUNCED_MOVE_PENALTY
            # New penalties
            score += metrics.get('self_attacks', 0) * self.SELF_ATTACK_PENALTY
            score += metrics.get('self_blocks', 0) * self.SELF_BLOCK_PENALTY

            self.precision_scores[power_name] = score

        logger.info("Precision scores calculated")
        return self.precision_scores
    
    def extract_press_scores(self) -> Dict[str, Dict]:
        """
        Extract press evaluation scores from LLM summaries.
        
        Looks for PRESS_SCORES: sections in summaries and extracts:
        - Truthfulness (0-10)
        - Cooperation (0-10)
        - Deception (0-10)
        
        Returns:
            Dict mapping power name to press scores dict
        """
        if not os.path.exists(self.summaries_folder):
            logger.warning("No summaries folder found")
            return self.press_scores
        
        # Get all summary files
        summary_files = sorted([f for f in os.listdir(self.summaries_folder) if f.endswith('.md')])
        
        for filename in summary_files:
            filepath = os.path.join(self.summaries_folder, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Look for PRESS_SCORES: section
            if 'PRESS_SCORES:' in content:
                # Extract scores using regex
                # Pattern: - PowerName: Truthfulness=X, Cooperation=Y, Deception=Z
                pattern = r'- (\w+(?:-\w+)?): Truthfulness=(\d+), Cooperation=(\d+), Deception=(\d+)'
                matches = re.findall(pattern, content)
                
                for match in matches:
                    power_name, truth, coop, decep = match
                    
                    # Initialize the score lists if they don't exist
                    if 'truthfulness' not in self.press_scores.get(power_name, {}):
                        if power_name not in self.press_scores:
                            self.press_scores[power_name] = {}
                        self.press_scores[power_name]['truthfulness'] = []
                        self.press_scores[power_name]['cooperation'] = []
                        self.press_scores[power_name]['deception'] = []
                    
                    self.press_scores[power_name]['truthfulness'].append(int(truth))
                    self.press_scores[power_name]['cooperation'].append(int(coop))
                    self.press_scores[power_name]['deception'].append(int(decep))
        
        logger.info("Press scores extracted from summaries")
        return self.press_scores
    
    def generate_report(self) -> str:
        """
        Generate comprehensive scoring report.
        
        Returns:
            Markdown-formatted report
        """
        # Calculate all scores
        self.calculate_performance_scores()
        self.calculate_precision_scores()
        self.extract_press_scores()
        
        # Build report
        report = "# Model Performance Scoring Report\n\n"
        
        # Add game configuration
        if self.model_assignments:
            report += "## Game Configuration\n\n"
            report += f"- **Game ID**: {self.model_assignments.get('game_id', 'N/A')}\n"
            report += f"- **Platform**: {self.model_assignments.get('platform', 'N/A')}\n"
            report += f"- **Randomized**: {'Yes' if self.model_assignments.get('randomized') else 'No'}\n\n"
            
            report += "### Model Assignments\n\n"
            report += "| Power | Model |\n"
            report += "|-------|-------|\n"
            
            assignments = self.model_assignments.get('assignments', {})
            for power in ['England', 'France', 'Germany', 'Italy', 'Austria-Hungary', 'Russia', 'Turkey']:
                model = assignments.get(power, 'N/A')
                report += f"| {power:15} | {model} |\n"
            report += "\n"
        
        # Overall rankings
        total_scores = {}
        for power in Power:
            power_name = power.value
            total = self.performance_scores.get(power_name, 0) + self.precision_scores.get(power_name, 0)
            total_scores[power_name] = total
        
        ranked = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
        
        report += "## Overall Rankings\n\n"
        report += "| Rank | Power | Total Score | Performance | Precision |\n"
        report += "|------|-------|-------------|-------------|----------|\n"
        
        for rank, (power, total) in enumerate(ranked, 1):
            perf = self.performance_scores.get(power, 0)
            prec = self.precision_scores.get(power, 0)
            report += f"| {rank} | {power:15} | {total:11} | {perf:11} | {prec:8} |\n"
        
        # Detailed Performance breakdown
        report += "\n## Performance Scores - Detailed Breakdown\n\n"
        report += "| Power | Initial SCs | Final SCs | Growth | SC Points | Growth Bonus | Survival | Victory | Total |\n"
        report += "|-------|-------------|-----------|--------|-----------|--------------|----------|---------|-------|\n"
        
        for power in Power:
            power_name = power.value
            details = self.sc_details.get(power_name, {})
            
            initial = details.get('initial', 0)
            final = details.get('final', 0)
            growth = details.get('growth', 0)
            sc_pts = details.get('sc_points', 0)
            growth_pts = details.get('growth_points', 0)
            survival_pts = details.get('survival_points', 0)
            victory_pts = details.get('victory_points', 0)
            total = self.performance_scores.get(power_name, 0)
            
            growth_str = f"+{growth}" if growth > 0 else str(growth)
            report += f"| {power_name:15} | {initial:11} | {final:9} | {growth_str:6} | {sc_pts:9} | {growth_pts:12} | {survival_pts:8} | {victory_pts:7} | {total:5} |\n"
        
        # Press evaluation (if available)
        if any(self.press_scores.values()):
            report += "\n## Press Evaluation Scores\n\n"
            report += "| Power | Avg Truthfulness | Avg Cooperation | Avg Deception |\n"
            report += "|-------|------------------|-----------------|---------------|\n"
            
            for power in Power:
                power_name = power.value
                scores = self.press_scores.get(power_name, {})
                
                if scores:
                    avg_truth = sum(scores.get('truthfulness', [0])) / len(scores.get('truthfulness', [1]))
                    avg_coop = sum(scores.get('cooperation', [0])) / len(scores.get('cooperation', [1]))
                    avg_decep = sum(scores.get('deception', [0])) / len(scores.get('deception', [1]))
                    
                    report += f"| {power_name:15} | {avg_truth:16.1f} | {avg_coop:15.1f} | {avg_decep:13.1f} |\n"
        
        # Precision scores breakdown table
        report += "\n## Precision Scores - Detailed Breakdown\n\n"
        report += "| Power | Model | Invalid Orders | Convoys | Support Own | Support Other | Support Hold | Support Attack | Bounces | Total |\n"
        report += "|-------|-------|----------------|---------|-------------|---------------|--------------|----------------|---------|-------|\n"
        
        for power in Power:
            power_name = power.value
            # Get model for this power
            model = "N/A"
            if self.model_assignments:
                assignments = self.model_assignments.get('assignments', {})
                model = assignments.get(power_name, 'N/A')
                # Shorten model name for display
                if '/' in model:
                    model = model.split('/')[-1]  # OpenRouter format
                elif 'claude' in model.lower():
                    if 'haiku' in model.lower():
                        model = 'Haiku 4.5'
                    elif 'sonnet' in model.lower():
                        model = 'Sonnet 4.5'
            
            # Get actual counts from precision analysis
            counts = getattr(self, 'precision_counts', {}).get(power_name, {})
            invalid = counts.get('invalid_orders', 0)
            convoys = counts.get('convoys', 0)
            supp_own = counts.get('support_own', 0)
            supp_other = counts.get('support_other', 0)
            supp_hold = counts.get('support_hold', 0)
            supp_attack = counts.get('support_attack', 0)
            bounces = counts.get('bounces', 0)
            total = self.precision_scores.get(power_name, 0)
            
            report += f"| {power_name:15} | {model:11} | {invalid:14} | {convoys:7} | {supp_own:11} | {supp_other:13} | {supp_hold:12} | {supp_attack:14} | {bounces:7} | {total:5} |\n"

        # Per-year SC counts (useful for analyzing progress even with interrupted games)
        if self.yearly_sc_counts:
            report += "\n## Per-Year Supply Center Counts\n\n"
            years = sorted(self.yearly_sc_counts.keys())

            # Header row with powers
            report += "| Year |"
            for power in Power:
                report += f" {power.value[:3]} |"
            report += "\n"

            report += "|------|"
            for _ in Power:
                report += "-----|"
            report += "\n"

            # Data rows
            for year in years:
                report += f"| {year} |"
                for power in Power:
                    sc = self.yearly_sc_counts[year].get(power.value, 0)
                    report += f" {sc:3} |"
                report += "\n"

        # Per-year precision metrics
        if self.yearly_precision:
            report += "\n## Per-Year Precision Metrics\n\n"
            years = sorted(self.yearly_precision.keys())

            for year in years:
                report += f"### Year {year}\n\n"
                report += "| Power | Invalid | Convoys | Supp Own | Supp Other | Bounces |\n"
                report += "|-------|---------|---------|----------|------------|--------|\n"

                year_data = self.yearly_precision[year]
                for power in Power:
                    power_name = power.value
                    if power_name in year_data:
                        m = year_data[power_name]
                        report += f"| {power_name:15} | {m.get('invalid_orders', 0):7} | {m.get('convoys', 0):7} | {m.get('support_own', 0):8} | {m.get('support_other', 0):10} | {m.get('bounces', 0):6} |\n"
                report += "\n"

        return report
    
    def save_report(self) -> str:
        """
        Generate and save scoring report.

        Returns:
            Path to saved report
        """
        report = self.generate_report()
        report_path = os.path.join(self.game_folder, "SCORING_REPORT.md")

        with open(report_path, 'w') as f:
            f.write(report)

        # Save yearly metrics as JSON for programmatic access
        yearly_data = {
            "sc_counts": {str(k): v for k, v in self.yearly_sc_counts.items()},
            "precision": {str(k): v for k, v in self.yearly_precision.items()}
        }
        yearly_path = os.path.join(self.game_folder, "yearly_metrics.json")
        with open(yearly_path, 'w') as f:
            json.dump(yearly_data, f, indent=2)

        logger.info(f"Scoring report saved: {report_path}")
        logger.info(f"Yearly metrics saved: {yearly_path}")
        return report_path
