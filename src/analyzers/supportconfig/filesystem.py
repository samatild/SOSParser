#!/usr/bin/env python3
"""Filesystem analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any
from .parser import SupportconfigParser
from .filesystem_analyzers.mounts import MountsAnalyzer
from .filesystem_analyzers.disk_usage import DiskUsageAnalyzer
from .filesystem_analyzers.lvm import LvmAnalyzer
from .filesystem_analyzers.filesystem_types import FilesystemTypesAnalyzer
from .filesystem_analyzers.nfs import NfsAnalyzer
from .filesystem_analyzers.samba import SambaAnalyzer
from analyzers.filesystem.lvm_visualizer import generate_lvm_svg
from utils.logger import Logger


class SupportconfigFilesystem:
    """Analyzer for supportconfig filesystem information."""
    
    def __init__(self, root_path: Path):
        """
        Initialize filesystem analyzer.
        
        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete filesystem analysis.
        
        Returns:
            Dictionary with filesystem information
        """
        Logger.memory("  Filesystem: start")
        
        mounts = MountsAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: mounts done")
        
        disk_usage = DiskUsageAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: disk_usage done")
        
        lvm_data = LvmAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: lvm done")
        
        lvm_diagram = generate_lvm_svg(lvm_data)
        Logger.memory("  Filesystem: lvm_diagram done")
        
        filesystems = FilesystemTypesAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: filesystems done")
        
        nfs = NfsAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: nfs done")
        
        samba = SambaAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  Filesystem: samba done")
        
        return {
            'mounts': mounts,
            'disk_usage': disk_usage,
            'lvm': lvm_data,
            'lvm_diagram': lvm_diagram,
            'filesystems': filesystems,
            'nfs': nfs,
            'samba': samba,
        }
