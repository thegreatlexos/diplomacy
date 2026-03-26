"""
Press analyzer for communication metrics.

Analyzes diplomatic messages for:
1. Communication volume (messages, words per model)
2. Say-do correlation (did they do what they promised?)
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import yaml


class PressAnalyzer:
    """Analyzes press (diplomatic messages) for metrics."""

    # Order patterns in text
    ORDER_PATTERNS = [
        # Standard notation: A Bel - Ruh, F NTH S A Bel - Ruh
        r'\b([AF])\s+([A-Za-z]{2,4})\s*[-–]\s*([A-Za-z]{2,4})\b',  # Move
        r'\b([AF])\s+([A-Za-z]{2,4})\s+[Ss](?:upport)?\s+([AF])\s+([A-Za-z]{2,4})\s*[-–]\s*([A-Za-z]{2,4})\b',  # Support move
        r'\b([AF])\s+([A-Za-z]{2,4})\s+[Ss](?:upport)?\s+([AF])\s+([A-Za-z]{2,4})\b',  # Support hold
        r'\b([AF])\s+([A-Za-z]{2,4})\s+[Hh](?:old)?\b',  # Hold
    ]

    # Natural language patterns
    NL_MOVE_PATTERNS = [
        r"(?:I'll|I will|I'm|I am)\s+(?:move|moving|push|pushing)\s+(?:my\s+)?(?:army|fleet|A|F)?\s*(?:from\s+)?([A-Za-z]+)\s+(?:to|into|toward|towards)\s+([A-Za-z]+)",
        r"(?:move|moving)\s+(?:to|into)\s+([A-Za-z]+)",
        r"(?:take|taking|secure|securing)\s+([A-Za-z]+)",
    ]

    NL_SUPPORT_PATTERNS = [
        r"(?:I'll|I will)\s+support\s+(?:your|the)\s+(?:move|advance)\s+(?:into|to)\s+([A-Za-z]+)",
        r"support\s+(?:your|the)\s+([A-Za-z]+)\s+(?:move|advance)",
    ]

    def __init__(self, game_folder: str):
        self.game_folder = Path(game_folder)
        self.press_folder = self.game_folder / "press"
        self.orders_folder = self.game_folder / "orders"

        # Load model assignments
        assignments_file = self.game_folder / "model_assignments.json"
        if assignments_file.exists():
            import json
            with open(assignments_file) as f:
                data = json.load(f)
            self.assignments = data.get("assignments", {})
        else:
            self.assignments = {}

        # Results
        self.volume_metrics = {}
        self.saydo_metrics = {}

    def analyze_volume(self) -> Dict[str, Dict]:
        """
        Analyze communication volume per power.

        Returns dict per power:
        - messages_sent: total messages
        - words_sent: total words
        - avg_words_per_message: average message length
        - unique_recipients: number of powers communicated with
        - messages_per_phase: messages divided by game phases
        """
        if not self.press_folder.exists():
            return {}

        power_stats = defaultdict(lambda: {
            "messages_sent": 0,
            "words_sent": 0,
            "recipients": set(),
            "phases": set(),
        })

        for press_file in self.press_folder.glob("*.txt"):
            # Extract powers from filename (e.g., "england_france.txt")
            powers = press_file.stem.replace("-", "_").split("_")
            # Handle compound names like austria-hungary
            if len(powers) == 3 and powers[0] == "austria":
                powers = ["austria-hungary", powers[2]]
            elif len(powers) == 4:
                powers = [f"{powers[0]}-{powers[1]}", f"{powers[2]}-{powers[3]}"]

            if len(powers) != 2:
                continue

            power1, power2 = self._normalize_power_name(powers[0]), self._normalize_power_name(powers[1])

            # Parse messages
            content = press_file.read_text()
            messages = self._parse_messages(content)

            for sender, phase, text in messages:
                sender_normalized = self._normalize_power_name(sender)
                recipient = power2 if sender_normalized == power1 else power1

                power_stats[sender_normalized]["messages_sent"] += 1
                power_stats[sender_normalized]["words_sent"] += len(text.split())
                power_stats[sender_normalized]["recipients"].add(recipient)
                power_stats[sender_normalized]["phases"].add(phase)

        # Compute final metrics
        results = {}
        for power, stats in power_stats.items():
            n_messages = stats["messages_sent"]
            results[power] = {
                "messages_sent": n_messages,
                "words_sent": stats["words_sent"],
                "avg_words_per_message": stats["words_sent"] / n_messages if n_messages > 0 else 0,
                "unique_recipients": len(stats["recipients"]),
                "phases_active": len(stats["phases"]),
                "messages_per_phase": n_messages / len(stats["phases"]) if stats["phases"] else 0,
            }

        self.volume_metrics = results
        return results

    def analyze_saydo(self) -> Dict[str, Dict]:
        """
        Analyze say-do correlation: did powers do what they promised?

        Returns dict per power:
        - promises_made: number of explicit order promises found
        - promises_kept: number that matched actual orders
        - saydo_rate: promises_kept / promises_made
        """
        if not self.press_folder.exists() or not self.orders_folder.exists():
            return {}

        # Load all actual orders by phase
        actual_orders = self._load_actual_orders()

        power_stats = defaultdict(lambda: {
            "promises_made": 0,
            "promises_kept": 0,
            "promises": [],  # For debugging
        })

        for press_file in self.press_folder.glob("*.txt"):
            content = press_file.read_text()
            messages = self._parse_messages(content)

            for sender, phase, text in messages:
                sender_normalized = self._normalize_power_name(sender)

                # Extract promised orders from text
                promised = self._extract_promised_orders(text)

                # Normalize phase: "Spring 1901 - Press Round 1" -> "Spring 1901"
                phase_normalized = phase.split(" - ")[0] if " - " in phase else phase

                for order_type, locations in promised:
                    power_stats[sender_normalized]["promises_made"] += 1
                    power_stats[sender_normalized]["promises"].append({
                        "phase": phase_normalized,
                        "order": (order_type, locations),
                        "text_snippet": text[:100],
                    })

                    # Check if this matches actual orders
                    phase_orders = actual_orders.get(phase_normalized, {}).get(sender_normalized, [])
                    if self._order_matches(order_type, locations, phase_orders):
                        power_stats[sender_normalized]["promises_kept"] += 1

        # Compute final metrics
        results = {}
        for power, stats in power_stats.items():
            made = stats["promises_made"]
            results[power] = {
                "promises_made": made,
                "promises_kept": stats["promises_kept"],
                "saydo_rate": stats["promises_kept"] / made if made > 0 else None,
            }

        self.saydo_metrics = results
        return results

    def _parse_messages(self, content: str) -> List[Tuple[str, str, str]]:
        """Parse press file into list of (sender, phase, text) tuples."""
        messages = []
        # Pattern: [Season Year - Press Round N]\nPower: message
        pattern = r'\[([^\]]+)\]\s*\n([A-Za-z-]+):\s*(.+?)(?=\n\[|\Z)'

        for match in re.finditer(pattern, content, re.DOTALL):
            phase = match.group(1).strip()
            sender = match.group(2).strip()
            text = match.group(3).strip()
            messages.append((sender, phase, text))

        return messages

    def _extract_promised_orders(self, text: str) -> List[Tuple[str, Tuple]]:
        """Extract promised orders from message text."""
        orders = []

        # Standard order notation: A Bel - Ruh
        move_pattern = r'\b([AF])\s+([A-Za-z]{2,4})\s*[-–]\s*([A-Za-z]{2,4})\b'
        for match in re.finditer(move_pattern, text, re.IGNORECASE):
            unit_type = match.group(1).upper()
            source = match.group(2).upper()
            dest = match.group(3).upper()
            orders.append(("move", (unit_type, source, dest)))

        # Support patterns: A Bel S A Bur - Mun
        support_pattern = r'\b([AF])\s+([A-Za-z]{2,4})\s+[Ss]\s+([AF])\s+([A-Za-z]{2,4})\s*[-–]\s*([A-Za-z]{2,4})\b'
        for match in re.finditer(support_pattern, text, re.IGNORECASE):
            orders.append(("support_move", (
                match.group(1).upper(),
                match.group(2).upper(),
                match.group(3).upper(),
                match.group(4).upper(),
                match.group(5).upper(),
            )))

        return orders

    def _load_actual_orders(self) -> Dict[str, Dict[str, List[dict]]]:
        """Load actual submitted orders by phase and power, using state files for ownership."""
        import json
        orders_by_phase = {}
        states_folder = self.game_folder / "states"

        for order_file in self.orders_folder.glob("*.yaml"):
            # Extract phase info from filename (e.g., "1901_01_spring.yaml")
            filename = order_file.stem
            phase = self._filename_to_phase(filename)
            if not phase:
                continue

            with open(order_file) as f:
                data = yaml.safe_load(f)

            if not data or "orders" not in data:
                continue

            # Find the state file BEFORE this phase to get unit ownership
            # For spring, use initial; for fall, use spring_after
            parts = filename.split("_")
            year = parts[0]
            season = parts[2] if len(parts) >= 3 else ""

            if season.lower() == "spring":
                state_file = states_folder / f"{year}_00_initial.json"
            else:
                state_file = states_folder / f"{year}_spring_after.json"

            # Load unit ownership
            unit_to_power = {}
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                for unit in state.get("units", []):
                    loc = unit["location"].upper()
                    power = unit["power"]
                    unit_to_power[loc] = power

            # Map orders to powers
            orders_by_phase[phase] = defaultdict(list)
            for order in data.get("orders", []):
                # Parse unit location from order (e.g., "F Lon" -> "LON")
                unit_str = order.get("unit", "")
                parts = unit_str.split()
                if len(parts) >= 2:
                    loc = parts[1].upper()
                    power = unit_to_power.get(loc)
                    if power:
                        power_normalized = self._normalize_power_name(power)
                        orders_by_phase[phase][power_normalized].append(order)

        return orders_by_phase

    def _filename_to_phase(self, filename: str) -> Optional[str]:
        """Convert filename like '1901_01_spring' to phase string."""
        parts = filename.split("_")
        if len(parts) >= 3:
            year = parts[0]
            season = parts[2].capitalize()
            return f"{season} {year}"
        return None

    def _order_matches(self, order_type: str, locations: Tuple, actual_orders: List[dict]) -> bool:
        """Check if promised order matches any actual order (lenient matching)."""
        for actual in actual_orders:
            if not isinstance(actual, dict):
                continue

            action = actual.get("action", "").lower()
            unit = actual.get("unit", "").upper()
            dest = actual.get("destination", "").upper()
            target = actual.get("target", "").upper()  # For supports

            if order_type == "move":
                _, source, promised_dest = locations
                source = source.upper()
                promised_dest = promised_dest.upper()
                # Match if same source unit moving to same destination
                if action == "move" and source in unit and promised_dest == dest:
                    return True
                # Lenient: just check destination matches
                if action == "move" and promised_dest == dest:
                    return True

            elif order_type == "support_move":
                _, supporter_loc, _, supported_from, supported_to = locations
                supporter_loc = supporter_loc.upper()
                supported_to = supported_to.upper()
                # Match support order
                if action == "support" and supporter_loc in unit:
                    if supported_to in dest or supported_to in target:
                        return True

        return False

    def _normalize_power_name(self, name: str) -> str:
        """Normalize power name to standard format."""
        name = name.lower().strip()
        mappings = {
            "england": "England",
            "france": "France",
            "germany": "Germany",
            "italy": "Italy",
            "austria": "Austria-Hungary",
            "austria-hungary": "Austria-Hungary",
            "austria_hungary": "Austria-Hungary",
            "russia": "Russia",
            "turkey": "Turkey",
        }
        return mappings.get(name, name.title())

    def get_metrics_by_model(self) -> Dict[str, Dict]:
        """Aggregate metrics by model type."""
        from scripts.plot_sc_comparison import normalize_model

        if not self.volume_metrics:
            self.analyze_volume()
        if not self.saydo_metrics:
            self.analyze_saydo()

        model_volume = defaultdict(lambda: {
            "messages_sent": [],
            "words_sent": [],
            "avg_words_per_message": [],
            "messages_per_phase": [],
        })

        model_saydo = defaultdict(lambda: {
            "promises_made": [],
            "promises_kept": [],
            "saydo_rate": [],
        })

        for power, model_id in self.assignments.items():
            model = normalize_model(model_id)

            if power in self.volume_metrics:
                vol = self.volume_metrics[power]
                model_volume[model]["messages_sent"].append(vol["messages_sent"])
                model_volume[model]["words_sent"].append(vol["words_sent"])
                model_volume[model]["avg_words_per_message"].append(vol["avg_words_per_message"])
                model_volume[model]["messages_per_phase"].append(vol["messages_per_phase"])

            if power in self.saydo_metrics:
                sd = self.saydo_metrics[power]
                model_saydo[model]["promises_made"].append(sd["promises_made"])
                model_saydo[model]["promises_kept"].append(sd["promises_kept"])
                if sd["saydo_rate"] is not None:
                    model_saydo[model]["saydo_rate"].append(sd["saydo_rate"])

        return {
            "volume": dict(model_volume),
            "saydo": dict(model_saydo),
        }
