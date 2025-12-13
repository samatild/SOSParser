"""
Supportconfig Mounts Analyzer

Analyzes mount point information from filesystem data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class MountsAnalyzer:
    """Analyzer for mount point information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract mount point information."""
        mounts = {}

        # df -Th provides type + sizes
        df_th = self.parser.get_command_output('fs-diskio.txt', '/bin/df -Th')
        if df_th:
            mounts['df_th'] = df_th

        # findmnt tree
        findmnt = self.parser.get_command_output('fs-diskio.txt', '/bin/findmnt')
        if findmnt:
            mounts['findmnt'] = findmnt
            # Use findmnt as current mounts view for template compatibility
            mounts['proc_mounts'] = findmnt

        # lsblk layout
        lsblk = self.parser.get_command_output('fs-diskio.txt', "/bin/lsblk -i -o 'NAME,KNAME,MAJ:MIN,FSTYPE,LABEL,RO,RM,MODEL,SIZE,OWNER,GROUP,MODE,ALIGNMENT,MIN-IO,OPT-IO,PHY-SEC,LOG-SEC,ROTA,SCHED,MOUNTPOINT,DISC-ALN,DISC-GRAN,DISC-MAX,DISC-ZERO'")
        if lsblk:
            mounts['lsblk'] = lsblk

        # Raw mount output if available
        mount_output = self.parser.get_command_output('fs-diskio.txt', '/bin/mount')
        if mount_output:
            mounts['mount'] = mount_output

        # /etc/fstab listing from etc.txt
        fstab = self.parser.get_file_listing('etc.txt', '/etc/fstab')
        if fstab:
            mounts['fstab'] = fstab

        # /proc/partitions
        proc_parts = self.parser.get_file_listing('fs-diskio.txt', '/proc/partitions')
        if proc_parts:
            mounts['proc_partitions'] = proc_parts

        return mounts
