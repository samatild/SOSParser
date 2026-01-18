#!/usr/bin/env python3
"""Filesystem analysis from sosreport"""

from pathlib import Path
from utils.logger import Logger


class FilesystemAnalyzer:
    """Analyze filesystem configuration and usage from sosreport"""
    
    def analyze_mounts(self, base_path: Path) -> dict:
        """Analyze mount points and fstab"""
        Logger.debug("Analyzing mounts and fstab")
        
        data = {}
        
        # fstab
        fstab = base_path / 'etc' / 'fstab'
        if fstab.exists():
            data['fstab'] = fstab.read_text()
        
        # Current mounts
        mounts = base_path / 'proc' / 'mounts'
        if mounts.exists():
            data['proc_mounts'] = mounts.read_text()
        
        # Mount command output
        mount_cmd = base_path / 'sos_commands' / 'filesys' / 'mount_-l'
        if mount_cmd.exists():
            data['mount_output'] = mount_cmd.read_text()
        
        # Mountinfo
        mountinfo = base_path / 'proc' / 'self' / 'mountinfo'
        if mountinfo.exists():
            data['mountinfo'] = mountinfo.read_text()
        
        return data
    
    def analyze_lvm(self, base_path: Path) -> dict:
        """Analyze LVM configuration"""
        Logger.debug("Analyzing LVM configuration")
        
        data = {}
        lvm2_dir = base_path / 'sos_commands' / 'lvm2'
        
        if lvm2_dir.exists():
            # Find pvs output (filename varies by sosreport version)
            pvs_files = list(lvm2_dir.glob('pvs_*'))
            if pvs_files:
                # Prefer the most detailed one (usually the longest filename)
                pvs_file = max(pvs_files, key=lambda f: len(f.name))
                try:
                    data['pvs'] = pvs_file.read_text()
                except Exception:
                    pass
            
            # Find vgs output
            vgs_files = list(lvm2_dir.glob('vgs_*'))
            if vgs_files:
                vgs_file = max(vgs_files, key=lambda f: len(f.name))
                try:
                    data['vgs'] = vgs_file.read_text()
                except Exception:
                    pass
            
            # Find lvs output
            lvs_files = list(lvm2_dir.glob('lvs_*'))
            if lvs_files:
                lvs_file = max(lvs_files, key=lambda f: len(f.name))
                try:
                    data['lvs'] = lvs_file.read_text()
                except Exception:
                    pass
            
            # Find vgdisplay output (contains detailed VG and LV info)
            vgdisplay_files = list(lvm2_dir.glob('vgdisplay_*'))
            if vgdisplay_files:
                vgdisplay_file = max(vgdisplay_files, key=lambda f: len(f.name))
                try:
                    data['vgdisplay'] = vgdisplay_file.read_text()
                except Exception:
                    pass
            
            # Find pvdisplay output
            pvdisplay_files = list(lvm2_dir.glob('pvdisplay_*'))
            if pvdisplay_files:
                pvdisplay_file = max(pvdisplay_files, key=lambda f: len(f.name))
                try:
                    data['pvdisplay'] = pvdisplay_file.read_text()
                except Exception:
                    pass
            
            # Find lvdisplay output
            lvdisplay_files = list(lvm2_dir.glob('lvdisplay_*'))
            if lvdisplay_files:
                lvdisplay_file = max(lvdisplay_files, key=lambda f: len(f.name))
                try:
                    data['lvdisplay'] = lvdisplay_file.read_text()
                except Exception:
                    pass
        
        # LVM config
        lvm_conf = base_path / 'etc' / 'lvm' / 'lvm.conf'
        if lvm_conf.exists():
            try:
                data['lvm_conf'] = lvm_conf.read_text()
            except Exception:
                pass
        
        # If no LVM data found, add a note
        if not data:
            data['note'] = 'No LVM configuration detected in sosreport'
        
        return data
    
    def analyze_disk_usage(self, base_path: Path) -> dict:
        """Analyze disk usage"""
        Logger.debug("Analyzing disk usage")
        
        data = {}
        
        # df output
        df_cmd = base_path / 'sos_commands' / 'filesys' / 'df_-al_-x_autofs'
        if not df_cmd.exists():
            df_cmd = base_path / 'df'
        if df_cmd.exists():
            data['df'] = df_cmd.read_text()
        
        # df inodes
        df_inodes = base_path / 'sos_commands' / 'filesys' / 'df_-ali'
        if df_inodes.exists():
            data['df_inodes'] = df_inodes.read_text()
        
        # Disk stats
        diskstats = base_path / 'proc' / 'diskstats'
        if diskstats.exists():
            data['diskstats'] = diskstats.read_text()
        
        return data
    
    def analyze_filesystems(self, base_path: Path) -> dict:
        """Analyze filesystem types and features"""
        Logger.debug("Analyzing filesystems")
        
        data = {}
        
        # Filesystem types
        filesystems = base_path / 'proc' / 'filesystems'
        if filesystems.exists():
            data['filesystems'] = filesystems.read_text()
        
        # XFS info
        xfs_info_dir = base_path / 'sos_commands' / 'xfs'
        if xfs_info_dir.exists():
            xfs_files = {}
            for xfs_file in xfs_info_dir.glob('xfs_info_*'):
                try:
                    xfs_files[xfs_file.name] = xfs_file.read_text()
                except Exception:
                    pass
            if xfs_files:
                data['xfs_info'] = xfs_files
        
        # Ext filesystem info
        ext_info_dir = base_path / 'sos_commands' / 'filesys'
        if ext_info_dir.exists():
            ext_files = {}
            for ext_file in ext_info_dir.glob('dumpe2fs_*'):
                try:
                    ext_files[ext_file.name] = ext_file.read_text()[:5000]  # Limit size
                except Exception:
                    pass
            if ext_files:
                data['ext_info'] = ext_files
        
        # Blkid output
        blkid = base_path / 'sos_commands' / 'block' / 'blkid_-c_.dev.null'
        if not blkid.exists():
            blkid = base_path / 'sos_commands' / 'filesys' / 'blkid'
        if blkid.exists():
            data['blkid'] = blkid.read_text()
        
        return data
