#!/usr/bin/env python3
"""
Updates analyzer for SUSE supportconfig.

Parses updates.txt to extract zypper-related update and repository information.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from .parser import SupportconfigParser
from utils.logger import Logger


class SupportconfigUpdates:
    """Analyze updates information from supportconfig."""

    def __init__(self, parser: SupportconfigParser):
        """
        Initialize updates analyzer.
        
        Args:
            parser: SupportconfigParser instance
        """
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze updates information from updates.txt.
        
        Returns:
            Dictionary with updates/zypper information
        """
        Logger.debug("Analyzing supportconfig updates")
        
        content = self.parser.read_file('updates.txt')
        if not content:
            return {'note': 'No updates.txt file found'}
        
        sections = self.parser.extract_sections(content)
        
        data = {
            'package_manager': 'zypper',
            'zypper': self._parse_zypper_data(sections),
        }
        
        return data

    def _parse_zypper_data(self, sections: list) -> Dict[str, Any]:
        """Parse zypper-related sections from updates.txt."""
        zypper_data = {}
        
        for section in sections:
            if section.get('type') != 'Command':
                continue
            
            content = section.get('content', '').strip()
            
            # Skip empty content
            if not content:
                continue
            
            # Extract command from first line of content (starts with #)
            lines = content.split('\n')
            if not lines or not lines[0].startswith('#'):
                continue
            
            command_line = lines[0].strip('# ').strip()
            # The actual output is everything after the command line
            output = '\n'.join(lines[1:]).strip()
            
            # Package locks
            if 'zypper locks' in command_line:
                zypper_data['locks'] = output
            
            # Services (SUSE modules)
            elif 'zypper' in command_line and 'services' in command_line:
                zypper_data['services'] = output
            
            # Detailed repository list
            elif 'zypper' in command_line and 'repos' in command_line:
                zypper_data['repos'] = output
            
            # Patch check summary
            elif 'zypper' in command_line and 'patch-check' in command_line:
                zypper_data['patch_check'] = output
                zypper_data['patch_summary'] = self._parse_patch_summary(output)
            
            # All patches (but not list-patches)
            elif 'zypper' in command_line and 'patches' in command_line and 'list-patches' not in command_line:
                zypper_data['patches'] = output
            
            # List of needed patches
            elif 'zypper' in command_line and 'list-patches' in command_line:
                zypper_data['list_patches'] = output
            
            # Available updates
            elif 'zypper' in command_line and 'list-updates' in command_line:
                zypper_data['list_updates'] = output
                zypper_data['update_count'] = self._count_updates(output)
            
            # Installed products (but not xmlout)
            elif 'zypper' in command_line and 'products' in command_line and 'xmlout' not in command_line:
                zypper_data['products'] = output
            
            # Orphaned packages
            elif 'zypper' in command_line and 'packages --orphaned' in command_line:
                zypper_data['orphaned'] = output
            
            # SUSEConnect status
            elif 'SUSEConnect --status' in command_line:
                zypper_data['suseconnect_status'] = output
            
            # Product lifecycle
            elif 'zypper lifecycle' in command_line:
                zypper_data['lifecycle'] = output
            
            # Installed patterns
            elif 'zypper' in command_line and 'patterns' in command_line:
                zypper_data['patterns'] = output
            
            # Products directory listing
            elif '/etc/products.d/' in command_line:
                zypper_data['products_dir'] = output
        
        return zypper_data

    def _parse_patch_summary(self, content: str) -> Dict[str, Any]:
        """Parse patch check summary to extract counts."""
        summary = {
            'total': 0,
            'security': 0,
            'recommended': 0,
            'optional': 0,
        }
        
        if not content:
            return summary
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Look for "Found X applicable patches:"
            if 'applicable patches' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            summary['total'] = int(part)
                            break
                except (ValueError, IndexError):
                    pass
            
            # Look for "X patches needed (Y security patches)"
            if 'patches needed' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if 'security' in line.lower() and i > 0:
                                # Check if this is the security count
                                next_word_idx = i + 1
                                if next_word_idx < len(parts) and 'security' in parts[next_word_idx].lower():
                                    summary['security'] = int(part)
                            elif summary['total'] == 0:
                                summary['total'] = int(part)
                except (ValueError, IndexError):
                    pass
            
            # Parse table rows for categories
            if line.startswith('security') and '|' in line:
                try:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        summary['security'] = int(parts[2])
                except (ValueError, IndexError):
                    pass
            elif line.startswith('recommended') and '|' in line:
                try:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        summary['recommended'] = int(parts[2])
                except (ValueError, IndexError):
                    pass
            elif line.startswith('optional') and '|' in line:
                try:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        summary['optional'] = int(parts[2])
                except (ValueError, IndexError):
                    pass
        
        return summary

    def _count_updates(self, content: str) -> int:
        """Count number of available updates from list-updates output."""
        if not content:
            return 0
        
        count = 0
        in_table = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip header lines
            if line.startswith('S  |') or line.startswith('---+'):
                in_table = True
                continue
            
            # Count update lines (start with 'v  |')
            if in_table and line.startswith('v  |'):
                count += 1
        
        return count
