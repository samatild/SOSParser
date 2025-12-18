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
        return {
            'mounts': MountsAnalyzer(self.root_path, self.parser).analyze(),
            'disk_usage': (
                DiskUsageAnalyzer(self.root_path, self.parser).analyze()
            ),
            'lvm': LvmAnalyzer(self.root_path, self.parser).analyze(),
            'filesystems': FilesystemTypesAnalyzer(
                self.root_path, self.parser).analyze(),
            'nfs': NfsAnalyzer(self.root_path, self.parser).analyze(),
            'samba': SambaAnalyzer(self.root_path, self.parser).analyze(),
        }
