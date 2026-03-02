"""
Supportconfig Cloud Data Reader

Reads cloud-related data files from supportconfig.
"""

from typing import Dict, Any
from pathlib import Path


class CloudDataReader:
    """Analyzer for reading cloud data files."""

    def __init__(self, root_path: Path):
        """Initialize with root path."""
        self.root_path = root_path

    def analyze(self) -> Dict[str, Any]:
        """Read cloud data files."""
        public_cloud_dir = self.root_path / 'public_cloud'
        data = {}

        def read_optional(path: Path, limit: int = 5000):
            """Read file with limit - reads only up to limit bytes, not entire file."""
            try:
                if not path.exists():
                    return None
                # Read only what we need - don't load entire file!
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(limit)
            except Exception:
                return None

        data['metadata'] = read_optional(public_cloud_dir / 'metadata.txt', 5000)
        data['instanceinit'] = read_optional(public_cloud_dir / 'instanceinit.txt', 5000)
        data['hosts'] = read_optional(public_cloud_dir / 'hosts.txt', 4000)
        data['cloudregister'] = read_optional(public_cloud_dir / 'cloudregister.txt', 4000)
        data['credentials'] = read_optional(public_cloud_dir / 'credentials.txt', 2000)
        data['osrelease'] = read_optional(public_cloud_dir / 'osrelease.txt', 1000)

        return data
