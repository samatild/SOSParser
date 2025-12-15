#!/usr/bin/env python3
"""SOSReport Summary Data Analyzer"""

from pathlib import Path
from typing import Dict, Any
from .system_info import (
    get_hostname,
    get_os_release,
    get_kernel_info,
    get_uptime,
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_system_load,
    get_dmidecode_info,
    get_system_resources,
    get_top_processes
)


class SOSReportSummaryAnalyzer:
    """Analyzer for SOSReport summary data extraction."""

    def __init__(self, root_path: Path):
        """
        Initialize summary analyzer.

        Args:
            root_path: Path to extracted SOSReport directory
        """
        self.root_path = root_path

    def get_basic_summary(self) -> Dict[str, Any]:
        """Get basic system information for summary display."""
        return {
            'hostname': get_hostname(self.root_path),
            'os_info': get_os_release(self.root_path),
            'kernel_info': get_kernel_info(self.root_path),
            'uptime': get_uptime(self.root_path),
            'cpu_info': get_cpu_info(self.root_path),
            'memory_info': get_memory_info(self.root_path),
            'disk_info': get_disk_info(self.root_path),
            'system_load': get_system_load(self.root_path),
            'dmi_info': get_dmidecode_info(self.root_path),
        }

    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Get enhanced summary data specific to SOSReport."""
        return {
            'top_processes': get_top_processes(self.root_path),
            'system_resources': get_system_resources(self.root_path),
        }

    def get_full_summary(self) -> Dict[str, Any]:
        """Get complete summary data combining basic and enhanced information."""
        summary = self.get_basic_summary()
        summary.update(self.get_enhanced_summary())
        return summary
