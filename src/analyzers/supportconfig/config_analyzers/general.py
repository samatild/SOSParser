"""
Supportconfig General Configuration Analyzer

Analyzes general system information from basic-environment.txt and basic-health-check.txt.
"""

from typing import Dict, Any, List
from pathlib import Path
from ..parser import SupportconfigParser


class GeneralConfigAnalyzer:
    """Analyzer for general system configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Populate general tab from basic-environment.txt and basic-health-check.txt.
        """
        general: Dict[str, Any] = {}

        # basic-environment.txt
        env_content = self.parser.read_file('basic-environment.txt')
        if env_content:
            sections = self.parser.extract_sections(env_content)
            for section in sections:
                if section['type'] == 'Command':
                    lines = section['content'].split('\n')
                    if not lines:
                        continue
                    cmd = lines[0].strip('# ').strip()
                    if cmd == '/bin/date':
                        general['collection_time'] = '\n'.join(lines[1:]).strip()
                    elif cmd == '/bin/uname -a':
                        general['uname'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'System':
                    # virtualization section body
                    text = section['content'].strip()
                    if text:
                        general['virtualization'] = text
                elif section['type'] == 'Configuration':
                    lines = section['content'].split('\n')
                    if lines and '/etc/os-release' in lines[0]:
                        general['os_release'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'Verification':
                    # Example: RPM Not Installed: firewalld
                    text = section['content'].strip()
                    if text:
                        general.setdefault('verifications', []).append(text)

        # basic-health-check.txt
        health_content = self.parser.read_file('basic-health-check.txt')
        if health_content:
            sections = self.parser.extract_sections(health_content)
            for section in sections:
                lines = section['content'].split('\n')
                if not lines:
                    continue
                if section['type'] == 'Command':
                    cmd = lines[0].strip('# ').strip()
                    body = '\n'.join(lines[1:]).strip()
                    if '/usr/bin/uptime' in cmd:
                        general['uptime'] = body
                    elif 'cpu/vulnerabilities' in cmd:
                        general['cpu_vulnerabilities'] = body
                    elif 'vmstat' in cmd:
                        general['vmstat'] = body
                    elif cmd.startswith('/usr/bin/free'):
                        general['free'] = body
                    elif cmd.startswith('/bin/df -h'):
                        general['df_h'] = body
                    elif cmd.startswith('/bin/df -i'):
                        general['df_i'] = body
                    elif cmd.startswith('/bin/ps axwwo'):
                        # avoid full process list; keep top part
                        general['ps_ax'] = '\n'.join(lines[:40]).strip()
                elif section['type'] == 'Configuration':
                    if '/proc/sys/kernel/tainted' in lines[0]:
                        general['kernel_tainted'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'Summary':
                    # Top processes summaries
                    header = section['header'].lower()
                    body = section['content'].strip()
                    if 'cpu' in header:
                        general['top_cpu'] = body
                    elif 'memory' in header:
                        general['top_mem'] = body

        return general
