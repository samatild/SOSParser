#!/usr/bin/env python3
"""Supportconfig Summary Data Analyzer"""

from pathlib import Path
from typing import Dict, Any
from .system_info import SupportconfigSystemInfo
from utils.logger import Logger


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
        Logger.memory("  Summary: basic start")
        
        hostname = self.system_info.get_hostname()
        Logger.memory("  Summary: hostname")
        
        os_info = self.system_info.get_os_info()
        Logger.memory("  Summary: os_info")
        
        kernel_info = self.system_info.get_kernel_info()
        Logger.memory("  Summary: kernel_info")
        
        uptime = self.system_info.get_uptime()
        cpu_info = self.system_info.get_cpu_info()
        memory_info = self.system_info.get_memory_info()
        disk_info = self.system_info.get_disk_info()
        system_load = self.system_info.get_system_load()
        dmi_info = self.system_info.get_dmi_info()
        Logger.memory("  Summary: basic done")
        
        return {
            'hostname': hostname,
            'os_info': os_info,
            'kernel_info': kernel_info,
            'uptime': uptime,
            'cpu_info': cpu_info,
            'memory_info': memory_info,
            'disk_info': disk_info,
            'system_load': system_load,
            'dmi_info': dmi_info,
        }

    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Get enhanced summary data specific to supportconfig."""
        Logger.memory("  Summary: enhanced start")
        
        cpu_vulnerabilities = self.system_info.get_cpu_vulnerabilities()
        Logger.memory("  Summary: cpu_vulnerabilities")
        
        kernel_tainted = self.system_info.get_kernel_tainted_status()
        supportconfig_info = self.system_info.get_supportconfig_info()
        top_processes = self.system_info.get_top_processes()
        system_resources = self.system_info.get_system_resources()
        Logger.memory("  Summary: enhanced done")
        
        return {
            'cpu_vulnerabilities': cpu_vulnerabilities,
            'kernel_tainted': kernel_tainted,
            'supportconfig_info': supportconfig_info,
            'top_processes': top_processes,
            'system_resources': system_resources,
        }

    def get_full_summary(self) -> Dict[str, Any]:
        """Get complete summary data combining basic and enhanced information."""
        summary = self.get_basic_summary()
        summary.update(self.get_enhanced_summary())
        return summary
