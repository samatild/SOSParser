"""
Supportconfig Kernel Modules Configuration Analyzer

Analyzes kernel modules and parameters from env.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class KernelModulesConfigAnalyzer:
    """Analyzer for kernel modules and parameters."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Capture kernel-related info from env.txt (sysctl, ulimit, etc.).
        """
        data: Dict[str, Any] = {
            'sysctl_all': '',
            'sysctl_files': {},
            'sysctl_service': {},
            'ulimit': '',
            'lsmod': '',
            'modprobe_d': {},
        }

        content = self.parser.read_file('env.txt')
        if not content:
            return data

        sections = self.parser.extract_sections(content)

        def _parse_systemctl(lines):
            info = {}
            for line in lines:
                line = line.strip()
                if line.startswith('Loaded:'):
                    info['loaded'] = line.split(':', 1)[1].strip()
                elif line.startswith('Active:'):
                    info['active'] = line.split(':', 1)[1].strip()
                elif line.startswith('Main PID:'):
                    info['pid'] = line.split(':', 1)[1].strip()
            return info

        for section in sections:
            if section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd = lines[0].strip('# ').strip()
                if cmd.startswith('ulimit'):
                    data['ulimit'] = '\n'.join(lines[1:]).strip()
                elif 'systemctl status systemd-sysctl.service' in cmd:
                    data['sysctl_service'] = _parse_systemctl(lines[1:])
                elif '/sbin/sysctl -a' in cmd or 'sysctl -a' in cmd:
                    data['sysctl_all'] = '\n'.join(lines[1:]).strip()

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
                if 'sysctl' in header:
                    data['sysctl_files'][header] = body

        return data
