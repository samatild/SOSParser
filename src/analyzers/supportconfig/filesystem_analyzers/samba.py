"""
Supportconfig Samba Analyzer

Analyzes Samba/CIFS configuration from filesystem data.
"""

from typing import Dict, Any, List
from pathlib import Path
from ..parser import SupportconfigParser


class SambaAnalyzer:
    """Analyzer for Samba/CIFS information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract Samba/CIFS information."""
        samba_info = {}

        # Samba packages
        packages = self._analyze_packages()
        if packages:
            samba_info['packages'] = packages

        # Package verification status
        verification = self._analyze_verification()
        if verification:
            samba_info['verification'] = verification

        # Samba configuration files (if they exist)
        config = self._analyze_config()
        if config:
            samba_info['config'] = config

        # Samba services status (if any)
        services = self._analyze_services()
        if services:
            samba_info['services'] = services

        # If nothing was found, add a note
        if not samba_info:
            samba_info['note'] = 'No Samba packages or configuration detected in supportconfig'

        return samba_info

    def _analyze_packages(self) -> List[str]:
        """Analyze Samba-related packages."""
        packages = []

        # Get Samba-related packages from rpm.txt grep
        samba_packages = self.parser.get_command_output('samba.txt', '/bin/egrep "samba|smb|cifs|libtallo|libtdb|libwbclient" /var/log/scc_sles15_251211_1144/rpm.txt')
        if samba_packages:
            # Parse the package list (skip the command line itself)
            lines = samba_packages.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and 'samba|smb|cifs|libtallo|libtdb|libwbclient' not in line:
                    packages.append(line)

        return packages

    def _analyze_verification(self) -> Dict[str, Any]:
        """Analyze package verification status."""
        verification = {}

        content = self.parser.read_file('samba.txt')
        if content:
            verification_sections = self.parser.find_sections_by_type(content, 'Verification')
            for section in verification_sections:
                header = section['header']
                content = section['content']
                # Extract package name from header like "RPM Not Installed: samba"
                if 'RPM Not Installed:' in header:
                    package_name = header.split('RPM Not Installed:')[-1].strip()
                    verification[package_name] = {
                        'status': 'not_installed',
                        'header': header,
                        'content': content
                    }

        return verification

    def _analyze_config(self) -> Dict[str, Any]:
        """Analyze Samba configuration files."""
        config = {}

        # Common Samba config locations
        config_files = [
            '/etc/samba/smb.conf',
            '/etc/samba/smb.conf.bak',
            '/etc/samba/smb.conf.local'
        ]

        for config_file in config_files:
            file_content = self.parser.get_file_listing('samba.txt', config_file)
            if file_content:
                config[config_file] = file_content

        return config

    def _analyze_services(self) -> Dict[str, Any]:
        """Analyze Samba-related services."""
        services = {}

        # Common Samba services
        samba_services = ['smb', 'nmb', 'winbind']

        for service in samba_services:
            service_status = self.parser.get_command_output('samba.txt', f'/bin/systemctl status {service}.service')
            if service_status:
                services[service] = service_status

        return services
