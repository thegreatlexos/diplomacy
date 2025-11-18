"""
Press system for managing diplomatic messages between powers.
"""

import os
from typing import Dict, Set
from diplomacy_game_engine.core.map import Power
import logging

logger = logging.getLogger(__name__)


class PressSystem:
    """Manages press (diplomatic messages) between powers using file-based threads."""
    
    def __init__(self, game_folder: str):
        """
        Initialize press system.
        
        Args:
            game_folder: Root folder for the game
        """
        self.game_folder = game_folder
        self.press_folder = os.path.join(game_folder, "press")
        
        # Create press folder if it doesn't exist
        os.makedirs(self.press_folder, exist_ok=True)
        
        logger.info(f"Press system initialized at {self.press_folder}")
    
    def _get_thread_filename(self, power1: Power, power2: Power) -> str:
        """
        Get the filename for a bilateral thread between two powers.
        Uses alphabetical ordering to ensure consistency.
        
        Args:
            power1: First power
            power2: Second power
            
        Returns:
            Filename for the thread
        """
        # Sort alphabetically to ensure consistent naming
        powers = sorted([power1.value, power2.value])
        return f"{powers[0].lower()}_{powers[1].lower()}.txt"
    
    def _get_thread_path(self, power1: Power, power2: Power) -> str:
        """Get full path to thread file."""
        filename = self._get_thread_filename(power1, power2)
        return os.path.join(self.press_folder, filename)
    
    def send_message(
        self,
        from_power: Power,
        to_power: Power,
        message: str,
        phase: str,
        round_number: int
    ) -> None:
        """
        Send a message from one power to another.
        
        Args:
            from_power: Power sending the message
            to_power: Power receiving the message
            message: Message content
            phase: Current phase (e.g., "Spring 1901")
            round_number: Press round number (1, 2, or 3)
        """
        if from_power == to_power:
            logger.warning(f"Cannot send message to self: {from_power.value}")
            return
        
        thread_path = self._get_thread_path(from_power, to_power)
        
        # Format message entry
        header = f"[{phase} - Press Round {round_number}]"
        entry = f"{header}\n{from_power.value}: {message}\n\n"
        
        # Append to thread file
        with open(thread_path, 'a') as f:
            f.write(entry)
        
        logger.info(f"Message sent: {from_power.value} -> {to_power.value} ({len(message)} chars)")
    
    def send_messages(
        self,
        from_power: Power,
        messages: Dict[str, str],
        phase: str,
        round_number: int
    ) -> None:
        """
        Send multiple messages from one power to others.
        
        Args:
            from_power: Power sending messages
            messages: Dictionary mapping recipient power names to message text
            phase: Current phase
            round_number: Press round number
        """
        for recipient_name, message in messages.items():
            try:
                to_power = Power(recipient_name)
                self.send_message(from_power, to_power, message, phase, round_number)
            except ValueError:
                logger.warning(f"Invalid recipient power: {recipient_name}")
    
    def get_thread_content(self, power1: Power, power2: Power) -> str:
        """
        Get the complete content of a thread between two powers.
        
        Args:
            power1: First power
            power2: Second power
            
        Returns:
            Thread content as string, or empty string if no thread exists
        """
        thread_path = self._get_thread_path(power1, power2)
        
        if not os.path.exists(thread_path):
            return ""
        
        with open(thread_path, 'r') as f:
            return f.read()
    
    def get_all_threads_for_power(self, power: Power) -> Dict[str, str]:
        """
        Get all press threads involving a specific power.
        
        Args:
            power: The power to get threads for
            
        Returns:
            Dictionary mapping other power names to thread content
        """
        threads = {}
        
        for other_power in Power:
            if other_power == power:
                continue
            
            content = self.get_thread_content(power, other_power)
            if content:
                threads[other_power.value] = content
        
        return threads
    
    def clear_all_threads(self) -> None:
        """Clear all press threads (for starting a new game)."""
        if os.path.exists(self.press_folder):
            for filename in os.listdir(self.press_folder):
                if filename.endswith('.txt'):
                    filepath = os.path.join(self.press_folder, filename)
                    os.remove(filepath)
            logger.info("All press threads cleared")
    
    def get_thread_summary(self) -> Dict[str, int]:
        """
        Get summary of all threads.
        
        Returns:
            Dictionary mapping thread names to message counts
        """
        summary = {}
        
        if not os.path.exists(self.press_folder):
            return summary
        
        for filename in os.listdir(self.press_folder):
            if filename.endswith('.txt'):
                filepath = os.path.join(self.press_folder, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    # Count message headers
                    message_count = content.count('[')
                    summary[filename[:-4]] = message_count  # Remove .txt extension
        
        return summary
