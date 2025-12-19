"""
Supportconfig System Configuration Analyzer

Analyzes system configuration from supportconfig format including:
- Boot and GRUB configuration
- SSH configuration
- Authentication settings
"""

from typing import Dict, Any
from pathlib import Path
from .parser import SupportconfigParser
from .config_analyzers.general import GeneralConfigAnalyzer
from .config_analyzers.boot import BootConfigAnalyzer
from .config_analyzers.authentication import AuthenticationConfigAnalyzer
from .config_analyzers.ssh_runtime import SSHRuntimeConfigAnalyzer
from .config_analyzers.services import ServicesConfigAnalyzer
from .config_analyzers.cron import CronConfigAnalyzer
from .config_analyzers.security import SecurityConfigAnalyzer
from .config_analyzers.packages import PackagesConfigAnalyzer
from .config_analyzers.kernel_modules import KernelModulesConfigAnalyzer
from .config_analyzers.containers import ContainersConfigAnalyzer
from .config_analyzers.crash import CrashConfigAnalyzer


class SupportconfigSystemConfig:
    """Analyzer for supportconfig system configuration."""
    
    def __init__(self, root_path: Path):
        """Initialize with root path of extracted supportconfig."""
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """Run all system config analysis."""
        return {
            'general': GeneralConfigAnalyzer(self.root_path, self.parser).analyze(),
            'boot': BootConfigAnalyzer(self.root_path, self.parser).analyze(),
            'authentication': AuthenticationConfigAnalyzer(self.root_path, self.parser).analyze(),
            'ssh_runtime': SSHRuntimeConfigAnalyzer(self.root_path, self.parser).analyze(),
            'services': ServicesConfigAnalyzer(self.root_path, self.parser).analyze(),
            'cron': CronConfigAnalyzer(self.root_path, self.parser).analyze(),
            'security': SecurityConfigAnalyzer(self.root_path, self.parser).analyze(),
            'packages': PackagesConfigAnalyzer(self.root_path, self.parser).analyze(),
            'kernel_modules': KernelModulesConfigAnalyzer(self.root_path, self.parser).analyze(),
            'crash': CrashConfigAnalyzer(self.root_path, self.parser).analyze(),
            'containers': ContainersConfigAnalyzer(self.root_path).analyze(),
        }
