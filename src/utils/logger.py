#!/usr/bin/env python3
"""Logging utilities for SOSReport analyzer"""

import sys
from datetime import datetime
from pathlib import Path


class Logger:
    """Simple logger for console and file output"""
    _debug_enabled = False
    _debug_file = None
    
    @classmethod
    def set_debug(cls, enabled: bool, debug_file_path: str = None):
        """Enable debug logging to file"""
        cls._debug_enabled = enabled
        if enabled and debug_file_path:
            cls._debug_file = Path(debug_file_path)
            cls._debug_file.parent.mkdir(parents=True, exist_ok=True)
    
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
