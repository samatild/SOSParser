"""
Supportconfig Cloud Provider Detector

Detects cloud provider from supportconfig data.
"""

from typing import Optional
from pathlib import Path


class ProviderDetector:
    """Analyzer for detecting cloud provider."""

    def __init__(self, root_path: Path):
        """Initialize with root path."""
        self.root_path = root_path

    def analyze(self) -> Optional[str]:
        """Detect cloud provider from metadata files."""
        public_cloud_dir = self.root_path / 'public_cloud'
        if not public_cloud_dir.exists():
            return None

        def read_optional(path: Path, limit: int = 5000):
            """Read file with proper size limit - doesn't load entire file first."""
            try:
                if not path.exists():
                    return None
                # Read only up to limit bytes - memory efficient
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(limit)
            except Exception:
                return None

        metadata = read_optional(public_cloud_dir / 'metadata.txt', 5000)
        instanceinit = read_optional(public_cloud_dir / 'instanceinit.txt', 5000)
        hosts_pc = read_optional(public_cloud_dir / 'hosts.txt', 4000)
        cloudregister = read_optional(public_cloud_dir / 'cloudregister.txt', 4000)

        provider = None
        for blob in (metadata, instanceinit, cloudregister, hosts_pc):
            if blob and 'azure' in blob.lower():
                provider = 'azure'
                break

        return provider or 'unknown'
