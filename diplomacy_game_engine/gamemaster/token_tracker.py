"""
Token usage tracker for monitoring LLM API costs.
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TokenTracker:
    """Tracks token usage across all LLM calls in a game."""
    
    # Model pricing (per 1M tokens) - Based on OpenRouter pricing
    MODEL_PRICING = {
        # Anthropic Claude models
        "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        
        # Google Gemini models
        "gemini-2-5-pro": {"input": 1.25, "output": 10.00},
        "gemini-2-5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2-5-flash-lite": {"input": 0.10, "output": 0.40},
        "gemini-pro": {"input": 1.25, "output": 10.00},  # Alias for 2.5 Pro
        "gemini-flash": {"input": 0.30, "output": 2.50},  # Alias for 2.5 Flash
        
        # OpenAI GPT models
        "gpt-5": {"input": 1.25, "output": 10.00},
        "gpt-5-1": {"input": 1.25, "output": 10.00},
        "gpt-5-mini": {"input": 0.25, "output": 2.00},
        "gpt-5-1-mini": {"input": 0.25, "output": 2.00},
        "gpt-5-1-codex": {"input": 1.25, "output": 10.00},
        "gpt-5-1-codex-mini": {"input": 0.25, "output": 2.00},
        
        # xAI Grok models
        "grok-4": {"input": 3.00, "output": 15.00},
        "grok-4-fast": {"input": 0.20, "output": 0.50},
        "grok-code-fast": {"input": 0.20, "output": 1.50},
        
        # Meta Llama models
        "llama-4-maverick": {"input": 0.15, "output": 0.60},
        "llama-4-scout": {"input": 0.08, "output": 0.30},
        "llama-3-3-70b": {"input": 0.15, "output": 0.60},  # Alias for Maverick
        "llama-3-1-8b": {"input": 0.08, "output": 0.30},   # Alias for Scout
        
        # DeepSeek models
        "deepseek-v3-1-terminus": {"input": 0.23, "output": 0.90},
        "deepseek-r1-distill-llama-70b": {"input": 0.03, "output": 0.13},
        "deepseek-r1-distill-qwen-32b": {"input": 0.27, "output": 0.27},
        "deepseek-r1-distill-qwen-14b": {"input": 0.15, "output": 0.15},
        "deepseek-v3": {"input": 0.23, "output": 0.90},  # Alias for Terminus
        
        # Mistral models
        "mistral-large": {"input": 2.00, "output": 6.00},
        "mistral-small-3": {"input": 0.05, "output": 0.08},
        "mistral-small-3-2": {"input": 0.06, "output": 0.18},
        
        # Fallbacks
        "claude-haiku": {"input": 1.00, "output": 5.00},
        "claude-sonnet": {"input": 3.00, "output": 15.00},
        "default": {"input": 1.00, "output": 5.00}
    }
    
    def __init__(self, game_folder: str):
        """
        Initialize token tracker.
        
        Args:
            game_folder: Root folder for game files
        """
        self.game_folder = game_folder
        self.csv_path = os.path.join(game_folder, "token_usage.csv")
        self.records: List[Dict] = []
        
        # Initialize CSV file with headers
        self._initialize_csv()
        
        logger.info(f"Token tracker initialized: {self.csv_path}")
    
    def _initialize_csv(self):
        """Create CSV file with headers."""
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'phase',
                'call_type',
                'power',
                'model_id',
                'input_tokens',
                'output_tokens',
                'total_tokens',
                'estimated_cost_usd'
            ])
    
    def log_usage(
        self,
        phase: str,
        call_type: str,
        power: str,
        model_id: str,
        token_usage: Dict[str, int]
    ):
        """
        Log a single LLM call's token usage.
        
        Args:
            phase: Game phase (e.g., "Spring 1901")
            call_type: Type of call (e.g., "press_round_1", "movement_orders", "summary")
            power: Power making the call (e.g., "England", "Summarizer")
            model_id: Bedrock model ID
            token_usage: Dict with input_tokens, output_tokens, total_tokens
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate estimated cost
        cost = self._calculate_cost(model_id, token_usage)
        
        # Create record
        record = {
            'timestamp': timestamp,
            'phase': phase,
            'call_type': call_type,
            'power': power,
            'model_id': model_id,
            'input_tokens': token_usage['input_tokens'],
            'output_tokens': token_usage['output_tokens'],
            'total_tokens': token_usage['total_tokens'],
            'estimated_cost_usd': f"{cost:.6f}"
        }
        
        # Store in memory
        self.records.append(record)
        
        # Append to CSV
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            writer.writerow(record)
        
        logger.debug(f"Logged: {power} {call_type} - {token_usage['total_tokens']} tokens (${cost:.4f})")
    
    def _calculate_cost(self, model_id: str, token_usage: Dict[str, int]) -> float:
        """Calculate estimated cost in USD."""
        # Find pricing for this model
        pricing = None
        model_lower = model_id.lower()
        
        for model_key, model_pricing in self.MODEL_PRICING.items():
            if model_key in model_lower:
                pricing = model_pricing
                break
        
        if not pricing:
            pricing = self.MODEL_PRICING["default"]
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (token_usage['input_tokens'] / 1_000_000) * pricing['input']
        output_cost = (token_usage['output_tokens'] / 1_000_000) * pricing['output']
        
        return input_cost + output_cost
    
    def _load_model_assignments(self) -> Optional[Dict]:
        """Load model assignments from JSON file if it exists."""
        assignments_path = os.path.join(self.game_folder, "model_assignments.json")
        if os.path.exists(assignments_path):
            try:
                with open(assignments_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load model assignments: {e}")
        return None
    
    def generate_report(self) -> str:
        """
        Generate a markdown report of token usage.
        
        Returns:
            Markdown-formatted report
        """
        if not self.records:
            return "# Token Usage Report\n\nNo LLM calls recorded."
        
        # Load model assignments if available
        assignments_data = self._load_model_assignments()
        
        # Calculate totals
        total_input = sum(r['input_tokens'] for r in self.records)
        total_output = sum(r['output_tokens'] for r in self.records)
        total_tokens = sum(r['total_tokens'] for r in self.records)
        total_cost = sum(float(r['estimated_cost_usd']) for r in self.records)
        
        # Group by power
        by_power = {}
        for record in self.records:
            power = record['power']
            if power not in by_power:
                by_power[power] = {
                    'calls': 0,
                    'input': 0,
                    'output': 0,
                    'total': 0,
                    'cost': 0.0
                }
            by_power[power]['calls'] += 1
            by_power[power]['input'] += record['input_tokens']
            by_power[power]['output'] += record['output_tokens']
            by_power[power]['total'] += record['total_tokens']
            by_power[power]['cost'] += float(record['estimated_cost_usd'])
        
        # Group by call type
        by_type = {}
        for record in self.records:
            call_type = record['call_type']
            if call_type not in by_type:
                by_type[call_type] = {
                    'calls': 0,
                    'tokens': 0,
                    'cost': 0.0
                }
            by_type[call_type]['calls'] += 1
            by_type[call_type]['tokens'] += record['total_tokens']
            by_type[call_type]['cost'] += float(record['estimated_cost_usd'])
        
        # Group by model
        by_model = {}
        for record in self.records:
            model_id = record['model_id']
            if model_id not in by_model:
                by_model[model_id] = {
                    'calls': 0,
                    'input': 0,
                    'output': 0,
                    'total': 0,
                    'cost': 0.0
                }
            by_model[model_id]['calls'] += 1
            by_model[model_id]['input'] += record['input_tokens']
            by_model[model_id]['output'] += record['output_tokens']
            by_model[model_id]['total'] += record['total_tokens']
            by_model[model_id]['cost'] += float(record['estimated_cost_usd'])
        
        # Build report with model assignments if available
        report = "# Token Usage Report\n\n"
        
        # Add model assignments section if available
        if assignments_data:
            report += "## Game Configuration\n"
            report += f"- **Game ID**: {assignments_data.get('game_id', 'N/A')}\n"
            report += f"- **Platform**: {assignments_data.get('platform', 'N/A')}\n"
            report += f"- **Randomized**: {'Yes' if assignments_data.get('randomized') else 'No'}\n"
            report += f"- **Timestamp**: {assignments_data.get('timestamp', 'N/A')}\n\n"
            
            report += "## Model Assignments\n\n"
            report += "| Power | Model |\n"
            report += "|-------|-------|\n"
            
            assignments = assignments_data.get('assignments', {})
            for power in ['ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'AUSTRIA', 'RUSSIA', 'TURKEY']:
                model = assignments.get(power, 'N/A')
                report += f"| {power:15} | {model} |\n"
            
            summarizer = assignments_data.get('summarizer')
            if summarizer:
                report += f"| {'Summarizer':15} | {summarizer} |\n"
            
            report += "\n"
        
        report += f"""## Summary
- **Total Calls**: {len(self.records)}
- **Total Input Tokens**: {total_input:,}
- **Total Output Tokens**: {total_output:,}
- **Total Tokens**: {total_tokens:,}
- **Estimated Cost**: ${total_cost:.4f}

## By Power

| Power | Calls | Input | Output | Total | Cost |
|-------|-------|-------|--------|-------|------|
"""
        
        for power in sorted(by_power.keys()):
            stats = by_power[power]
            report += f"| {power:15} | {stats['calls']:5} | {stats['input']:7,} | {stats['output']:7,} | {stats['total']:8,} | ${stats['cost']:.4f} |\n"
        
        report += f"""
## By Model

| Model ID | Calls | Input | Output | Total | Cost |
|----------|-------|-------|--------|-------|------|
"""
        
        for model_id in sorted(by_model.keys()):
            stats = by_model[model_id]
            # Shorten model ID for display
            display_id = model_id.split(':')[-2] if ':' in model_id else model_id
            report += f"| {display_id:40} | {stats['calls']:5} | {stats['input']:7,} | {stats['output']:7,} | {stats['total']:8,} | ${stats['cost']:.4f} |\n"
        
        report += f"""
## By Call Type

| Type | Calls | Total Tokens | Cost |
|------|-------|--------------|------|
"""
        
        for call_type in sorted(by_type.keys()):
            stats = by_type[call_type]
            report += f"| {call_type:20} | {stats['calls']:5} | {stats['tokens']:12,} | ${stats['cost']:.4f} |\n"
        
        report += f"""
## Details

See `token_usage.csv` for detailed per-call breakdown.
"""
        
        return report
    
    def save_report(self):
        """Save the token usage report to a markdown file."""
        report = self.generate_report()
        report_path = os.path.join(self.game_folder, "TOKEN_USAGE_REPORT.md")
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Token usage report saved: {report_path}")
        return report_path
