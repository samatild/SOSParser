"""
Supportconfig System Logs Analyzer

Analyzes system log files from supportconfig data.
"""

import os
from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser

# Use same configurable limits as sosreport log analyzer
DEFAULT_LOG_LINES = int(os.environ.get('LOG_LINES_DEFAULT', '1000'))
PRIMARY_LOG_LINES = int(os.environ.get('LOG_LINES_PRIMARY', str(DEFAULT_LOG_LINES)))


class SystemLogsAnalyzer:
    """Analyzer for system logs."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Analyze system logs."""
        system_logs = {}
        messages = self.parser.read_file_tail('messages.txt', PRIMARY_LOG_LINES)
        if messages:
            system_logs['messages'] = messages
        messages_config = self.parser.read_file_tail('messages_config.txt', PRIMARY_LOG_LINES)
        if messages_config:
            system_logs['syslog'] = messages_config
        messages_localwarn = self.parser.read_file_tail('messages_localwarn.txt', PRIMARY_LOG_LINES)
        if messages_localwarn and 'syslog' not in system_logs:
            system_logs['syslog'] = messages_localwarn

        return system_logs
