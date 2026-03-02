"""
Supportconfig Packages Configuration Analyzer

Analyzes installed RPM packages from rpm.txt.
"""

from typing import Dict, Any, List
from pathlib import Path
from ..parser import SupportconfigParser


class PackagesConfigAnalyzer:
    """Analyzer for package management configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Summarize installed RPMs from rpm.txt.
        """
        packages: Dict[str, Any] = {
            'rpm_count': 0,
            'rpm_list': [],
            'repos': '',
            'package_manager_conf': '',
        }

        content = self.parser.read_file('rpm.txt')
        if not content:
            return packages

        sections = self.parser.extract_sections(content)
        rpm_entries: List[str] = []

        for section in sections:
            if section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd = lines[0].strip('# ').strip()
                # Full rpm list
                if 'rpm -qa --queryformat "%-35{NAME}' in cmd:
                    # Skip header line if present
                    for line in lines[1:]:
                        line = line.strip()
                        if not line or line.startswith('NAME '):
                            continue
                        rpm_entries.append(line)
                # Repo list (if present)
                elif 'zypper lr' in cmd or 'zypper repos' in cmd:
                    repo_body = '\n'.join(lines[1:]).strip()
                    if repo_body:
                        packages['repos'] = repo_body
                # Package manager conf (e.g., zypper.conf) - none in this file, placeholder if added later

        if rpm_entries:
            packages['rpm_count'] = len(rpm_entries)
            packages['rpm_list'] = rpm_entries  # Full list

        return packages
