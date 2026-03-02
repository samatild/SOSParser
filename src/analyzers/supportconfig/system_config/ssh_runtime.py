"""
Supportconfig SSH Runtime Configuration Analyzer

Analyzes SSH runtime configuration from ssh.txt.
Since supportconfig doesn't capture 'sshd -T' output, we parse sshd_config
and create a similar structure.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class SSHRuntimeConfigAnalyzer:
    """Analyzer for SSH runtime configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract SSH runtime configuration from ssh.txt.
        Since supportconfig doesn't capture 'sshd -T' output, we parse sshd_config
        and create a similar structure.

        Returns:
            Dictionary shaped like the report template expects for ssh_runtime:
              - source: path to the config file
              - settings: list of dicts with 'option' and 'value_list'
              - raw: the raw configuration content
        """
        ssh_runtime: Dict[str, Any] = {
            'source': '',
            'settings': [],
            'raw': '',
        }

        content = self.parser.read_file('ssh.txt')
        if not content:
            return ssh_runtime

        sections = self.parser.extract_sections(content)
        grouped = {}
        order = []

        for section in sections:
            if section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue

                file_path = lines[0].strip('# ').strip()
                if '/etc/ssh/sshd_config' in file_path and 'not found' not in file_path.lower():
                    ssh_runtime['source'] = file_path
                    ssh_runtime['raw'] = '\n'.join(lines[1:]).strip()

                    # Parse configuration into settings format similar to sshd -T output
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('Include'):
                            parts = line.split(None, 1)
                            if len(parts) >= 1:
                                key = parts[0]
                                value = parts[1] if len(parts) > 1 else ''

                                if key not in grouped:
                                    grouped[key] = []
                                    order.append(key)
                                grouped[key].append(value)

                    # Create settings list in order
                    ssh_runtime['settings'] = [{'option': key, 'value_list': grouped.get(key, [])} for key in order]

        return ssh_runtime
