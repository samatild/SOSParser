#!/usr/bin/env python3
"""Format detection utility for sosreport and supportconfig files."""

from pathlib import Path
from typing import Literal, Optional

FormatType = Literal['sosreport', 'supportconfig', 'unknown']


def detect_format(extracted_path: Path) -> FormatType:
    """
    Detect if the extracted archive is a sosreport or supportconfig.
    
    Args:
        extracted_path: Path to the extracted directory
        
    Returns:
        'sosreport', 'supportconfig', or 'unknown'
    """
    if not extracted_path.exists() or not extracted_path.is_dir():
        return 'unknown'
    
    # Check for supportconfig indicators
    supportconfig_markers = [
        'supportconfig.txt',
        'basic-environment.txt',
        'basic-health-check.txt',
    ]
    
    for marker in supportconfig_markers:
        if (extracted_path / marker).exists():
            return 'supportconfig'
    
    # Check for sosreport indicators
    sosreport_markers = [
        'sos_commands',
        'sos_reports',
        'proc',
        'sys',
        'etc'
    ]
    
    # Check if at least 3 sosreport markers exist
    sosreport_count = sum(1 for marker in sosreport_markers 
                          if (extracted_path / marker).exists())
    
    if sosreport_count >= 3:
        return 'sosreport'
    
    # Additional check: look for nested sosreport directory
    # Sometimes sosreports extract to a subdirectory
    subdirs = [d for d in extracted_path.iterdir() if d.is_dir()]
    if len(subdirs) == 1:
        subdir = subdirs[0]
        # Recursive check on subdirectory
        sosreport_count = sum(1 for marker in sosreport_markers 
                              if (subdir / marker).exists())
        if sosreport_count >= 3:
            return 'sosreport'
    
    return 'unknown'


def get_format_info(format_type: FormatType) -> dict:
    """
    Get human-readable information about the format.
    
    Args:
        format_type: The detected format type
        
    Returns:
        Dictionary with format information
    """
    format_info = {
        'sosreport': {
            'name': 'SOSReport',
            'description': 'Red Hat sosreport diagnostic bundle',
            'vendor': 'Red Hat',
            'supported_os': ['RHEL', 'CentOS', 'Fedora', 'Ubuntu'],
        },
        'supportconfig': {
            'name': 'Supportconfig',
            'description': 'SUSE supportconfig diagnostic bundle',
            'vendor': 'SUSE',
            'supported_os': ['SLES', 'openSUSE'],
        },
        'unknown': {
            'name': 'Unknown',
            'description': 'Unknown or unsupported format',
            'vendor': 'Unknown',
            'supported_os': [],
        }
    }
    
    return format_info.get(format_type, format_info['unknown'])
