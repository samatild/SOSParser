#!/usr/bin/env python3
"""Logging utilities for SOSReport analyzer"""

import sys
import os
from datetime import datetime
from pathlib import Path


def _get_memory_stats() -> dict:
    """
    Get process memory stats from /proc/self/status (Linux).
    
    Returns dict with:
        - rss: Current Resident Set Size (RAM actually used now)
        - peak: VmHWM - High Water Mark (peak RSS since process start)
        - virtual: VmSize - Total virtual memory allocated
    """
    stats = {'rss': 0.0, 'peak': 0.0, 'virtual': 0.0}
    
    try:
        # Try Linux /proc filesystem (most accurate for containers)
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    # Current resident set size in kB
                    stats['rss'] = int(line.split()[1]) / 1024.0
                elif line.startswith('VmHWM:'):
                    # High Water Mark - peak RSS since process start
                    stats['peak'] = int(line.split()[1]) / 1024.0
                elif line.startswith('VmSize:'):
                    # Total virtual memory
                    stats['virtual'] = int(line.split()[1]) / 1024.0
        return stats
    except (FileNotFoundError, PermissionError):
        pass
    
    # Fallback to psutil if available
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        stats['rss'] = mem.rss / 1024 / 1024
        stats['peak'] = getattr(mem, 'peak_wset', mem.rss) / 1024 / 1024  # Windows has peak_wset
        stats['virtual'] = mem.vms / 1024 / 1024
        return stats
    except ImportError:
        pass
    
    return stats


def _get_memory_mb() -> float:
    """Get current process RSS memory usage in MB (backward compat)."""
    return _get_memory_stats()['rss']


class Logger:
    """Simple logger for console and file output"""
    _debug_enabled = False
    _debug_file = None
    _memory_tracking_enabled = False
    _last_memory_mb = 0.0
    
    @classmethod
    def set_debug(cls, enabled: bool, debug_file_path: str = None):
        """Enable debug logging to file"""
        cls._debug_enabled = enabled
        if enabled and debug_file_path:
            cls._debug_file = Path(debug_file_path)
            cls._debug_file.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def enable_memory_tracking(cls, enabled: bool = True):
        """Enable memory usage tracking in debug logs."""
        cls._memory_tracking_enabled = enabled
        if enabled:
            stats = _get_memory_stats()
            cls._last_memory_mb = stats['rss']
            cls._initial_peak_mb = stats['peak']
            cls.debug(f"[MEMORY] Tracking enabled. RSS: {stats['rss']:.1f} MB, Peak: {stats['peak']:.1f} MB")
    
    @classmethod
    def _log(cls, level: str, message: str):
        """Internal log method"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        # Always print to console with flush for Kubernetes log streaming
        print(log_msg, file=sys.stderr if level == "ERROR" else sys.stdout, flush=True)
        
        # Write to debug file if enabled
        if cls._debug_enabled and cls._debug_file:
            try:
                with open(cls._debug_file, 'a', encoding='utf-8') as f:
                    f.write(log_msg + '\n')
            except Exception:
                pass
    
    @classmethod
    def info(cls, message: str):
        """Log info message"""
        cls._log("INFO", message)
    
    @classmethod
    def debug(cls, message: str):
        """Log debug message (only if debug enabled)"""
        if cls._debug_enabled:
            cls._log("DEBUG", message)
    
    @classmethod
    def warning(cls, message: str):
        """Log warning message"""
        cls._log("WARNING", message)
    
    @classmethod
    def error(cls, message: str):
        """Log error message"""
        cls._log("ERROR", message)
    
    @classmethod
    def memory(cls, phase: str):
        """
        Log memory usage for a specific phase (only when debug + memory tracking enabled).
        
        Shows:
        - RSS: Current resident memory (RAM used right now)
        - Peak: High water mark since process start (catches transient spikes)
        - Delta: Change from last checkpoint
        
        Use this to identify memory spikes during analysis.
        """
        if not cls._debug_enabled or not cls._memory_tracking_enabled:
            return
        
        stats = _get_memory_stats()
        current_rss = stats['rss']
        current_peak = stats['peak']
        
        delta_rss = current_rss - cls._last_memory_mb
        delta_sign = "+" if delta_rss >= 0 else ""
        
        # Check if peak increased (indicates a spike happened even if RSS dropped)
        initial_peak = getattr(cls, '_initial_peak_mb', current_peak)
        peak_increase = current_peak - initial_peak
        
        # Format: RSS (delta) | Peak +increase
        msg = f"{phase}: RSS {current_rss:.1f} MB ({delta_sign}{delta_rss:.1f}) | Peak {current_peak:.1f} MB"
        if peak_increase > 1:  # Only show if peak increased by more than 1MB
            msg += f" (+{peak_increase:.1f} since start)"
        
        cls._log("MEMORY", msg)
        cls._last_memory_mb = current_rss
