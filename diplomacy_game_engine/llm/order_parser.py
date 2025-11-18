"""
Parser for extracting Diplomacy orders from LLM responses.
"""

import re
import logging
from typing import List, Dict, Optional
from diplomacy_game_engine.core.orders import (
    Order, MoveOrder, HoldOrder, SupportOrder, ConvoyOrder,
    RetreatOrder, DisbandOrder, BuildOrder
)
from diplomacy_game_engine.core.map import Power, Coast
from diplomacy_game_engine.core.game_state import UnitType, Unit

logger = logging.getLogger(__name__)


class OrderParser:
    """Parses LLM responses to extract Diplomacy orders."""
    
    # Common province abbreviations and variations
    PROVINCE_ALIASES = {
        'eng': 'ENG', 'english': 'ENG', 'channel': 'ENG',
        'nth': 'NTH', 'north': 'NTH',
        'mao': 'MAO', 'mid': 'MAO', 'atlantic': 'MAO',
        'spa': 'Spa', 'spain': 'Spa',
        'stp': 'StP', 'petersburg': 'StP', 'st.petersburg': 'StP',
        'bul': 'Bul', 'bulgaria': 'Bul',
    }
    
    @staticmethod
    def parse_orders(response: str, power: Power) -> List[Order]:
        """
        Parse orders from LLM response text.
        
        Args:
            response: The LLM's response text
            power: The power submitting orders
            
        Returns:
            List of parsed Order objects
        """
        orders = []
        
        # Try to find structured order blocks
        order_lines = OrderParser._extract_order_lines(response)
        
        for line in order_lines:
            try:
                order = OrderParser._parse_single_order(line, power)
                if order:
                    orders.append(order)
                    logger.debug(f"Parsed order: {order}")
            except Exception as e:
                logger.warning(f"Failed to parse order line '{line}': {e}")
        
        logger.info(f"Parsed {len(orders)} orders for {power.value}")
        return orders
    
    @staticmethod
    def _extract_order_lines(response: str) -> List[str]:
        """Extract individual order lines from response."""
        lines = []
        
        # First, try to extract from code block
        code_block_match = re.search(r'```(?:orders)?\n(.*?)\n```', response, re.DOTALL)
        if code_block_match:
            # Extract content from code block
            block_content = code_block_match.group(1)
            for line in block_content.split('\n'):
                line = line.strip()
                if line and re.match(r'[AF]\s+[A-Za-z]{3}', line, re.IGNORECASE):
                    lines.append(line)
            if lines:
                return lines
        
        # Fallback: Look for common order patterns in full response
        # Pattern 1: "F Lon - ENG" or "A Par H" or "F Bre S A Par - Pic"
        pattern1 = r'[AF]\s+[A-Za-z]{3}(?:/[a-z]{2})?\s+[-HMSC].*'
        
        # Pattern 2: Numbered lists "1. F Lon - ENG"
        pattern2 = r'\d+\.\s+[AF]\s+[A-Za-z]{3}.*'
        
        # Pattern 3: Bullet points "- F Lon - ENG"
        pattern3 = r'[-*]\s+[AF]\s+[A-Za-z]{3}.*'
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Try each pattern
            if re.match(pattern1, line, re.IGNORECASE):
                lines.append(line)
            elif re.match(pattern2, line, re.IGNORECASE):
                # Remove numbering
                line = re.sub(r'^\d+\.\s+', '', line)
                lines.append(line)
            elif re.match(pattern3, line, re.IGNORECASE):
                # Remove bullet
                line = re.sub(r'^[-*]\s+', '', line)
                lines.append(line)
        
        return lines
    
    @staticmethod
    def _parse_single_order(line: str, power: Power) -> Optional[Order]:
        """Parse a single order line."""
        line = line.strip()
        
        # Extract unit type and location
        match = re.match(r'([AF])\s+([A-Za-z]{3}(?:/[a-z]{2})?)', line, re.IGNORECASE)
        if not match:
            return None
        
        unit_type_str = match.group(1).upper()
        location = OrderParser._normalize_province(match.group(2))
        
        unit_type = UnitType.ARMY if unit_type_str == 'A' else UnitType.FLEET
        
        # Extract coast if present
        coast = None
        if '/' in location:
            loc_parts = location.split('/')
            location = loc_parts[0]
            coast_str = loc_parts[1].lower()
            if coast_str in ['nc', 'north']:
                coast = Coast.NORTH
            elif coast_str in ['sc', 'south']:
                coast = Coast.SOUTH
            elif coast_str in ['ec', 'east']:
                coast = Coast.EAST
            elif coast_str in ['wc', 'west']:
                coast = Coast.WEST
        
        # Determine order type
        remainder = line[match.end():].strip()
        
        # Hold order: "H" or "HOLD" or "HOLDS"
        if re.match(r'^H(OLD|OLDS)?$', remainder, re.IGNORECASE):
            unit = Unit(power, unit_type, location, coast)
            return HoldOrder(unit)
        
        # Move order: "- Destination" or "-> Destination" or "M Destination"
        move_match = re.match(
            r'^[-–>]+\s*([A-Za-z]{3}(?:/[a-z]{2})?)|^M(?:OVE)?\s+([A-Za-z]{3}(?:/[a-z]{2})?)',
            remainder,
            re.IGNORECASE
        )
        if move_match:
            dest = move_match.group(1) or move_match.group(2)
            dest = OrderParser._normalize_province(dest)
            
            # Check for convoy flag
            via_convoy = 'convoy' in remainder.lower() or 'via convoy' in remainder.lower()
            
            # Create Unit object
            unit = Unit(power, unit_type, location, coast)
            return MoveOrder(unit, dest, None, via_convoy)
        
        # Support order: "S A Par - Pic" or "SUPPORT A Par - Pic"
        support_match = re.match(
            r'^S(?:UPPORT)?\s+([AF])\s+([A-Za-z]{3}(?:/[a-z]{2})?)\s*(?:[-–>]+\s*([A-Za-z]{3}(?:/[a-z]{2})?)|H(?:OLD)?)?',
            remainder,
            re.IGNORECASE
        )
        if support_match:
            supported_loc = OrderParser._normalize_province(support_match.group(2))
            target = support_match.group(3)
            
            # Create Unit object
            unit = Unit(power, unit_type, location, coast)
            
            if target:
                target = OrderParser._normalize_province(target)
                # SupportOrder(unit, supported_unit_location, supported_unit_coast, destination, dest_coast)
                return SupportOrder(unit, supported_loc, None, target, None)
            else:
                # Support to hold - destination is None
                return SupportOrder(unit, supported_loc, None, None, None)
        
        # Convoy order: "C A Lon - Pic" or "CONVOY A Lon - Pic"
        convoy_match = re.match(
            r'^C(?:ONVOY)?\s+A\s+([A-Za-z]{3})\s*[-–>]+\s*([A-Za-z]{3})',
            remainder,
            re.IGNORECASE
        )
        if convoy_match:
            army_loc = OrderParser._normalize_province(convoy_match.group(1))
            army_dest = OrderParser._normalize_province(convoy_match.group(2))
            
            # Create Unit object
            unit = Unit(power, unit_type, location, coast)
            # ConvoyOrder(unit, convoyed_army_location, destination)
            return ConvoyOrder(unit, army_loc, army_dest)
        
        # If we can't parse it, default to hold
        logger.warning(f"Could not parse order type from '{line}', defaulting to HOLD")
        unit = Unit(power, unit_type, location, coast)
        return HoldOrder(unit)
    
    @staticmethod
    def _normalize_province(province: str) -> str:
        """Normalize province name/abbreviation."""
        province = province.strip()
        
        # Remove coast notation for lookup
        base_province = province.split('/')[0]
        
        # Check aliases
        lower_prov = base_province.lower()
        if lower_prov in OrderParser.PROVINCE_ALIASES:
            base_province = OrderParser.PROVINCE_ALIASES[lower_prov]
        else:
            # Capitalize first letter
            base_province = base_province.capitalize()
        
        # Re-add coast if present
        if '/' in province:
            coast_part = province.split('/')[1]
            return f"{base_province}/{coast_part}"
        
        return base_province
    
    @staticmethod
    def parse_press_messages(response: str, power: Power) -> Dict[str, str]:
        """
        Parse press messages from LLM response.
        
        Expected format:
        TO FRANCE: "Message text here"
        TO GERMANY: "Another message"
        
        Args:
            response: The LLM's response text
            power: The power sending messages
            
        Returns:
            Dictionary mapping recipient power names to message text
        """
        messages = {}
        
        # First, try to extract from code block
        code_block_match = re.search(r'```(?:messages)?\n(.*?)\n```', response, re.DOTALL)
        if code_block_match:
            response = code_block_match.group(1)
        
        # Pattern: "TO POWER:" or "To Power:" followed by message
        pattern = r'TO\s+([A-Z]+):\s*["\']?(.+?)["\']?(?=\n|$)'
        
        for match in re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE):
            recipient_name = match.group(1).upper()
            message_text = match.group(2).strip()
            
            # Try to match to a valid power
            try:
                # Handle common variations
                if recipient_name in ['ENGLAND', 'ENGLISH']:
                    recipient_name = 'England'
                elif recipient_name in ['FRANCE', 'FRENCH']:
                    recipient_name = 'France'
                elif recipient_name in ['GERMANY', 'GERMAN']:
                    recipient_name = 'Germany'
                elif recipient_name in ['ITALY', 'ITALIAN']:
                    recipient_name = 'Italy'
                elif recipient_name in ['AUSTRIA', 'AUSTRIAN', 'AUSTRIA-HUNGARY', 'AUSTRIAHUNGARY']:
                    recipient_name = 'Austria-Hungary'
                elif recipient_name in ['RUSSIA', 'RUSSIAN']:
                    recipient_name = 'Russia'
                elif recipient_name in ['TURKEY', 'TURKISH']:
                    recipient_name = 'Turkey'
                
                # Validate it's a real power
                Power(recipient_name)
                messages[recipient_name] = message_text
                logger.debug(f"{power.value} -> {recipient_name}: {message_text[:50]}...")
                
            except ValueError:
                logger.warning(f"Invalid recipient power: {recipient_name}")
        
        logger.info(f"Parsed {len(messages)} press messages from {power.value}")
        return messages
    
    @staticmethod
    def parse_retreat_orders(response: str, power: Power) -> List[RetreatOrder]:
        """Parse retreat orders from LLM response."""
        orders = []
        
        # Similar to regular orders but specifically for retreats
        order_lines = OrderParser._extract_order_lines(response)
        
        for line in order_lines:
            try:
                # Parse unit and destination
                match = re.match(
                    r'([AF])\s+([A-Za-z]{3}(?:/[a-z]{2})?)\s*[-–>]+\s*([A-Za-z]{3}(?:/[a-z]{2})?)',
                    line,
                    re.IGNORECASE
                )
                if match:
                    unit_type = UnitType.ARMY if match.group(1).upper() == 'A' else UnitType.FLEET
                    from_loc = OrderParser._normalize_province(match.group(2))
                    to_loc = OrderParser._normalize_province(match.group(3))
                    
                    # Create Unit object
                    unit = Unit(power, unit_type, from_loc, None)
                    # RetreatOrder(unit, destination, dest_coast)
                    orders.append(RetreatOrder(unit, to_loc, None))
                    logger.debug(f"Parsed retreat: {unit_type.value[0]} {from_loc} -> {to_loc}")
            except Exception as e:
                logger.warning(f"Failed to parse retreat order '{line}': {e}")
        
        return orders
    
    @staticmethod
    def parse_build_disband_orders(response: str, power: Power) -> List[Order]:
        """Parse build/disband orders from LLM response."""
        orders = []
        
        # Build pattern: "BUILD F Lon" or "B F Lon"
        build_pattern = r'B(?:UILD)?\s+([AF])\s+([A-Za-z]{3}(?:/[a-z]{2})?)'
        
        # Disband pattern: "DISBAND A Par" or "D A Par" or "REMOVE A Par"
        disband_pattern = r'(?:D(?:ISBAND)?|R(?:EMOVE)?)\s+([AF])\s+([A-Za-z]{3}(?:/[a-z]{2})?)'
        
        for line in response.split('\n'):
            line = line.strip()
            
            # Try build
            match = re.match(build_pattern, line, re.IGNORECASE)
            if match:
                unit_type = UnitType.ARMY if match.group(1).upper() == 'A' else UnitType.FLEET
                location = OrderParser._normalize_province(match.group(2))
                orders.append(BuildOrder(power, unit_type, location))
                continue
            
            # Try disband
            match = re.match(disband_pattern, line, re.IGNORECASE)
            if match:
                unit_type = UnitType.ARMY if match.group(1).upper() == 'A' else UnitType.FLEET
                location = OrderParser._normalize_province(match.group(2))
                # Create Unit object for DisbandOrder
                unit = Unit(power, unit_type, location, None)
                orders.append(DisbandOrder(unit))
        
        logger.info(f"Parsed {len(orders)} build/disband orders for {power.value}")
        return orders
