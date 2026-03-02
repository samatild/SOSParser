#!/usr/bin/env python3
"""Cloud analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any, Optional
from .cloud_analyzers.provider_detector import ProviderDetector
from .cloud_analyzers.cloud_data_reader import CloudDataReader
from utils.logger import Logger


class SupportconfigCloud:
    """Analyzer for supportconfig cloud information."""

    def __init__(self, root_path: Path):
        """
        Initialize cloud analyzer.

        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path

    def analyze(self) -> Dict[str, Any] | None:
        """
        Analyze cloud information from supportconfig.

        Returns:
            Dictionary with cloud information or None if no cloud detected
        """
        Logger.memory("  Cloud: start")
        
        public_cloud_dir = self.root_path / 'public_cloud'
        if not public_cloud_dir.exists():
            Logger.memory("  Cloud: no public_cloud dir, skipping")
            return None

        # Detect provider
        provider_detector = ProviderDetector(self.root_path)
        provider = provider_detector.analyze()
        Logger.memory("  Cloud: provider detected")

        # Read cloud data
        data_reader = CloudDataReader(self.root_path)
        cloud_data = data_reader.analyze()
        Logger.memory("  Cloud: data read")

        cloud = {}
        cloud['provider'] = provider or 'unknown'
        cloud['virtualization'] = {}
        cloud['cloud_init'] = {}
        if cloud_data.get('instanceinit'):
            cloud['cloud_init']['cloud_status'] = cloud_data['instanceinit']

        # Add provider-specific data
        if provider == 'azure':
            cloud['azure'] = {
                'metadata': cloud_data.get('metadata'),
                'hosts': cloud_data.get('hosts'),
                'cloudregister': cloud_data.get('cloudregister'),
                'credentials': cloud_data.get('credentials'),
                'osrelease': cloud_data.get('osrelease'),
            }
        else:
            cloud['azure'] = {}

        return cloud
