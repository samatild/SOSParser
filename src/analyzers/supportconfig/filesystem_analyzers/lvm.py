"""
Supportconfig LVM Analyzer

Analyzes LVM information from filesystem data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class LvmAnalyzer:
    """Analyzer for LVM information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract LVM information."""
        lvm_info = {}

        # Get pvs, vgs, lvs from lvm.txt
        pvs = self.parser.get_command_output('lvm.txt', '/sbin/pvs')
        if pvs:
            lvm_info['pvs'] = pvs

        vgs = self.parser.get_command_output('lvm.txt', '/sbin/vgs')
        if vgs:
            lvm_info['vgs'] = vgs

        lvs = self.parser.get_command_output('lvm.txt', '/sbin/lvs')
        if lvs:
            lvm_info['lvs'] = lvs

        # Get pvdisplay
        pvdisplay = self.parser.get_command_output('lvm.txt', '/sbin/pvdisplay')
        if pvdisplay:
            lvm_info['pvdisplay'] = pvdisplay

        # Get vgdisplay
        vgdisplay = self.parser.get_command_output('lvm.txt', '/sbin/vgdisplay')
        if vgdisplay:
            lvm_info['vgdisplay'] = vgdisplay

        # Get lvdisplay
        lvdisplay = self.parser.get_command_output('lvm.txt', '/sbin/lvdisplay')
        if lvdisplay:
            lvm_info['lvdisplay'] = lvdisplay

        # If nothing was found, add a note
        if not lvm_info:
            lvm_info['note'] = 'No LVM volumes detected in supportconfig'

        return lvm_info
