#!/usr/bin/env python3
"""Logs analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any
from .parser import SupportconfigParser
from .logs_analyzers.system_logs import SystemLogsAnalyzer
from .logs_analyzers.kernel_logs import KernelLogsAnalyzer
from .logs_analyzers.auth_logs import AuthLogsAnalyzer
from .logs_analyzers.services_logs import ServicesLogsAnalyzer


class SupportconfigLogs:
    """Analyzer for supportconfig log information."""

    def __init__(self, root_path: Path):
        """
        Initialize logs analyzer.

        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze log information from supportconfig.

        Returns:
            Dictionary with log information
        """
        return {
            'system': SystemLogsAnalyzer(self.root_path, self.parser).analyze(),
            'kernel': KernelLogsAnalyzer(self.root_path, self.parser).analyze(),
            'auth': AuthLogsAnalyzer(self.root_path, self.parser).analyze(),
            'services': ServicesLogsAnalyzer(self.root_path, self.parser).analyze(),
        }
