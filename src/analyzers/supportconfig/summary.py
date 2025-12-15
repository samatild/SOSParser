#!/usr/bin/env python3
"""Supportconfig Summary Data Analyzer"""

from pathlib import Path
from typing import Dict, Any
from .system_info import SupportconfigSystemInfo


class SupportconfigSummaryAnalyzer:
    """Analyzer for supportconfig summary data extraction."""

    def __init__(self, root_path: Path):
        """
        Initialize summary analyzer.

        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path
        self.system_info = SupportconfigSystemInfo(root_path)

    def get_basic_summary(self) -> Dict[str, Any]:
        """Get basic system information for summary display."""
        return {
            'hostname': self.system_info.get_hostname(),
            'os_info': self.system_info.get_os_info(),
            'kernel_info': self.system_info.get_kernel_info(),
            'uptime': self.system_info.get_uptime(),
            'cpu_info': self.system_info.get_cpu_info(),
            'memory_info': self.system_info.get_memory_info(),
            'disk_info': self.system_info.get_disk_info(),
            'system_load': self.system_info.get_system_load(),
            'dmi_info': self.system_info.get_dmi_info(),
        }

    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Get enhanced summary data specific to supportconfig."""
        return {
            'cpu_vulnerabilities': self.system_info.get_cpu_vulnerabilities(),
            'kernel_tainted': self.system_info.get_kernel_tainted_status(),
            'supportconfig_info': self.system_info.get_supportconfig_info(),
            'top_processes': self.system_info.get_top_processes(),
            'system_resources': self.system_info.get_system_resources(),
        }

    def get_full_summary(self) -> Dict[str, Any]:
        """Get complete summary data combining basic and enhanced information."""
        summary = self.get_basic_summary()
        summary.update(self.get_enhanced_summary())
        return summary
