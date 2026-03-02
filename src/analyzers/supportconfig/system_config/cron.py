"""
Supportconfig Cron Configuration Analyzer

Analyzes cron/at scheduler configuration from cron.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class CronConfigAnalyzer:
    """Analyzer for cron/at scheduler configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract cron/at scheduler configuration from cron.txt.

        Returns a dictionary with:
          - cron_verification_status
          - cron_service (loaded/active/pid)
          - cron_dirs: mapping of cron.* dirs to file lists
          - crontab: /etc/crontab contents
          - at_verification_status
          - at_service (loaded/active/pid)
          - at_jobs: list of job files
        """
        data: Dict[str, Any] = {
            'cron_verification_status': '',
            'cron_service': {},
            'cron_dirs': {},
            'crontab': '',
            'at_verification_status': '',
            'at_service': {},
            'at_jobs': [],
            'at_jobs_content': {},
        }

        content = self.parser.read_file('cron.txt')
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
            if section['type'] == 'Verification':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].lower()
                for line in lines:
                    if 'Verification Status:' in line:
                        status = line.split(':', 1)[1].strip()
                        if 'cronie' in header:
                            data['cron_verification_status'] = status
                        elif 'at-' in header or ' at-' in header:
                            data['at_verification_status'] = status

            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                if 'systemctl status cron.service' in cmd_line:
                    data['cron_service'] = _parse_systemctl(lines[1:])
                elif 'systemctl status atd.service' in cmd_line:
                    data['at_service'] = _parse_systemctl(lines[1:])
                elif 'find -L /etc/cron.' in cmd_line:
                    dir_name = cmd_line.split()[-1].rstrip('/').split('/')[-1]
                    files = [l.strip() for l in lines[1:] if l.strip()]
                    data['cron_dirs'][dir_name] = files
                elif 'find /var/spool/atjobs/' in cmd_line:
                    jobs = [l.strip() for l in lines[1:] if l.strip()]
                    data['at_jobs'].extend(jobs)

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].strip()
                if '/etc/crontab' in header and 'not found' not in header.lower():
                    data['crontab'] = '\n'.join(lines[1:]).strip()
                elif '/var/spool/atjobs/' in header and 'not found' not in header.lower():
                    content_str = '\n'.join(lines[1:]).strip()
                    data['at_jobs_content'][header] = content_str

        return data
