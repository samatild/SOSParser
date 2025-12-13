"""
Supportconfig Disk Usage Analyzer

Analyzes disk usage information from filesystem data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class DiskUsageAnalyzer:
    """Analyzer for disk usage information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract disk usage information."""
        disk_usage = {}

        # Get df output
        df_output = self.parser.get_command_output('fs-diskio.txt', '/bin/df')
        if df_output:
            disk_usage['df'] = df_output

        # Get df -h or df -Th for human-readable
        df_h = self.parser.get_command_output('fs-diskio.txt', '/bin/df -h')
        if df_h:
            disk_usage['df_human'] = df_h
        df_th = self.parser.get_command_output('fs-diskio.txt', '/bin/df -Th')
        if df_th:
            disk_usage['df'] = df_th  # Template expects df; prefer typed view

        # Get df -i for inodes
        df_i = self.parser.get_command_output('fs-diskio.txt', '/bin/df -i')
        if df_i:
            disk_usage['df_inodes'] = df_i

        return disk_usage
