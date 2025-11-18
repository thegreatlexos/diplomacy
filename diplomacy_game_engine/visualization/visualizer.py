"""
Visualization module for Diplomacy game engine.
Creates a simplified geometric map display of the game state.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Polygon, FancyBboxPatch, RegularPolygon
from matplotlib.image import imread
from typing import Dict, Tuple, Optional
import math
import os

from diplomacy_game_engine.core.game_state import GameState, Unit, UnitType
from diplomacy_game_engine.core.map import Power, ProvinceType


# Power colors matching the reference image
POWER_COLORS = {
    Power.ENGLAND: '#4169E1',      # Royal Blue
    Power.FRANCE: '#E6E6FA',       # Lavender (light)
    Power.GERMANY: '#696969',      # Dim Gray
    Power.ITALY: '#90EE90',        # Light Green
    Power.AUSTRIA: '#CD5C5C',      # Indian Red
    Power.RUSSIA: '#DDA0DD',       # Plum (purple/pink)
    Power.TURKEY: '#F0E68C',       # Khaki (yellow/olive)
}

# Province center coordinates in ABSOLUTE PIXELS
# Base image: 915×767 pixels (europemapbw.png)
# Manually calibrated using interactive_calibrator.py
# Y-axis flipped for matplotlib: matplotlib_y = 767 - pixel_y
PROVINCE_POSITIONS = {
    # British Isles
    "Lon": (286, 389), "Edi": (276, 500), "Lvp": (265, 443),
    "Wal": (247, 395), "Yor": (286, 432), "Cly": (247, 500),
    
    # France & Iberia
    "Par": (283, 295), "Bre": (244, 307), "Mar": (318, 220),
    "Gas": (253, 233), "Pic": (297, 333), "Bur": (325, 282),
    "Por": (105, 197), "Spa": (163, 150),
    "Spa/nc": (175, 224), "Spa/sc": (163, 104),
    
    # Low Countries & Germany
    "Bel": (337, 360), "Hol": (357, 379), "Kie": (395, 368), "Ber": (449, 385),
    "Mun": (402, 302), "Ruh": (366, 332),
    
    # Scandinavia
    "Den": (415, 436), "Swe": (482, 547), "Nwy": (426, 559),
    "Fin": (589, 575), "StP": (722, 579),
    "StP/nc": (718, 691), "StP/sc": (626, 519),
    
    # Central Europe
    "Tyr": (423, 258), "Boh": (457, 310), "Sil": (476, 348),
    "Pru": (505, 390), "War": (562, 353), "Gal": (573, 305),
    "Vie": (497, 281), "Bud": (549, 250),
    
    # Italy
    "Ven": (406, 218), "Pie": (365, 224), "Rom": (418, 161),
    "Tus": (390, 190), "Nap": (476, 84), "Apu": (475, 126),
    
    # Balkans
    "Tri": (488, 206), "Alb": (533, 128), "Ser": (549, 166),
    "Gre": (562, 96), "Bul": (615, 161), "Rum": (638, 227),
    
    # Eastern Europe
    "Mos": (702, 417), "Lvn": (591, 430), "Ukr": (649, 321),
    "Sev": (776, 298), "Arm": (878, 134), "Syr": (860, 47),
    
    # Turkey
    "Con": (675, 121), "Ank": (764, 143), "Smy": (727, 71),
    
    # North Africa
    "Tun": (359, 21), "Naf": (184, 32),
    
    # Sea zones
    "IRI": (193, 393), "ENG": (238, 354), "MAO": (67, 298),
    "NAO": (112, 578), "NTH": (334, 468), "NWG": (364, 654),
    "HEL": (383, 419), "BAL": (498, 428), "SKA": (427, 491),
    "BOT": (538, 513), "BAR": (667, 742),
    "WES": (269, 93), "LYO": (306, 167), "TYS": (404, 113),
    "ADR": (473, 165), "ION": (500, 37), "AEG": (620, 56),
    "BLA": (735, 199), "EAS": (703, 22),
}


class MapVisualizer:
    """Visualizes Diplomacy game state on a simplified map."""
    
    def __init__(self, game_state: GameState, figsize=(16, 10), base_image_path=None):
        self.state = game_state
        self.base_image_path = base_image_path
        self.base_image = None
        
        # Try to load base image if provided
        if base_image_path and os.path.exists(base_image_path):
            try:
                self.base_image = imread(base_image_path)
                # Adjust figsize based on image aspect ratio
                if self.base_image is not None:
                    img_height, img_width = self.base_image.shape[:2]
                    aspect_ratio = img_width / img_height
                    # Keep height at 10, adjust width
                    self.figsize = (10 * aspect_ratio, 10)
                else:
                    self.figsize = figsize
            except Exception as e:
                print(f"Warning: Could not load base image: {e}")
                self.base_image = None
                self.figsize = figsize
        else:
            self.figsize = figsize
        
        self.fig = None
        self.ax = None
    
    def draw_map(self, show_labels=False, show_legend=False, orders=None, skip_orders=False):
        """Draw the complete map with current game state."""
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        
        # Set coordinate system based on whether we have a base image
        if self.base_image is not None:
            # Use absolute pixel coordinates matching the image dimensions
            img_height, img_width = self.base_image.shape[:2]
            self.ax.set_xlim(0, img_width)
            self.ax.set_ylim(0, img_height)
            # Don't force equal aspect - let image determine it
            self.ax.set_aspect('auto')
        else:
            # For programmatic map, use the old coordinate system
            self.ax.set_xlim(0, 100)
            self.ax.set_ylim(40, 95)
            self.ax.set_aspect('equal')
        
        self.ax.axis('off')
        
        # Draw base image if available, otherwise draw programmatic map
        if self.base_image is not None:
            self._draw_base_image()
        else:
            # Draw background (sea)
            self.ax.set_facecolor('#B0C4DE')  # Light steel blue for sea
            # Draw land masses (simplified)
            self._draw_land_masses()
        
        # Draw territory control colors
        self._draw_territory_control()
        
        # Draw supply centers
        self._draw_supply_centers()
        
        # Draw units
        self._draw_units()
        
        # Draw orders if provided (skip if we'll draw them later with results)
        if orders and not skip_orders:
            self._draw_orders(orders)
        
        # Draw province labels (disabled by default when using base image)
        if show_labels:
            self._draw_province_labels()
        
        # Draw title
        self._draw_title()
        
        # Draw legend (disabled by default when using base image)
        if show_legend:
            self._draw_legend()
        
        plt.tight_layout()
    
    def _draw_base_image(self):
        """Draw the base map image."""
        # Display the image using absolute pixel coordinates
        img_height, img_width = self.base_image.shape[:2]
        self.ax.imshow(self.base_image, extent=[0, img_width, 0, img_height], 
                      aspect='auto', zorder=0, alpha=0.9)
    
    def _draw_land_masses(self):
        """Draw simplified land masses."""
        # Draw large land regions as polygons
        
        # British Isles
        britain = Polygon([
            (8, 65), (8, 82), (16, 82), (18, 78), (18, 65)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(britain)
        
        # Western Europe
        west_europe = Polygon([
            (18, 55), (18, 72), (32, 76), (38, 72), (38, 60), (28, 55)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(west_europe)
        
        # Central/Eastern Europe
        central_europe = Polygon([
            (32, 60), (32, 80), (48, 82), (58, 78), (58, 62), (48, 56), (38, 56)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(central_europe)
        
        # Scandinavia
        scandinavia = Polygon([
            (28, 82), (28, 92), (46, 92), (46, 82)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(scandinavia)
        
        # Mediterranean
        med_north = Polygon([
            (28, 48), (28, 62), (42, 62), (50, 58), (50, 48)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(med_north)
        
        # Turkey/Middle East
        turkey = Polygon([
            (50, 52), (50, 62), (64, 62), (64, 52)
        ], facecolor='#F5DEB3', edgecolor='white', linewidth=1, alpha=0.3)
        self.ax.add_patch(turkey)
    
    def _draw_territory_control(self):
        """Draw colored circles showing territory control."""
        # Scale radius based on coordinate system (scaled for 915×767 image)
        radius = 22 if self.base_image is not None else 2.5
        
        for prov_abbr, power in self.state.supply_centers.items():
            if prov_abbr in PROVINCE_POSITIONS:
                x, y = PROVINCE_POSITIONS[prov_abbr]
                color = POWER_COLORS.get(power, '#CCCCCC')
                
                # Draw semi-transparent circle for territory control
                circle = Circle((x, y), radius, color=color, alpha=0.4, zorder=1)
                self.ax.add_patch(circle)
    
    def _draw_supply_centers(self):
        """Draw supply center markers."""
        # Scale size based on coordinate system (scaled for 915×767 image)
        size = 6 if self.base_image is not None else 1.2
        half_size = size / 2
        
        for province in self.state.game_map.get_supply_centers():
            if province.abbreviation in PROVINCE_POSITIONS:
                x, y = PROVINCE_POSITIONS[province.abbreviation]
                
                # Draw small square for supply center
                square = patches.Rectangle(
                    (x - half_size, y - half_size), size, size,
                    facecolor='white', edgecolor='black',
                    linewidth=1, zorder=2
                )
                self.ax.add_patch(square)
    
    def _draw_units(self):
        """Draw unit markers (armies and fleets)."""
        # Scale sizes based on coordinate system (scaled for 915×767 image)
        army_radius = 13 if self.base_image is not None else 1.5
        fleet_radius = 16 if self.base_image is not None else 1.8
        linewidth = 2
        
        for unit in self.state.units.values():
            # Check for coast-specific position first (e.g., "StP/sc")
            position_key = unit.location
            if unit.coast:
                coast_key = f"{unit.location}/{unit.coast.value}"
                if coast_key in PROVINCE_POSITIONS:
                    position_key = coast_key
            
            if position_key in PROVINCE_POSITIONS:
                x, y = PROVINCE_POSITIONS[position_key]
                color = POWER_COLORS.get(unit.power, '#CCCCCC')
                
                if unit.unit_type == UnitType.ARMY:
                    # Draw circle for army
                    circle = Circle((x, y), army_radius, facecolor=color, 
                                  edgecolor='black', linewidth=linewidth, zorder=3)
                    self.ax.add_patch(circle)
                else:  # Fleet
                    # Draw triangle for fleet
                    triangle = RegularPolygon(
                        (x, y), 3, radius=fleet_radius, orientation=math.pi,
                        facecolor=color, edgecolor='black', 
                        linewidth=linewidth, zorder=3)
                    self.ax.add_patch(triangle)
    
    def _draw_orders(self, orders):
        """Draw order arrows and indicators."""
        if not orders:
            return
        
        for order in orders:
            self._draw_single_order(order)
    
    def _draw_single_order(self, order):
        """Draw a single order visualization."""
        from diplomacy_game_engine.core.orders import MoveOrder, SupportOrder, HoldOrder, ConvoyOrder, BuildOrder, DisbandOrder
        
        # BuildOrder doesn't have a unit attribute, handle it separately
        if isinstance(order, BuildOrder):
            build_pos = PROVINCE_POSITIONS.get(order.location)
            if build_pos:
                self._draw_build_indicator(build_pos)
            return
        
        # DisbandOrder - draw red X
        if isinstance(order, DisbandOrder):
            unit_pos = PROVINCE_POSITIONS.get(order.unit.location)
            if unit_pos:
                self._draw_disband_indicator(unit_pos)
            return
        
        # Get unit position, checking for coast-specific position
        position_key = order.unit.location
        if order.unit.coast:
            coast_key = f"{order.unit.location}/{order.unit.coast.value}"
            if coast_key in PROVINCE_POSITIONS:
                position_key = coast_key
        
        unit_pos = PROVINCE_POSITIONS.get(position_key)
        if not unit_pos:
            return
        
        if isinstance(order, HoldOrder):
            self._draw_hold_order(unit_pos)
        elif isinstance(order, MoveOrder):
            # Check for coast-specific destination position
            dest_key = order.destination
            if order.dest_coast:
                coast_dest_key = f"{order.destination}/{order.dest_coast.value}"
                if coast_dest_key in PROVINCE_POSITIONS:
                    dest_key = coast_dest_key
            
            target_pos = PROVINCE_POSITIONS.get(dest_key)
            if target_pos:
                # Check if this move was illegal (resulted in "Held position")
                unit_id = order.unit.get_id()
                is_illegal = False
                if hasattr(self, 'move_results') and unit_id in self.move_results:
                    result = self.move_results[unit_id]
                    # Illegal moves result in "Held position"
                    is_illegal = result == "Held position"
                
                # Draw red arrow for illegal moves, black for legal moves
                color = 'red' if is_illegal else 'black'
                self._draw_arrow(unit_pos, target_pos, solid=True, arrowhead=True, color=color)
        elif isinstance(order, ConvoyOrder):
            # Draw wavy line indicator above the convoying fleet
            self._draw_convoy_indicator(unit_pos)
        elif isinstance(order, SupportOrder):
            supported_pos = PROVINCE_POSITIONS.get(order.supported_unit_location)
            if not supported_pos:
                return
            
            # Check if this support is cut (disrupted by attack) or if unit is dislodged
            # Note: We don't show invalid/misaligned supports in red, only cut/dislodged ones
            unit_id = order.unit.get_id()
            is_cut = hasattr(self, 'cut_supports') and unit_id in self.cut_supports
            
            # Also check if the supporting unit is dislodged
            is_dislodged = False
            if hasattr(self, 'dislodged_units') and self.dislodged_units:
                is_dislodged = any(d.unit.get_id() == unit_id for d in self.dislodged_units)
            
            use_red = is_cut or is_dislodged
                
            if order.destination:
                # Support for move - draw two-segment arrow: supporting unit -> supported unit -> destination
                target_pos = PROVINCE_POSITIONS.get(order.destination)
                if target_pos:
                    self._draw_support_move_order(unit_pos, supported_pos, target_pos, use_red=use_red)
            else:
                # Support for hold - draw single arrow: supporting unit -> supported unit
                self._draw_support_hold_order(unit_pos, supported_pos, use_red=use_red)
    
    def _draw_convoy_indicator(self, unit_pos):
        """Draw a wavy line above a fleet performing a convoy."""
        import numpy as np
        
        x, y = unit_pos
        
        # Scale based on coordinate system
        if self.base_image is not None:
            wave_width = 20  # Total width of wavy line
            wave_height = 4  # Amplitude of waves
            y_offset = 20  # Distance above the fleet
            num_waves = 3  # Number of wave cycles
        else:
            wave_width = 2.5
            wave_height = 0.5
            y_offset = 2.5
            num_waves = 3
        
        # Generate wavy line points
        t = np.linspace(0, num_waves * 2 * np.pi, 50)
        wave_x = x - wave_width/2 + (t / (num_waves * 2 * np.pi)) * wave_width
        wave_y = y + y_offset + wave_height * np.sin(t)
        
        # Draw the wavy line
        self.ax.plot(wave_x, wave_y, 'k-', linewidth=2, zorder=4)
    
    def _draw_build_indicator(self, build_pos):
        """Draw a dotted circle to indicate a build location."""
        x, y = build_pos
        radius = 20 if self.base_image is not None else 2.0
        
        # Draw dotted circle
        build_circle = Circle((x, y), radius, facecolor='none', 
                            edgecolor='black', linewidth=2, linestyle=':', zorder=4)
        self.ax.add_patch(build_circle)
    
    def _draw_hold_order(self, unit_pos):
        """Draw a black circle around unit to indicate hold order."""
        x, y = unit_pos
        radius = 20 if self.base_image is not None else 2.0
        
        hold_circle = Circle((x, y), radius, facecolor='none', 
                           edgecolor='black', linewidth=3, zorder=4)
        self.ax.add_patch(hold_circle)
    
    def _draw_move_order(self, start_pos, end_pos):
        """Draw a solid arrow for move orders."""
        self._draw_arrow(start_pos, end_pos, solid=True)
    
    def _draw_support_move_order(self, supporting_pos, supported_pos, target_pos, use_red=False):
        """Draw a two-segment dotted arrow for support move orders."""
        color = 'red' if use_red else 'black'
        # First segment: supporting unit -> supported unit (dotted, no arrowhead)
        self._draw_arrow(supporting_pos, supported_pos, solid=False, arrowhead=False, color=color)
        # Second segment: supported unit -> target (dotted, with arrowhead)
        self._draw_arrow(supported_pos, target_pos, solid=False, arrowhead=True, color=color)
    
    def _draw_support_hold_order(self, supporting_pos, supported_pos, use_red=False):
        """Draw a single dotted line for support hold orders (no arrowhead)."""
        color = 'red' if use_red else 'black'
        self._draw_arrow(supporting_pos, supported_pos, solid=False, arrowhead=False, color=color)
    
    def _draw_support_order(self, start_pos, end_pos):
        """Draw a dotted arrow for support orders."""
        self._draw_arrow(start_pos, end_pos, solid=False)
    
    def _draw_arrow(self, start_pos, end_pos, solid=True, arrowhead=True, color='black'):
        """Draw an arrow between two positions."""
        x1, y1 = start_pos
        x2, y2 = end_pos
        
        # Calculate arrow properties
        dx = x2 - x1
        dy = y2 - y1
        
        # Shorten arrow to not overlap with units
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return
        
        # Smart conditional offsetting
        start_offset_pixels = 17 if self.base_image is not None else 2.0
        
        # Check if target province has a unit
        target_province = None
        for province, pos in PROVINCE_POSITIONS.items():
            if pos == end_pos:
                target_province = province
                break
        
        target_has_unit = False
        if target_province:
            target_has_unit = any(unit.location == target_province for unit in self.state.units.values())
        
        # Set end offset based on whether target has a unit
        end_offset_pixels = start_offset_pixels if target_has_unit else 0
        
        # Adjust start and end points to not overlap units
        start_offset = start_offset_pixels / length
        end_offset = end_offset_pixels / length if arrowhead else 0
        
        x1_adj = x1 + dx * start_offset
        y1_adj = y1 + dy * start_offset
        x2_adj = x2 - dx * end_offset
        y2_adj = y2 - dy * end_offset
        
        # Draw arrow with or without arrowhead
        linewidth = 3 if self.base_image is not None else 1.5
        
        if arrowhead:
            head_width = 7.5 if self.base_image is not None else 0.75
            head_length = 10 if self.base_image is not None else 1.0
            
            arrow_props = dict(
                arrowstyle=f'-|>,head_width={head_width},head_length={head_length}',
                lw=linewidth,
                color=color,
                zorder=5
            )
        else:
            # Just a line without arrowhead
            arrow_props = dict(
                arrowstyle='-',
                lw=linewidth,
                color=color,
                zorder=5
            )
        
        if not solid:
            arrow_props['linestyle'] = '--'
        
        from matplotlib.patches import FancyArrowPatch
        arrow = FancyArrowPatch((x1_adj, y1_adj), (x2_adj, y2_adj), **arrow_props)
        self.ax.add_patch(arrow)
    
    def _draw_province_labels(self):
        """Draw province abbreviation labels."""
        for abbr, (x, y) in PROVINCE_POSITIONS.items():
            self.ax.text(x, y - 3.5, abbr, fontsize=7, ha='center',
                        va='top', fontweight='bold', color='#333333')
    
    def _draw_title(self):
        """Draw game phase title."""
        from diplomacy_game_engine.core.game_state import Season
        
        season_name = self.state.season.value
        year = self.state.year
        
        title = f"{season_name.upper()} {year}"
        # Position title at top center of image (in pixel coordinates)
        if self.base_image is not None:
            img_height, img_width = self.base_image.shape[:2]
            self.ax.text(img_width/2, img_height*0.93, title, fontsize=16, ha='center',
                        fontweight='bold', bbox=dict(boxstyle='round',
                        facecolor='white', alpha=0.8))
        else:
            self.ax.text(50, 93, title, fontsize=16, ha='center',
                        fontweight='bold', bbox=dict(boxstyle='round',
                        facecolor='white', alpha=0.8))
    
    def _draw_legend(self):
        """Draw legend showing power colors and unit counts."""
        legend_y = 42
        legend_x_start = 5
        
        for i, power in enumerate(Power):
            x = legend_x_start + (i * 13)
            color = POWER_COLORS[power]
            
            # Draw colored box
            box = patches.Rectangle(
                (x, legend_y), 2, 1.5,
                facecolor=color, edgecolor='black', linewidth=1
            )
            self.ax.add_patch(box)
            
            # Get unit and SC counts
            unit_count = self.state.get_unit_count(power)
            sc_count = self.state.get_sc_count(power)
            
            # Draw text
            self.ax.text(x + 1, legend_y + 2.5, power.value.split('-')[0],
                        fontsize=8, ha='center', fontweight='bold')
            self.ax.text(x + 1, legend_y - 0.8, f"{sc_count} SC",
                        fontsize=7, ha='center')
            
            # Draw unit symbols
            if unit_count > 0:
                # Army symbol
                army_count = len([u for u in self.state.get_units_by_power(power) 
                                if u.unit_type == UnitType.ARMY])
                if army_count > 0:
                    circle = Circle((x + 0.5, legend_y + 0.75), 0.3,
                                  facecolor=color, edgecolor='black', linewidth=0.5)
                    self.ax.add_patch(circle)
                    self.ax.text(x + 0.9, legend_y + 0.75, str(army_count),
                               fontsize=6, ha='left', va='center')
                
                # Fleet symbol
                fleet_count = unit_count - army_count
                if fleet_count > 0:
                    triangle = RegularPolygon(
                        (x + 1.5, legend_y + 0.75), 3, radius=0.35,
                        orientation=math.pi, facecolor=color,
                        edgecolor='black', linewidth=0.5
                    )
                    self.ax.add_patch(triangle)
                    self.ax.text(x + 1.9, legend_y + 0.75, str(fleet_count),
                               fontsize=6, ha='left', va='center')
    
    def _draw_failed_moves(self, move_results, original_state):
        """Draw red arrows for failed/bounced moves."""
        from diplomacy_game_engine.core.orders import MoveOrder
        
        for unit_id, result_str in move_results.items():
            if 'Bounced' in result_str:
                # Find the unit in original state
                unit = original_state.units.get(unit_id)
                if not unit:
                    continue
                
                # Get unit position, checking for coast
                start_key = unit.location
                if unit.coast:
                    coast_key = f"{unit.location}/{unit.coast.value}"
                    if coast_key in PROVINCE_POSITIONS:
                        start_key = coast_key
                
                # Extract destination from result string
                # Format: "Bounced from {destination}"
                dest = result_str.split('from ')[-1]
                
                start_pos = PROVINCE_POSITIONS.get(start_key)
                end_pos = PROVINCE_POSITIONS.get(dest)
                
                if start_pos and end_pos:
                    self._draw_arrow(start_pos, end_pos, solid=True, arrowhead=True, color='red')
    
    def _draw_dislodged_indicators(self, dislodged_units):
        """Draw red circles around dislodged units."""
        radius = 25 if self.base_image is not None else 2.5
        
        for dislodged in dislodged_units:
            unit_pos = PROVINCE_POSITIONS.get(dislodged.dislodged_from)
            if unit_pos:
                x, y = unit_pos
                # Draw thick red circle around the dislodged unit
                dislodged_circle = Circle((x, y), radius, facecolor='none',
                                        edgecolor='red', linewidth=4, zorder=6)
                self.ax.add_patch(dislodged_circle)
    
    def _draw_disband_indicators(self, disband_unit_ids):
        """Draw red X marks over units being disbanded."""
        size = 20 if self.base_image is not None else 2.0
        
        for unit_id in disband_unit_ids:
            # Try direct ID lookup first
            unit = self.state.units.get(unit_id)
            
            # If not found, try to find by matching location and power from the ID
            if not unit:
                # Parse the unit ID to extract location (format: Power_Type_Location_Counter)
                parts = unit_id.split('_')
                if len(parts) >= 3:
                    location = parts[2]
                    # Find unit at this location in the state
                    for state_unit in self.state.units.values():
                        if state_unit.location == location:
                            unit = state_unit
                            break
            
            if not unit:
                continue
            
            unit_pos = PROVINCE_POSITIONS.get(unit.location)
            if unit_pos:
                x, y = unit_pos
                # Draw red X
                self.ax.plot([x - size, x + size], [y - size, y + size], 
                           'r-', linewidth=4, zorder=6)
                self.ax.plot([x - size, x + size], [y + size, y - size], 
                           'r-', linewidth=4, zorder=6)
    
    def _draw_retreat_arrows(self, retreat_orders):
        """Draw orange arrows for retreat orders."""
        from diplomacy_game_engine.core.orders import RetreatOrder
        
        # Handle both dict and list formats
        orders_to_draw = retreat_orders.values() if isinstance(retreat_orders, dict) else retreat_orders
        
        for order in orders_to_draw:
            if isinstance(order, RetreatOrder):
                unit = order.unit
                start_pos = PROVINCE_POSITIONS.get(unit.location)
                end_pos = PROVINCE_POSITIONS.get(order.destination)
                
                if start_pos and end_pos:
                    # Draw orange arrow for retreat
                    self._draw_arrow(start_pos, end_pos, solid=True, arrowhead=True, color='orange')
    
    def draw_map_with_results(self, show_labels=False, show_legend=False, orders=None,
                             move_results=None, dislodged_units=None, original_state=None,
                             invalid_supports=None, cut_supports=None, retreat_orders=None):
        """Draw map with visual indicators for failed moves, dislodged units, invalid/cut supports, and retreat orders."""
        # Store invalid/cut supports, dislodged units, and move results for use in drawing
        self.invalid_supports = invalid_supports or set()
        self.cut_supports = cut_supports or set()
        self.dislodged_units = dislodged_units or []
        self.move_results = move_results or {}
        
        # Draw the base map first (skip orders, we'll draw them after setting cut_supports)
        self.draw_map(show_labels, show_legend, orders=None, skip_orders=True)
        
        # Now draw orders with cut_supports already set
        if orders:
            self._draw_orders(orders)
        
        # Add failed move indicators (red arrows)
        if move_results and original_state:
            self._draw_failed_moves(move_results, original_state)
        
        # Add dislodged unit indicators (red circles)
        if dislodged_units:
            self._draw_dislodged_indicators(dislodged_units)
        
        # Add retreat arrows (orange)
        if retreat_orders:
            self._draw_retreat_arrows(retreat_orders)
        
        # Draw hold circles for units that held (explicit or implicit)
        if original_state and orders is not None:
            self._draw_implicit_holds(original_state, orders, move_results or {})
    
    def _draw_implicit_holds(self, original_state, orders, move_results):
        """Draw hold circles for units that held (no order, failed order, or explicit hold)."""
        from diplomacy_game_engine.core.orders import HoldOrder
        
        for unit in original_state.units.values():
            unit_id = unit.get_id()
            
            # Check if unit has an order
            unit_order = None
            for order in orders:
                if hasattr(order, 'unit') and order.unit.get_id() == unit_id:
                    unit_order = order
                    break
            
            # Determine if unit held
            held = False
            
            if unit_order is None:
                # No order submitted → implicit hold
                held = True
            elif isinstance(unit_order, HoldOrder):
                # Explicit hold order
                held = True
            elif unit_id in move_results:
                # Check if move failed (bounced or illegal)
                result = move_results[unit_id]
                if 'Bounced' in result or 'Held position' in result:
                    held = True
            
            # Draw hold circle if unit held
            if held:
                # Get unit position
                position_key = unit.location
                if unit.coast:
                    coast_key = f"{unit.location}/{unit.coast.value}"
                    if coast_key in PROVINCE_POSITIONS:
                        position_key = coast_key
                
                unit_pos = PROVINCE_POSITIONS.get(position_key)
                if unit_pos:
                    self._draw_hold_order(unit_pos)
    
    def show(self):
        """Display the map in a window."""
        if self.fig is None:
            self.draw_map()
        plt.show()
    
    def save(self, filename: str, dpi=150):
        """Save the map to a file."""
        if self.fig is None:
            self.draw_map()
        self.fig.savefig(filename, dpi=dpi, bbox_inches='tight',
                        facecolor='white')
        print(f"Map saved to {filename}")


def visualize_game(game_state: GameState, filename: Optional[str] = None, 
                   base_image_path: Optional[str] = None, orders=None, disband_unit_ids=None):
    """
    Convenience function to visualize a game state.
    
    Args:
        game_state: The game state to visualize
        filename: Optional filename to save to. If None, displays in window.
        base_image_path: Optional path to base map image. If None, uses programmatic map.
        orders: Optional list of orders to visualize on the map.
        disband_unit_ids: Optional list of unit IDs being disbanded (for winter phase).
    """
    viz = MapVisualizer(game_state, base_image_path=base_image_path)
    
    # If we have disband indicators, we need to draw them before tight_layout
    # So we manually build the map instead of calling draw_map()
    if disband_unit_ids:
        # Initialize figure and axes
        viz.fig, viz.ax = plt.subplots(figsize=viz.figsize)
        
        # Set coordinate system
        if viz.base_image is not None:
            img_height, img_width = viz.base_image.shape[:2]
            viz.ax.set_xlim(0, img_width)
            viz.ax.set_ylim(0, img_height)
            viz.ax.set_aspect('auto')
        else:
            viz.ax.set_xlim(0, 100)
            viz.ax.set_ylim(40, 95)
            viz.ax.set_aspect('equal')
        
        viz.ax.axis('off')
        
        # Draw base layers
        if viz.base_image is not None:
            viz._draw_base_image()
        else:
            viz.ax.set_facecolor('#B0C4DE')
            viz._draw_land_masses()
        
        viz._draw_territory_control()
        viz._draw_supply_centers()
        viz._draw_units()
        
        # Draw orders if provided
        if orders:
            viz._draw_orders(orders)
        
        # Draw disband indicators BEFORE tight_layout
        viz._draw_disband_indicators(disband_unit_ids)
        
        # Draw title
        viz._draw_title()
        
        # Now call tight_layout
        plt.tight_layout()
    else:
        # No disband indicators, use normal draw_map
        viz.draw_map(orders=orders)
    
    if filename:
        viz.save(filename)
    else:
        viz.show()
