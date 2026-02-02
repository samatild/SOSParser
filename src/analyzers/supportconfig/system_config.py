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
from .config_analyzers.sssd import SSSDConfigAnalyzer
from .config_analyzers.ntp import NTPConfigAnalyzer
from utils.logger import Logger


class SupportconfigSystemConfig:
    """Analyzer for supportconfig system configuration."""
    
    def __init__(self, root_path: Path):
        """Initialize with root path of extracted supportconfig."""
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """Run all system config analysis."""
        Logger.memory("  SysConfig: start")
        
        general = GeneralConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: general done")
        
        boot = BootConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: boot done")
        
        authentication = AuthenticationConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: authentication done")
        
        ssh_runtime = SSHRuntimeConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: ssh_runtime done")
        
        services = ServicesConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: services done")
        
        cron = CronConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: cron done")
        
        security = SecurityConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: security done")
        
        packages = PackagesConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: packages done")
        
        kernel_modules = KernelModulesConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: kernel_modules done")
        
        crash = CrashConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: crash done")
        
        containers = ContainersConfigAnalyzer(self.root_path).analyze()
        Logger.memory("  SysConfig: containers done")
        
        sssd = SSSDConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: sssd done")
        
        ntp = NTPConfigAnalyzer(self.root_path, self.parser).analyze()
        Logger.memory("  SysConfig: ntp done")
        
        return {
            'general': general,
            'boot': boot,
            'authentication': authentication,
            'ssh_runtime': ssh_runtime,
            'services': services,
            'cron': cron,
            'security': security,
            'packages': packages,
            'kernel_modules': kernel_modules,
            'crash': crash,
            'containers': containers,
            'sssd': sssd,
            'ntp': ntp,
        }
