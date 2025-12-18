"""
Supportconfig NFS Analyzer

Analyzes NFS client and server configuration from filesystem data.
"""

from typing import Dict, Any, List
from pathlib import Path
from ..parser import SupportconfigParser


class NfsAnalyzer:
    """Analyzer for NFS information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract NFS information."""
        nfs_info = {}

        # NFS client packages and verification
        client_packages = self._analyze_client_packages()
        if client_packages:
            nfs_info['client_packages'] = client_packages

        # NFS server packages and verification
        server_packages = self._analyze_server_packages()
        if server_packages:
            nfs_info['server_packages'] = server_packages

        # Service status
        services = self._analyze_services()
        if services:
            nfs_info['services'] = services

        # NFS configuration
        config = self._analyze_config()
        if config:
            nfs_info['config'] = config

        # NFS statistics and status
        stats = self._analyze_stats()
        if stats:
            nfs_info['stats'] = stats

        # NFS mounts from fstab
        mounts = self._analyze_mounts()
        if mounts:
            nfs_info['mounts'] = mounts

        # NFS exports (server side)
        exports = self._analyze_exports()
        if exports:
            nfs_info['exports'] = exports

        # If nothing was found, add a note
        if not nfs_info:
            nfs_info['note'] = 'No NFS configuration detected in supportconfig'

        return nfs_info

    def _analyze_client_packages(self) -> Dict[str, Any]:
        """Analyze NFS client packages."""
        packages = {}

        content = self.parser.read_file('nfs.txt')
        if content:
            verification_sections = self.parser.find_sections_by_type(content, 'Verification')
            for section in verification_sections:
                header = section['header']
                if 'nfs-client' in header:
                    packages['client'] = {
                        'header': header,
                        'content': section['content']
                    }
                elif 'rpcbind' in header:
                    packages['rpcbind'] = {
                        'header': header,
                        'content': section['content']
                    }

        return packages

    def _analyze_server_packages(self) -> Dict[str, Any]:
        """Analyze NFS server packages."""
        packages = {}

        content = self.parser.read_file('nfs.txt')
        if content:
            verification_sections = self.parser.find_sections_by_type(content, 'Verification')
            for section in verification_sections:
                header = section['header']
                if 'nfs-kernel-server' in header:
                    packages['server'] = {
                        'header': header,
                        'content': section['content']
                    }

        return packages

    def _analyze_services(self) -> Dict[str, Any]:
        """Analyze NFS-related services."""
        services = {}

        # NFS client service
        nfs_service = self.parser.get_command_output('nfs.txt', '/bin/systemctl status nfs.service')
        if nfs_service:
            services['nfs_client'] = nfs_service

        # RPC bind service
        rpcbind_service = self.parser.get_command_output('nfs.txt', '/bin/systemctl status rpcbind.service')
        if rpcbind_service:
            services['rpcbind'] = rpcbind_service

        # NFS server service
        nfs_server = self.parser.get_command_output('nfs.txt', '/bin/systemctl status nfs-server.service')
        if nfs_server:
            services['nfs_server'] = nfs_server

        return services

    def _analyze_config(self) -> Dict[str, Any]:
        """Analyze NFS configuration."""
        config = {}

        # NFS sysconfig
        sysconfig = self.parser.get_file_listing('nfs.txt', '/etc/sysconfig/nfs')
        if sysconfig:
            config['sysconfig'] = sysconfig

        return config

    def _analyze_stats(self) -> Dict[str, Any]:
        """Analyze NFS statistics and status."""
        stats = {}

        # NFS statistics
        nfsstat = self.parser.get_command_output('nfs.txt', '/usr/sbin/nfsstat')
        if nfsstat:
            stats['nfsstat'] = nfsstat

        # RPC info
        rpcinfo = self.parser.get_command_output('nfs.txt', '/sbin/rpcinfo -p')
        if rpcinfo:
            stats['rpcinfo'] = rpcinfo

        return stats

    def _analyze_mounts(self) -> List[str]:
        """Analyze NFS mounts from fstab."""
        mounts = []

        # Get NFS entries from fstab
        fstab_nfs = self.parser.get_command_output('nfs.txt', "/bin/egrep '[[:space:]]nfs[[:space:]]|[[:space:]]nfs4[[:space:]]' /etc/fstab")
        if fstab_nfs and fstab_nfs.strip():
            mounts.append(fstab_nfs)

        return mounts

    def _analyze_exports(self) -> Dict[str, Any]:
        """Analyze NFS exports."""
        exports = {}

        # Exportfs output
        exportfs = self.parser.get_command_output('nfs.txt', '/usr/sbin/exportfs -v')
        if exportfs:
            exports['exportfs'] = exportfs

        # Exports file
        exports_file = self.parser.get_file_listing('nfs.txt', '/etc/exports')
        if exports_file:
            exports['exports_file'] = exports_file

        return exports
