"""
Season summarizer for generating narrative summaries of game phases.
"""

import logging
from typing import Dict, List, Optional
from diplomacy_game_engine.core.game_state import GameState
from diplomacy_game_engine.core.map import Power
from diplomacy_game_engine.core.orders import Order
from diplomacy_game_engine.llm.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class SeasonSummarizer:
    """Generates LLM-based narrative summaries of game seasons."""
    
    def __init__(self, bedrock_client: BedrockClient, model_id: str, token_tracker=None):
        """
        Initialize summarizer.
        
        Args:
            bedrock_client: Bedrock client for LLM calls
            model_id: Model to use for summaries
            token_tracker: Optional TokenTracker for logging token usage
        """
        self.bedrock_client = bedrock_client
        self.model_id = model_id
        self.token_tracker = token_tracker
        logger.info(f"Season summarizer initialized with model: {model_id}")
    
    def generate_summary(
        self,
        phase_name: str,
        press_threads: Dict[str, str],
        orders: List[Order],
        resolution_result,
        state_before: GameState,
        state_after: GameState
    ) -> str:
        """
        Generate a narrative summary of a season.
        
        Args:
            phase_name: Name of the phase (e.g., "Spring 1901")
            press_threads: All press conversations (power_pair -> content)
            orders: All orders submitted
            resolution_result: Resolution result with move outcomes
            state_before: Game state before resolution
            state_after: Game state after resolution
            
        Returns:
            Markdown-formatted summary
        """
        try:
            # Build analysis prompt
            prompt = self._build_summary_prompt(
                phase_name,
                press_threads,
                orders,
                resolution_result,
                state_before,
                state_after
            )
            
            logger.info(f"Generating summary for {phase_name}...")
            
            # Get LLM summary
            summary, token_usage = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                prompt=prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            # Log token usage
            if self.token_tracker:
                self.token_tracker.log_usage(
                    phase=phase_name,
                    call_type="summary",
                    power="Summarizer",
                    model_id=self.model_id,
                    token_usage=token_usage
                )
            
            logger.info(f"Summary generated ({len(summary)} chars, {token_usage['total_tokens']} tokens)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"# {phase_name} Summary\n\nError generating summary: {e}"
    
    def _build_summary_prompt(
        self,
        phase_name: str,
        press_threads: Dict[str, str],
        orders: List[Order],
        resolution_result,
        state_before: GameState,
        state_after: GameState
    ) -> str:
        """Build prompt for summary generation."""
        
        # Collect press activity
        press_summary = self._summarize_press(press_threads)
        
        # Collect order activity
        orders_summary = self._summarize_orders(orders, state_before)
        
        # Collect resolution results
        resolution_summary = self._summarize_resolution(resolution_result)
        
        # Collect SC changes
        sc_changes = self._summarize_sc_changes(state_before, state_after)
        
        # Extract illegal orders for special emphasis
        illegal_orders_section = ""
        if hasattr(resolution_result, 'illegal_orders') and resolution_result.illegal_orders:
            illegal_orders_section = f"""
## ⚠️ ILLEGAL ORDERS (CRITICAL ERRORS)

The following orders were ILLEGAL and were automatically treated as HOLD orders:

{chr(10).join('- ' + order for order in resolution_result.illegal_orders)}

These represent mistakes by the players - they attempted moves that violate Diplomacy rules (non-adjacent provinces, wrong unit types, etc.). These units held position instead of moving.
"""
        
        prompt = f"""You are an expert Diplomacy game analyst. Analyze the following game phase and create a compelling narrative summary.

# PHASE: {phase_name}

## DIPLOMATIC ACTIVITY (Press Messages)
{press_summary}

## MILITARY ORDERS SUBMITTED
{orders_summary}

## RESOLUTION RESULTS
{resolution_summary}

## SUPPLY CENTER CHANGES
{sc_changes}
{illegal_orders_section}
---

# TASK: Create a Narrative Summary

Write a compelling summary of this phase in markdown format. Include:

1. **Diplomatic Landscape** - Key alliances, agreements, and tensions
2. **Military Actions** - Major moves, conflicts, and their outcomes
3. **Strategic Analysis** - Notable strategies, betrayals, or clever plays
4. **Power Rankings** - Who's ahead, who's behind, who's rising/falling

IMPORTANT: If there are any ILLEGAL ORDERS listed above, you MUST mention them in your summary. These represent significant errors by players who attempted invalid moves. Explain what they tried to do and why it was illegal.

Focus on:
- Interesting diplomatic developments (alliances, betrayals, deceptions)
- Significant military outcomes (successful attacks, bounces, dislodgements)
- **Player errors (illegal orders) and their impact**
- Strategic implications for future turns
- Power dynamics and balance shifts

Keep it concise but insightful. Use markdown formatting.

Generate the summary now:
"""
        return prompt
    
    def _summarize_press(self, press_threads: Dict[str, str]) -> str:
        """Summarize press activity."""
        if not press_threads:
            return "No press activity this phase."
        
        lines = []
        for thread_name, content in sorted(press_threads.items()):
            # Count messages in this thread for this phase
            message_count = content.count('[')
            if message_count > 0:
                lines.append(f"- {thread_name}: {message_count} messages")
                # Include a sample of recent messages
                recent = content.split('\n\n')[-2:] if '\n\n' in content else [content]
                for msg in recent:
                    if msg.strip():
                        lines.append(f"  {msg[:200]}...")
        
        return "\n".join(lines) if lines else "No press activity."
    
    def _summarize_orders(self, orders: List[Order], state: GameState) -> str:
        """Summarize orders by power."""
        lines = []
        
        for power in Power:
            power_orders = [o for o in orders if o.unit.power == power]
            if power_orders:
                lines.append(f"\n**{power.value}** ({len(power_orders)} orders):")
                for order in power_orders:
                    lines.append(f"- {order}")
        
        return "\n".join(lines)
    
    def _summarize_resolution(self, resolution_result) -> str:
        """Summarize resolution outcomes."""
        if not resolution_result:
            return "No resolution data available."
        
        successful = sum(1 for r in resolution_result.move_results.values() if 'Successfully' in r)
        bounced = sum(1 for r in resolution_result.move_results.values() if 'Bounced' in r)
        held = sum(1 for r in resolution_result.move_results.values() if 'Held' in r)
        
        lines = [
            f"- Successful moves: {successful}",
            f"- Bounced moves: {bounced}",
            f"- Units held position: {held}",
            f"- Dislodgements: {len(resolution_result.dislodged_units)}"
        ]
        
        # Add detailed move results
        if resolution_result.move_results:
            lines.append("\n**Detailed Move Results:**")
            
            # Group by outcome type
            successful_moves = []
            bounced_moves = []
            held_positions = []
            
            for unit_id, result in sorted(resolution_result.move_results.items()):
                if 'Successfully' in result:
                    successful_moves.append(f"  ✓ {result}")
                elif 'Bounced' in result:
                    bounced_moves.append(f"  ✗ {result}")
                elif 'Held' in result:
                    held_positions.append(f"  • {result}")
            
            if successful_moves:
                lines.append("\nSuccessful Moves:")
                lines.extend(successful_moves)
            
            if bounced_moves:
                lines.append("\nBounced/Failed Moves:")
                lines.extend(bounced_moves)
            
            if held_positions:
                lines.append("\nUnits Holding Position:")
                lines.extend(held_positions)
        
        # Add support information
        if hasattr(resolution_result, 'invalid_supports') and resolution_result.invalid_supports:
            lines.append("\n**Invalid Supports:**")
            for support_info in resolution_result.invalid_supports:
                lines.append(f"  - {support_info}")
        
        if hasattr(resolution_result, 'cut_supports') and resolution_result.cut_supports:
            lines.append("\n**Cut Supports:**")
            for support_info in resolution_result.cut_supports:
                lines.append(f"  - {support_info}")
        
        # Add dislodgement details
        if resolution_result.dislodged_units:
            lines.append("\n**Dislodged Units:**")
            for du in resolution_result.dislodged_units:
                lines.append(f"  - {du.unit.power.value} {du.unit} dislodged from {du.dislodged_from}")
        
        # Add illegal orders
        if hasattr(resolution_result, 'illegal_orders') and resolution_result.illegal_orders:
            lines.append("\n**Illegal Orders (Treated as Hold):**")
            for illegal_order in resolution_result.illegal_orders:
                lines.append(f"  ⚠ {illegal_order}")
        
        return "\n".join(lines)
    
    def _summarize_sc_changes(self, state_before: GameState, state_after: GameState) -> str:
        """Summarize supply center ownership changes."""
        changes = []
        
        # Check each SC for ownership change
        all_scs = set(state_before.supply_centers.keys()) | set(state_after.supply_centers.keys())
        
        for sc in sorted(all_scs):
            before_owner = state_before.supply_centers.get(sc)
            after_owner = state_after.supply_centers.get(sc)
            
            if before_owner != after_owner:
                before_str = before_owner.value if before_owner else "Neutral"
                after_str = after_owner.value if after_owner else "Neutral"
                changes.append(f"- {sc}: {before_str} → {after_str}")
        
        if not changes:
            return "No supply center ownership changes."
        
        return "\n".join(changes)
