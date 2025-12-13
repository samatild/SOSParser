"""
Supportconfig Filesystem Types Analyzer

Analyzes filesystem type information from filesystem data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class FilesystemTypesAnalyzer:
    """Analyzer for filesystem type information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract filesystem type information."""
        fs_types = {}

        # Block device IDs
        blkid = self.parser.get_command_output('fs-diskio.txt', '/sbin/blkid')
        if blkid:
            fs_types['blkid'] = blkid

        # Supported filesystems not present explicitly; leave placeholder if needed
        filesystems = self.parser.get_file_listing('fs-diskio.txt', '/proc/filesystems')
        if filesystems:
            fs_types['filesystems'] = filesystems

        return fs_types
