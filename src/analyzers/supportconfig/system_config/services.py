"""
Supportconfig Services Configuration Analyzer

Analyzes systemd service status from systemd-status.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class ServicesConfigAnalyzer:
    """Analyzer for systemd service configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract basic systemd service status from systemd-status.txt.

        Returns:
            Dictionary with:
              - entries: list of service dicts (name, desc, loaded, active, pid, cmd)
              - failed_services: list of entries where Active indicates failure/inactive
        """
        services: Dict[str, Any] = {
            'entries': [],
            'failed_services': [],
        }

        content = self.parser.read_file('systemd-status.txt')
        if not content:
            return services

        sections = self.parser.extract_sections(content)

        for section in sections:
            if section['type'] != 'Command':
                continue
            lines = section['content'].split('\n')
            if not lines:
                continue
            header = lines[0].strip('# ').strip()
            service_name = ''
            if 'systemctl status' in header:
                # Extract service name from the command
                parts = header.split('status', 1)
                if len(parts) > 1:
                    service_name = parts[1].strip().strip("'\"")
            # Fallback to unknown if not extracted
            if not service_name:
                service_name = '(unknown)'

            service_desc = ''
            loaded = ''
            active = ''
            main_pid = ''

            for line in lines[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                # First bullet line: "● name.service - Description"
                if stripped.startswith('●'):
                    bullet = stripped.lstrip('●').strip()
                    if ' - ' in bullet:
                        maybe_name, maybe_desc = bullet.split(' - ', 1)
                        service_desc = maybe_desc.strip()
                        # Use the name from the bullet if it looks like a service
                        if maybe_name.endswith('.service'):
                            service_name = maybe_name.strip()
                    continue
                if stripped.startswith('Loaded:'):
                    loaded = stripped.split(':', 1)[1].strip()
                elif stripped.startswith('Active:'):
                    active = stripped.split(':', 1)[1].strip()
                elif stripped.startswith('Main PID:'):
                    main_pid = stripped.split(':', 1)[1].strip()

            entry = {
                'name': service_name,
                'description': service_desc,
                'loaded': loaded,
                'active': active,
                'main_pid': main_pid,
                'command': header,
            }
            services['entries'].append(entry)

            active_lower = active.lower()
            if 'failed' in active_lower or 'inactive' in active_lower:
                services['failed_services'].append(entry)

        return services
