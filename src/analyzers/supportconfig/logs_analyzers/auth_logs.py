"""
Supportconfig Auth Logs Analyzer

Analyzes authentication log files from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class AuthLogsAnalyzer:
    """Analyzer for authentication logs."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Analyze authentication logs."""
        auth_logs = {}
        security_audit = self.parser.read_file('security-audit.txt')
        if security_audit:
            sections = self.parser.extract_sections(security_audit)
            for section in sections:
                header = section.get('header', '')
                content = section.get('content', '')
                # Check header or first line of content for audit log path
                first_line = content.split('\n', 1)[0] if content else ''
                if '/var/log/audit/audit.log' in header or '/var/log/audit/audit.log' in first_line:
                    auth_logs['audit_log'] = content.strip()
                    break

        return auth_logs
