#!/usr/bin/env python3
"""
LVM Visualization Generator

Generates SVG diagrams showing LVM structure:
Physical Volumes (PV) -> Volume Groups (VG) -> Logical Volumes (LV)

Works with both sosreport and supportconfig data.
"""

import re
from typing import Dict, List, Any, Tuple, Optional


class LvmVisualizer:
    """Generate SVG visualizations of LVM configuration."""

    # Color scheme (matching dark theme)
    COLORS = {
        'pv': '#E06C75',      # Soft red for Physical Volumes
        'vg': '#98C379',      # Soft green for Volume Groups
        'lv': '#61AFEF',      # Soft blue for Logical Volumes
        'text': '#ffffff',    # White text
        'line': '#6b7280',    # Gray lines
        'bg': 'transparent',  # Transparent background
    }

    # Layout constants
    BOX_WIDTH = 160
    BOX_HEIGHT = 60
    BOX_PADDING = 10
    VERTICAL_GAP = 30
    HORIZONTAL_GAP = 15
    MAX_ITEMS_PER_ROW = 4  # Maximum items per row to prevent horizontal overflow

    def __init__(self):
        """Initialize the visualizer."""
        pass

    def parse_pvs(self, pvs_output: str) -> List[Dict[str, str]]:
        """
        Parse pvs command output.
        
        Returns list of dicts with: pv_name, vg_name, size, free
        """
        pvs = []
        if not pvs_output:
            return pvs

        lines = pvs_output.strip().split('\n')
        for line in lines:
            # Skip headers and warning lines
            if not line.strip() or line.strip().startswith('PV') or 'WARNING' in line or 'Reloading' in line:
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                pv_info = {
                    'name': parts[0],
                    'vg': parts[1] if len(parts) > 1 and not parts[1].startswith('---') else '',
                    'size': parts[4] if len(parts) > 4 else '',
                    'free': parts[5] if len(parts) > 5 else '',
                }
                # Only include PVs that are part of a VG
                if pv_info['vg'] and pv_info['vg'] != '---':
                    pvs.append(pv_info)
        
        return pvs

    def parse_vgs(self, vgs_output: str) -> List[Dict[str, str]]:
        """
        Parse vgs command output.
        
        Returns list of dicts with: vg_name, size, free
        
        Expected format:
        VG     Attr   Ext   #PV #LV #SN VSize    VFree   VG UUID ...
        vg00   wz--n- 4.00m   1   9   0  <34.50g 452.00m RrQfpQ...
        Index:   0      1      2    3   4   5      6       7
        """
        vgs = []
        if not vgs_output:
            return vgs

        lines = vgs_output.strip().split('\n')
        for line in lines:
            # Skip headers and warning lines
            if not line.strip() or line.strip().startswith('VG') or 'WARNING' in line or 'Reloading' in line:
                continue
            
            parts = line.split()
            if len(parts) >= 1:
                vg_info = {
                    'name': parts[0],
                    'size': parts[6] if len(parts) > 6 else '',   # VSize is at index 6
                    'free': parts[7] if len(parts) > 7 else '',   # VFree is at index 7
                }
                vgs.append(vg_info)
        
        return vgs

    def parse_lvs(self, lvs_output: str) -> List[Dict[str, str]]:
        """
        Parse lvs command output.
        
        Returns list of dicts with: lv_name, vg_name, size, attr
        """
        lvs = []
        if not lvs_output:
            return lvs

        lines = lvs_output.strip().split('\n')
        seen_lvs = set()  # Track unique LVs (some may appear multiple times for multi-segment)
        
        for line in lines:
            # Skip headers and warning lines
            if not line.strip() or line.strip().startswith('LV') or 'WARNING' in line or 'Reloading' in line:
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                lv_name = parts[0]
                vg_name = parts[1]
                lv_key = f"{vg_name}/{lv_name}"
                
                # Skip duplicates (multi-segment LVs appear multiple times)
                if lv_key in seen_lvs:
                    continue
                seen_lvs.add(lv_key)
                
                lv_info = {
                    'name': lv_name,
                    'vg': vg_name,
                    'attr': parts[2] if len(parts) > 2 else '',
                    'size': parts[3] if len(parts) > 3 else '',
                }
                lvs.append(lv_info)
        
        return lvs

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        if not text:
            return ''
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def _create_box(self, x: int, y: int, width: int, height: int, 
                    color: str, label: str, sublabel: str = '') -> str:
        """Create an SVG rounded rectangle with text."""
        # Truncate long labels
        display_label = label[:20] + '...' if len(label) > 20 else label
        
        svg = f'''
        <g>
            <rect x="{x}" y="{y}" width="{width}" height="{height}" 
                  rx="6" ry="6" fill="{color}" stroke="{self.COLORS['line']}" stroke-width="1"/>
            <text x="{x + width//2}" y="{y + 25}" 
                  text-anchor="middle" fill="{self.COLORS['text']}" 
                  font-family="monospace" font-size="11" font-weight="bold">
                {self._escape_xml(display_label)}
            </text>'''
        
        if sublabel:
            svg += f'''
            <text x="{x + width//2}" y="{y + 45}" 
                  text-anchor="middle" fill="{self.COLORS['text']}" 
                  font-family="monospace" font-size="10" opacity="0.8">
                {self._escape_xml(sublabel)}
            </text>'''
        
        svg += '\n        </g>'
        return svg

    def _create_arrow(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """Create an SVG line (arrow without head for cleaner look)."""
        return f'''
        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" 
              stroke="{self.COLORS['line']}" stroke-width="2" stroke-dasharray="4,2"/>'''

    def generate_vg_diagram(self, vg_name: str, vg_size: str, vg_free: str,
                           pvs: List[Dict[str, str]], 
                           lvs: List[Dict[str, str]]) -> str:
        """Generate SVG diagram for a single Volume Group."""
        
        # Calculate rows needed for PVs and LVs
        num_pvs = max(1, len(pvs))
        num_lvs = max(1, len(lvs))
        
        pv_rows = (num_pvs + self.MAX_ITEMS_PER_ROW - 1) // self.MAX_ITEMS_PER_ROW
        lv_rows = (num_lvs + self.MAX_ITEMS_PER_ROW - 1) // self.MAX_ITEMS_PER_ROW
        
        # Items per row (capped)
        pvs_per_row = min(num_pvs, self.MAX_ITEMS_PER_ROW)
        lvs_per_row = min(num_lvs, self.MAX_ITEMS_PER_ROW)
        
        # Calculate width based on max items in any row
        max_items_in_row = max(pvs_per_row, lvs_per_row, 1)
        width = max(400, max_items_in_row * (self.BOX_WIDTH + self.HORIZONTAL_GAP) + self.HORIZONTAL_GAP + 40)
        
        # Calculate height: PV rows + VG row + LV rows + gaps + padding
        total_rows = pv_rows + 1 + lv_rows  # PV rows + VG + LV rows
        height = total_rows * self.BOX_HEIGHT + (total_rows + 1) * self.VERTICAL_GAP + 20
        
        # Collect lines and boxes separately so we can draw lines first (behind boxes)
        line_parts = []
        box_parts = []
        
        current_y = 20
        
        # Physical Volumes (multiple rows if needed)
        pv_positions = []
        for row in range(pv_rows):
            start_idx = row * self.MAX_ITEMS_PER_ROW
            end_idx = min(start_idx + self.MAX_ITEMS_PER_ROW, num_pvs)
            row_pvs = pvs[start_idx:end_idx]
            
            row_width = len(row_pvs) * self.BOX_WIDTH + (len(row_pvs) - 1) * self.HORIZONTAL_GAP
            row_start_x = (width - row_width) // 2
            
            for i, pv in enumerate(row_pvs):
                x = row_start_x + i * (self.BOX_WIDTH + self.HORIZONTAL_GAP)
                sublabel = f"Size: {pv.get('size', 'N/A')}"
                box_parts.append(self._create_box(x, current_y, self.BOX_WIDTH, self.BOX_HEIGHT,
                                                  self.COLORS['pv'], f"PV: {pv['name']}", sublabel))
                pv_positions.append((x + self.BOX_WIDTH // 2, current_y + self.BOX_HEIGHT))
            
            current_y += self.BOX_HEIGHT + self.VERTICAL_GAP
        
        # Volume Group (centered, single row)
        vg_y = current_y
        vg_x = (width - self.BOX_WIDTH) // 2
        sublabel = f"Size: {vg_size} | Free: {vg_free}"
        box_parts.append(self._create_box(vg_x, vg_y, self.BOX_WIDTH, self.BOX_HEIGHT,
                                          self.COLORS['vg'], f"VG: {vg_name}", sublabel))
        vg_center_x = vg_x + self.BOX_WIDTH // 2
        vg_top_y = vg_y
        vg_bottom_y = vg_y + self.BOX_HEIGHT
        
        # Collect lines from PVs to VG
        for px, py in pv_positions:
            line_parts.append(self._create_arrow(px, py, vg_center_x, vg_top_y))
        
        current_y = vg_y + self.BOX_HEIGHT + self.VERTICAL_GAP
        
        # Logical Volumes (multiple rows if needed)
        lv_positions = []
        for row in range(lv_rows):
            start_idx = row * self.MAX_ITEMS_PER_ROW
            end_idx = min(start_idx + self.MAX_ITEMS_PER_ROW, num_lvs)
            row_lvs = lvs[start_idx:end_idx]
            
            row_width = len(row_lvs) * self.BOX_WIDTH + (len(row_lvs) - 1) * self.HORIZONTAL_GAP
            row_start_x = (width - row_width) // 2
            
            for i, lv in enumerate(row_lvs):
                x = row_start_x + i * (self.BOX_WIDTH + self.HORIZONTAL_GAP)
                sublabel = f"Size: {lv.get('size', 'N/A')}"
                box_parts.append(self._create_box(x, current_y, self.BOX_WIDTH, self.BOX_HEIGHT,
                                                  self.COLORS['lv'], f"LV: {lv['name']}", sublabel))
                lv_positions.append((x + self.BOX_WIDTH // 2, current_y))
            
            current_y += self.BOX_HEIGHT + self.VERTICAL_GAP
        
        # Collect lines from VG to LVs
        for lx, ly in lv_positions:
            line_parts.append(self._create_arrow(vg_center_x, vg_bottom_y, lx, ly))
        
        # Build SVG: header, then lines (behind), then boxes (on top)
        svg_parts = [f'''
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" 
     style="display: block; margin-bottom: 20px; background: transparent;">
    <defs>
        <style>
            text {{ font-family: monospace; }}
        </style>
    </defs>
    <!-- Connection lines (drawn first, behind boxes) -->
    <g class="connections">{''.join(line_parts)}
    </g>
    <!-- Boxes (drawn on top of lines) -->
    <g class="boxes">{''.join(box_parts)}
    </g>
</svg>''']
        
        return ''.join(svg_parts)

    def generate_visualization(self, lvm_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate complete LVM visualization from parsed data.
        
        Args:
            lvm_data: Dictionary containing 'pvs', 'vgs', 'lvs' raw output strings
            
        Returns:
            HTML string with embedded SVG diagrams, or None if no LVM data
        """
        pvs_output = lvm_data.get('pvs', '')
        vgs_output = lvm_data.get('vgs', '')
        lvs_output = lvm_data.get('lvs', '')
        
        if not any([pvs_output, vgs_output, lvs_output]):
            return None
        
        # Parse the outputs
        pvs = self.parse_pvs(pvs_output)
        vgs = self.parse_vgs(vgs_output)
        lvs = self.parse_lvs(lvs_output)
        
        if not vgs:
            return None
        
        # Generate diagram for each VG
        html_parts = ['<div class="lvm-visualization">']
        
        for vg in vgs:
            vg_name = vg['name']
            vg_size = vg.get('size', 'N/A')
            vg_free = vg.get('free', 'N/A')
            
            # Get PVs belonging to this VG
            vg_pvs = [pv for pv in pvs if pv.get('vg') == vg_name]
            
            # Get LVs belonging to this VG
            vg_lvs = [lv for lv in lvs if lv.get('vg') == vg_name]
            
            if vg_pvs or vg_lvs:
                svg = self.generate_vg_diagram(vg_name, vg_size, vg_free, vg_pvs, vg_lvs)
                html_parts.append(svg)
        
        html_parts.append('</div>')
        
        result = '\n'.join(html_parts)
        return result if len(html_parts) > 2 else None


def generate_lvm_svg(lvm_data: Dict[str, Any]) -> Optional[str]:
    """
    Convenience function to generate LVM visualization.
    
    Args:
        lvm_data: Dictionary containing 'pvs', 'vgs', 'lvs' raw output strings
        
    Returns:
        HTML string with embedded SVG diagrams, or None if no LVM data
    """
    visualizer = LvmVisualizer()
    return visualizer.generate_visualization(lvm_data)
