"""
Supportconfig Containers Configuration Analyzer

Analyzes Docker container runtime information.
"""

from typing import Dict, Any
from pathlib import Path
from analyzers.docker import DockerCommandsAnalyzer


class ContainersConfigAnalyzer:
    """Analyzer for container runtime configuration."""

    def __init__(self, root_path: Path, parser=None):
        """Initialize with root path."""
        self.root_path = root_path

    def analyze(self) -> Dict[str, Any]:
        """
        Parse docker information from sos_commands/docker when present.
        """
        analyzer = DockerCommandsAnalyzer(self.root_path)
        return analyzer.analyze()
