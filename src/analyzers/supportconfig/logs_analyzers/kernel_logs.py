"""
Supportconfig Kernel Logs Analyzer

Analyzes kernel log files from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class KernelLogsAnalyzer:
    """Analyzer for kernel logs."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Analyze kernel logs."""
        kernel_logs = {}
        dmesg = self.parser.get_command_output('boot.txt', '/bin/dmesg -T')
        if dmesg:
            kernel_logs['dmesg'] = dmesg

        return kernel_logs
