#!/usr/bin/env python3
"""Process analysis from sosreport"""

from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import Logger
from .pstree_parser import PstreeParser


class ProcessAnalyzer:
    """Analyze process information from sosreport"""
    
    def __init__(self):
        """Initialize the process analyzer."""
        pass
    
    def analyze(self, base_path: Path) -> Dict[str, Any]:
        """
        Analyze process information from sosreport.
        
        Args:
            base_path: Path to extracted sosreport directory
            
        Returns:
            Dictionary with process information
        """
        Logger.debug("Analyzing process information")
        
        process_dir = base_path / 'sos_commands' / 'process'
        
        data = {
            'process_tree': self._analyze_process_tree(process_dir),
            'process_utilization': self._analyze_process_utilization(process_dir),
            'process_io': self._analyze_process_io(process_dir),
            'process_handlers': self._analyze_process_handlers(process_dir),
            'process_stats': self._analyze_process_stats(process_dir),
        }
        
        return data
    
    def _analyze_process_tree(self, process_dir: Path) -> Dict[str, Any]:
        """Analyze process tree from pstree output"""
        Logger.debug("Analyzing process tree")
        
        data = {'raw': None, 'html': None, 'available': False}
        
        # Look for pstree files
        pstree_files = list(process_dir.glob('pstree*')) if process_dir.exists() else []
        
        if pstree_files:
            # Prefer pstree_-lp (most common)
            pstree_file = None
            for f in pstree_files:
                if 'pstree_-lp' in f.name or 'pstree_-l' in f.name:
                    pstree_file = f
                    break
            
            if not pstree_file and pstree_files:
                pstree_file = pstree_files[0]
            
            if pstree_file:
                try:
                    raw_text = pstree_file.read_text()
                    data['raw'] = raw_text
                    data['available'] = True
                    Logger.debug(f"Found process tree file: {pstree_file.name}")
                    
                    # Parse and convert to HTML
                    try:
                        parser = PstreeParser()
                        root_node = parser.parse(raw_text)
                        if root_node:
                            data['html'] = parser.to_html(root_node, max_depth=3)
                            Logger.debug("Successfully parsed process tree to HTML")
                    except Exception as e:
                        Logger.warning(f"Failed to parse process tree to HTML: {e}")
                        # Fall back to raw text if parsing fails
                    
                except Exception as e:
                    Logger.warning(f"Failed to read process tree file {pstree_file}: {e}")
        
        return data
    
    def _analyze_process_utilization(self, process_dir: Path) -> Dict[str, Any]:
        """Analyze process utilization from ps outputs"""
        Logger.debug("Analyzing process utilization")
        
        data = {
            'ps_auxwwwm': None,
            'ps_auxfwww': None,
            'ps_auxwww': None,
            'ps_alxwww': None,
            'ps_elfL': None,
            'available': False
        }
        
        if not process_dir.exists():
            return data
        
        # Try different ps output formats
        ps_files = {
            'ps_auxwwwm': 'ps_auxwwwm',
            'ps_auxfwww': 'ps_auxfwww',
            'ps_auxwww': 'ps_auxwww',
            'ps_alxwww': 'ps_alxwww',
            'ps_elfL': 'ps_-elfL',
        }
        
        for key, pattern in ps_files.items():
            ps_files_found = list(process_dir.glob(f'{pattern}*'))
            if ps_files_found:
                ps_file = ps_files_found[0]
                try:
                    content = ps_file.read_text()
                    data[key] = content
                    data['available'] = True
                    Logger.debug(f"Found {key} file: {ps_file.name}")
                except Exception as e:
                    Logger.warning(f"Failed to read {key} file {ps_file}: {e}")
        
        return data
    
    def _analyze_process_io(self, process_dir: Path) -> Dict[str, Any]:
        """Analyze process IO from iotop output"""
        Logger.debug("Analyzing process IO")
        
        data = {'raw': None, 'available': False, 'error': None}
        
        if not process_dir.exists():
            return data
        
        # Look for iotop files
        iotop_files = list(process_dir.glob('iotop*'))
        
        if iotop_files:
            iotop_file = iotop_files[0]
            try:
                content = iotop_file.read_text()
                # Check if iotop command failed
                if 'failed to run command' in content.lower() or 'no such file' in content.lower():
                    data['error'] = content.strip()
                    Logger.debug("iotop command failed or not available")
                else:
                    data['raw'] = content
                    data['available'] = True
                    Logger.debug(f"Found iotop file: {iotop_file.name}")
            except Exception as e:
                Logger.warning(f"Failed to read iotop file {iotop_file}: {e}")
        
        return data
    
    def _analyze_process_handlers(self, process_dir: Path) -> Dict[str, Any]:
        """Analyze process handlers from lsof output"""
        Logger.debug("Analyzing process handlers")
        
        data = {
            'lsof_M_n_l': None,
            'lsof_M_n_l_c': None,
            'available': False
        }
        
        if not process_dir.exists():
            return data
        
        # Look for lsof files
        lsof_files = list(process_dir.glob('lsof*'))
        
        for lsof_file in lsof_files:
            try:
                content = lsof_file.read_text()
                
                # Determine which lsof file this is
                if 'lsof_M_-n_-l_-c' in lsof_file.name:
                    data['lsof_M_n_l_c'] = content
                    data['available'] = True
                    Logger.debug(f"Found lsof file (with -c): {lsof_file.name}")
                elif 'lsof_M_-n_-l' in lsof_file.name or 'lsof_M_n_l' in lsof_file.name:
                    data['lsof_M_n_l'] = content
                    data['available'] = True
                    Logger.debug(f"Found lsof file: {lsof_file.name}")
            except Exception as e:
                Logger.warning(f"Failed to read lsof file {lsof_file}: {e}")
        
        return data
    
    def _analyze_process_stats(self, process_dir: Path) -> Dict[str, Any]:
        """Analyze process stats from pidstat output"""
        Logger.debug("Analyzing process stats")
        
        data = {
            'pidstat_all': None,
            'pidstat_tl': None,
            'available': False
        }
        
        if not process_dir.exists():
            return data
        
        # Look for pidstat files
        pidstat_files = list(process_dir.glob('pidstat*'))
        
        for pidstat_file in pidstat_files:
            try:
                content = pidstat_file.read_text()
                
                # Determine which pidstat file this is
                if 'pidstat_-p_ALL' in pidstat_file.name or 'pidstat_-p_ALL' in pidstat_file.name:
                    data['pidstat_all'] = content
                    data['available'] = True
                    Logger.debug(f"Found pidstat file (all processes): {pidstat_file.name}")
                elif 'pidstat_-tl' in pidstat_file.name or 'pidstat_tl' in pidstat_file.name:
                    data['pidstat_tl'] = content
                    data['available'] = True
                    Logger.debug(f"Found pidstat file (threads): {pidstat_file.name}")
            except Exception as e:
                Logger.warning(f"Failed to read pidstat file {pidstat_file}: {e}")
        
        return data
