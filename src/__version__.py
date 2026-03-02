"""Version information for SOSParser."""

import os
from pathlib import Path

def get_version():
    """Get version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except Exception:
        return "unknown"

__version__ = get_version()
