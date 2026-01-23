#!/usr/bin/env python3
"""Log file analysis from sosreport"""

import os
from pathlib import Path
from utils.logger import Logger


# Configurable log line limits via environment variables
# Default: 1000 lines, Max recommended: 5000 for browser performance
DEFAULT_LOG_LINES = int(os.environ.get('LOG_LINES_DEFAULT', '1000'))
# Some logs may warrant more lines (e.g., journal, messages)
PRIMARY_LOG_LINES = int(os.environ.get('LOG_LINES_PRIMARY', str(DEFAULT_LOG_LINES)))
# Secondary logs can have fewer lines (e.g., cron, mail)
SECONDARY_LOG_LINES = int(os.environ.get('LOG_LINES_SECONDARY', str(DEFAULT_LOG_LINES // 2)))


class LogAnalyzer:
    """Analyze system logs from sosreport"""
    
    def analyze_system_logs(self, base_path: Path) -> dict:
        """Analyze system logs (messages, syslog)"""
        Logger.debug("Analyzing system logs")
        
        data = {}
        
        # messages
        messages = base_path / 'var' / 'log' / 'messages'
        if messages.exists():
            data['messages'] = self._tail_file(messages, PRIMARY_LOG_LINES)
        
        # syslog
        syslog = base_path / 'var' / 'log' / 'syslog'
        if syslog.exists():
            data['syslog'] = self._tail_file(syslog, PRIMARY_LOG_LINES)
        
        # Boot log
        boot_log = base_path / 'var' / 'log' / 'boot.log'
        if boot_log.exists():
            data['boot_log'] = self._tail_file(boot_log, SECONDARY_LOG_LINES)
        
        return data
    
    def analyze_kernel_logs(self, base_path: Path) -> dict:
        """Analyze kernel logs"""
        Logger.debug("Analyzing kernel logs")
        
        data = {}
        
        # dmesg
        dmesg = base_path / 'sos_commands' / 'kernel' / 'dmesg'
        if not dmesg.exists():
            dmesg = base_path / 'var' / 'log' / 'dmesg'
        if dmesg.exists():
            data['dmesg'] = self._tail_file(dmesg, PRIMARY_LOG_LINES)
        
        # kern.log
        kern_log = base_path / 'var' / 'log' / 'kern.log'
        if kern_log.exists():
            data['kern_log'] = self._tail_file(kern_log, PRIMARY_LOG_LINES)
        
        return data
    
    def analyze_auth_logs(self, base_path: Path) -> dict:
        """Analyze authentication logs"""
        Logger.debug("Analyzing authentication logs")
        
        data = {}
        
        # secure
        secure = base_path / 'var' / 'log' / 'secure'
        if secure.exists():
            data['secure'] = self._tail_file(secure, PRIMARY_LOG_LINES)
        
        # auth.log
        auth_log = base_path / 'var' / 'log' / 'auth.log'
        if auth_log.exists():
            data['auth_log'] = self._tail_file(auth_log, PRIMARY_LOG_LINES)
        
        # audit log
        audit_log = base_path / 'var' / 'log' / 'audit' / 'audit.log'
        if audit_log.exists():
            data['audit_log'] = self._tail_file(audit_log, SECONDARY_LOG_LINES)
        
        # lastlog
        lastlog = base_path / 'sos_commands' / 'login' / 'lastlog_-t_999999'
        if not lastlog.exists():
            lastlog = base_path / 'sos_commands' / 'login' / 'lastlog'
        if lastlog.exists():
            data['lastlog'] = lastlog.read_text()
        
        return data
    
    def analyze_service_logs(self, base_path: Path) -> dict:
        """Analyze service-specific logs"""
        Logger.debug("Analyzing service logs")
        
        data = {}
        
        # Journal log - primary importance
        journal = base_path / 'sos_commands' / 'logs' / 'journalctl_--no-pager'
        if not journal.exists():
            journal = base_path / 'sos_commands' / 'systemd' / 'journalctl_--no-pager_--boot'
        if journal.exists():
            data['journal'] = self._tail_file(journal, PRIMARY_LOG_LINES)
        
        # Cron log
        cron = base_path / 'var' / 'log' / 'cron'
        if cron.exists():
            data['cron'] = self._tail_file(cron, SECONDARY_LOG_LINES)
        
        # Mail log
        maillog = base_path / 'var' / 'log' / 'maillog'
        if maillog.exists():
            data['maillog'] = self._tail_file(maillog, SECONDARY_LOG_LINES)
        
        # YUM/DNF log
        yum_log = base_path / 'var' / 'log' / 'yum.log'
        if yum_log.exists():
            data['yum_log'] = self._tail_file(yum_log, SECONDARY_LOG_LINES)
        
        dnf_log = base_path / 'var' / 'log' / 'dnf.log'
        if dnf_log.exists():
            data['dnf_log'] = self._tail_file(dnf_log, SECONDARY_LOG_LINES)
        
        return data
    
    def _tail_file(self, file_path: Path, lines: int = None) -> str:
        """Read last N lines from a file"""
        if lines is None:
            lines = DEFAULT_LOG_LINES
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                content = ''.join(tail_lines)
                return content
        except Exception as e:
            Logger.warning(f"Failed to read {file_path}: {e}")
            return f"Error reading file: {e}"
