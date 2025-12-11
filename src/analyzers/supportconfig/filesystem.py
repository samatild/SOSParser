#!/usr/bin/env python3
"""Filesystem analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any
from .parser import SupportconfigParser


class SupportconfigFilesystem:
    """Analyzer for supportconfig filesystem information."""
    
    def __init__(self, root_path: Path):
        """
        Initialize filesystem analyzer.
        
        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete filesystem analysis.
        
        Returns:
            Dictionary with filesystem information
        """
        return {
            'mounts': self.get_mounts(),
            'disk_usage': self.get_disk_usage(),
            'lvm': self.get_lvm_info(),
            'filesystems': self.get_filesystem_types(),
        }
    
    def get_mounts(self) -> Dict[str, Any]:
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
    
    def get_disk_usage(self) -> Dict[str, Any]:
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
    
    def get_lvm_info(self) -> Dict[str, Any]:
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
    
    def get_filesystem_types(self) -> Dict[str, Any]:
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
