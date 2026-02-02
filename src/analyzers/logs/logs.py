#!/usr/bin/env python3
"""Log file analysis from sosreport"""

import os
import gzip
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils.logger import Logger


# Configurable log line limits via environment variables
# Default: 1000 lines, Max recommended: 5000 for browser performance
DEFAULT_LOG_LINES = int(os.environ.get('LOG_LINES_DEFAULT', '1000'))
# Some logs may warrant more lines (e.g., journal, messages)
PRIMARY_LOG_LINES = int(os.environ.get('LOG_LINES_PRIMARY', str(DEFAULT_LOG_LINES)))
# Secondary logs can have fewer lines (e.g., cron, mail)
SECONDARY_LOG_LINES = int(os.environ.get('LOG_LINES_SECONDARY', str(DEFAULT_LOG_LINES // 2)))
# Lines for historical/rotated logs (keep smaller to avoid heavy reports)
HISTORICAL_LOG_LINES = int(os.environ.get('LOG_LINES_HISTORICAL', '500'))


class LogAnalyzer:
    """Analyze system logs from sosreport"""
    
    def analyze_system_logs(self, base_path: Path) -> dict:
        """Analyze system logs (messages, syslog)"""
        Logger.debug("Analyzing system logs")
        
        data = {}
        log_dir = base_path / 'var' / 'log'
        
        # messages - with fallback to rotated/gzipped files
        messages = log_dir / 'messages'
        messages_content, messages_source = self._read_log_with_fallback(messages, 'messages', log_dir)
        if messages_content:
            data['messages'] = messages_content
            if messages_source != 'messages':
                data['messages_source'] = messages_source
        
        # Get historical messages files
        historical_messages = self._get_historical_logs(log_dir, 'messages')
        if historical_messages:
            data['messages_historical'] = historical_messages
        
        # syslog - with fallback to rotated/gzipped files
        syslog = log_dir / 'syslog'
        syslog_content, syslog_source = self._read_log_with_fallback(syslog, 'syslog', log_dir)
        if syslog_content:
            data['syslog'] = syslog_content
            if syslog_source != 'syslog':
                data['syslog_source'] = syslog_source
        
        # Get historical syslog files
        historical_syslog = self._get_historical_logs(log_dir, 'syslog')
        if historical_syslog:
            data['syslog_historical'] = historical_syslog
        
        # Boot log
        boot_log = log_dir / 'boot.log'
        if boot_log.exists():
            data['boot_log'] = self._tail_file(boot_log, SECONDARY_LOG_LINES)
        
        return data
    
    def _read_log_with_fallback(self, primary_file: Path, base_name: str, log_dir: Path) -> Tuple[Optional[str], str]:
        """
        Read a log file with fallback to rotated/gzipped versions.
        Returns tuple of (content, source_filename).
        """
        # Try primary file first
        if primary_file.exists():
            content = self._tail_file(primary_file, PRIMARY_LOG_LINES)
            if content and content.strip():
                return content, base_name
        
        # Find rotated files and sort by date (newest first)
        rotated_files = self._find_rotated_files(log_dir, base_name)
        
        for rotated_file in rotated_files:
            content = self._read_file_auto(rotated_file, PRIMARY_LOG_LINES)
            if content and content.strip():
                return content, rotated_file.name
        
        return None, ''
    
    def _find_rotated_files(self, log_dir: Path, base_name: str) -> List[Path]:
        """
        Find rotated log files matching the base name, sorted by date (newest first).
        Matches: messages.1, messages-20250713.gz, messages.1.gz, etc.
        """
        if not log_dir.exists():
            return []
        
        rotated = []
        pattern = re.compile(rf'^{re.escape(base_name)}[-.][\d-]+(?:\.gz)?$')
        
        for f in log_dir.iterdir():
            if f.is_file() and pattern.match(f.name):
                rotated.append(f)
        
        # Sort by modification time (newest first) or by name (which often includes date)
        rotated.sort(key=lambda x: x.name, reverse=True)
        
        return rotated
    
    def _get_historical_logs(self, log_dir: Path, base_name: str) -> List[Dict[str, str]]:
        """
        Get list of historical log files with metadata.
        Returns list of dicts with filename and content (limited lines).
        """
        rotated_files = self._find_rotated_files(log_dir, base_name)
        
        historical = []
        for f in rotated_files[:5]:  # Limit to 5 most recent historical files
            content = self._read_file_auto(f, HISTORICAL_LOG_LINES)
            if content and content.strip():
                # Extract date from filename if possible
                date_match = re.search(r'(\d{8})', f.name)
                date_str = date_match.group(1) if date_match else ''
                if date_str:
                    # Format as YYYY-MM-DD
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                historical.append({
                    'filename': f.name,
                    'date': date_str,
                    'content': content,
                    'is_gzipped': f.suffix == '.gz'
                })
        
        return historical
    
    def _read_file_auto(self, file_path: Path, lines: int = None) -> Optional[str]:
        """
        Read a file, automatically handling gzip compression.
        """
        if lines is None:
            lines = DEFAULT_LOG_LINES
        
        try:
            if file_path.suffix == '.gz':
                return self._tail_gzip_file(file_path, lines)
            else:
                return self._tail_file(file_path, lines)
        except Exception as e:
            Logger.warning(f"Failed to read {file_path}: {e}")
            return None
    
    def _tail_gzip_file(self, file_path: Path, lines: int = None) -> str:
        """Read last N lines from a gzipped file using memory-efficient streaming.
        
        Uses a deque with maxlen to only keep the last N lines in memory,
        avoiding loading the entire decompressed file at once.
        """
        if lines is None:
            lines = DEFAULT_LOG_LINES
        try:
            from collections import deque
            
            # Use deque with maxlen to automatically discard old lines
            # This streams through the file keeping only the last N lines
            result_lines = deque(maxlen=lines)
            
            with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    result_lines.append(line)
            
            return ''.join(result_lines)
        except Exception as e:
            Logger.warning(f"Failed to read gzipped file {file_path}: {e}")
            return f"Error reading gzipped file: {e}"
    
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
        """Read last N lines from a file using memory-efficient tail algorithm.
        
        Uses reverse reading from end of file to avoid loading entire file into memory.
        This is critical for large log files (multi-GB) that would cause OOM.
        """
        if lines is None:
            lines = DEFAULT_LOG_LINES
        try:
            from collections import deque
            
            file_size = file_path.stat().st_size
            
            # For small files (< 1MB), just read the whole thing
            if file_size < 1024 * 1024:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return ''.join(tail_lines)
            
            # For larger files, use memory-efficient reverse reading
            # Read in chunks from the end of file
            chunk_size = 8192  # 8KB chunks
            result_lines = deque(maxlen=lines)
            
            with open(file_path, 'rb') as f:
                # Start from end of file
                f.seek(0, 2)  # Seek to end
                remaining_size = f.tell()
                buffer = b''
                
                while remaining_size > 0 and len(result_lines) < lines:
                    # Calculate how much to read
                    read_size = min(chunk_size, remaining_size)
                    remaining_size -= read_size
                    
                    # Seek and read
                    f.seek(remaining_size)
                    chunk = f.read(read_size)
                    buffer = chunk + buffer
                    
                    # Extract complete lines from buffer
                    # Keep incomplete line at start in buffer for next iteration
                    while b'\n' in buffer and len(result_lines) < lines:
                        # Find the last newline
                        last_newline = buffer.rfind(b'\n')
                        if last_newline == len(buffer) - 1:
                            # Newline at end, find the one before it
                            second_last = buffer.rfind(b'\n', 0, last_newline)
                            if second_last != -1:
                                line = buffer[second_last + 1:last_newline + 1]
                                buffer = buffer[:second_last + 1]
                                try:
                                    result_lines.appendleft(line.decode('utf-8', errors='ignore'))
                                except Exception:
                                    pass
                            else:
                                break
                        else:
                            line = buffer[last_newline + 1:]
                            buffer = buffer[:last_newline + 1]
                            if line:
                                try:
                                    result_lines.appendleft(line.decode('utf-8', errors='ignore'))
                                except Exception:
                                    pass
                
                # Handle any remaining buffer content
                if buffer and len(result_lines) < lines:
                    # Process remaining lines in buffer
                    remaining_lines = buffer.decode('utf-8', errors='ignore').split('\n')
                    for line in reversed(remaining_lines):
                        if len(result_lines) >= lines:
                            break
                        if line:
                            result_lines.appendleft(line + '\n')
            
            return ''.join(result_lines)
        except Exception as e:
            Logger.warning(f"Failed to read {file_path}: {e}")
            return f"Error reading file: {e}"
