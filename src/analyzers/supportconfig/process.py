#!/usr/bin/env python3
"""Process analysis for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any, Optional
from .parser import SupportconfigParser
from utils.logger import Logger


class SupportconfigProcess:
    """Analyzer for supportconfig process information."""

    def __init__(self, root_path: Path):
        """
        Initialize process analyzer.

        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze process information from supportconfig.

        Returns:
            Dictionary with process information
        """
        Logger.debug("Analyzing supportconfig process information")
        
        data = {
            'process_tree': self._analyze_process_tree(),
            'process_utilization': self._analyze_process_utilization(),
            'process_io': self._analyze_process_io(),
            'process_handlers': self._analyze_process_handlers(),
            'process_stats': self._analyze_process_stats(),
        }
        
        return data
    
    def _analyze_process_tree(self) -> Dict[str, Any]:
        """Analyze process tree - not directly available in supportconfig"""
        Logger.debug("Analyzing process tree (supportconfig)")
        
        # Process tree is not directly available in supportconfig
        # We could potentially construct it from ps output, but for now return empty
        return {'raw': None, 'available': False, 'note': 'Process tree not available in supportconfig format'}
    
    def _analyze_process_utilization(self) -> Dict[str, Any]:
        """Analyze process utilization from ps output in basic-health-check.txt"""
        Logger.debug("Analyzing process utilization (supportconfig)")
        
        data = {
            'ps_axwwo': None,
            'available': False
        }
        
        # Extract ps command output from basic-health-check.txt
        # The command line is: /bin/ps axwwo user,pid,ppid,%cpu,%mem,vsz,rss,stat,time,cmd
        # The get_command_output method checks if command string is in the command line
        # So 'ps axwwo' should match '/bin/ps axwwo user,pid,...'
        ps_output = self.parser.get_command_output(
            'basic-health-check.txt',
            'ps axwwo'
        )
        
        if ps_output and ps_output.strip():
            data['ps_axwwo'] = ps_output
            data['available'] = True
            Logger.debug(f"Found ps axwwo output in basic-health-check.txt ({len(ps_output)} chars)")
        else:
            Logger.debug("ps axwwo output not found in basic-health-check.txt")
            Logger.debug(f"Root path: {self.root_path}")
            file_path = self.root_path / 'basic-health-check.txt'
            Logger.debug(f"Looking for file: {file_path}")
            if file_path.exists():
                Logger.debug(f"File exists, size: {file_path.stat().st_size} bytes")
            else:
                Logger.debug("File does not exist")
        
        return data
    
    def _analyze_process_io(self) -> Dict[str, Any]:
        """Analyze process IO - not available in supportconfig"""
        Logger.debug("Analyzing process IO (supportconfig)")
        
        # iotop is not typically collected in supportconfig
        return {
            'raw': None,
            'available': False,
            'note': 'Process IO (iotop) not available in supportconfig format'
        }
    
    def _analyze_process_handlers(self) -> Dict[str, Any]:
        """Analyze process handlers from lsof output in open-files.txt"""
        Logger.debug("Analyzing process handlers (supportconfig)")
        
        data = {
            'lsof': None,
            'available': False
        }
        
        # Extract lsof command output from open-files.txt
        # The command line is: /usr/bin/lsof -b -n -l +fg -P -Ki 2>/dev/null
        # The get_command_output method checks if command string is in the command line
        # So 'lsof' should match '/usr/bin/lsof -b -n -l +fg -P -Ki 2>/dev/null'
        lsof_output = self.parser.get_command_output(
            'open-files.txt',
            'lsof'
        )
        
        if lsof_output and lsof_output.strip():
            data['lsof'] = lsof_output
            data['available'] = True
            Logger.debug(f"Found lsof output in open-files.txt ({len(lsof_output)} chars)")
        else:
            Logger.debug("lsof output not found in open-files.txt")
            file_path = self.root_path / 'open-files.txt'
            if file_path.exists():
                Logger.debug(f"File exists, size: {file_path.stat().st_size} bytes")
            else:
                Logger.debug("File does not exist")
        
        return data
    
    def _analyze_process_stats(self) -> Dict[str, Any]:
        """Analyze process stats - pidstat not available in supportconfig"""
        Logger.debug("Analyzing process stats (supportconfig)")
        
        # pidstat is not typically collected in supportconfig
        return {
            'pidstat_all': None,
            'pidstat_tl': None,
            'available': False,
            'note': 'Process stats (pidstat) not available in supportconfig format'
        }
