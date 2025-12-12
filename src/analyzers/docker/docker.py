#!/usr/bin/env python3
"""Parse docker data captured under sos_commands/docker."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class DockerCommandsAnalyzer:
    """
    Collect docker/container runtime information from sos_commands/docker.

    The sosreport docker plugin records command output into individual files
    (docker ps, docker images, docker info, etc.). This analyzer normalizes
    the most useful artifacts into structured data for the report.
    """

    def __init__(self, root_path: Path):
        root = Path(root_path)
        docker_dir = root / 'sos_commands' / 'docker'
        self.docker_dir: Optional[Path] = docker_dir if docker_dir.is_dir() else None

    def analyze(self) -> Dict[str, Any]:
        """Return parsed docker information, if available."""
        if not self.docker_dir:
            return {}

        data: Dict[str, Any] = {}

        version = self._read_text('docker_version')
        if version:
            data['version'] = version

        info = self._read_text('docker_info', limit=20000)
        if info:
            data['info'] = info

        ps = self._parse_table_file('docker_ps')
        if ps:
            data['ps'] = ps

        ps_all = self._parse_table_file('docker_ps_-a')
        if ps_all:
            data['ps_all'] = ps_all

        images = self._parse_table_file('docker_images')
        if images:
            data['images'] = images

        stats = self._parse_table_glob('docker_stats*')
        if stats:
            data['stats'] = stats

        events = self._read_text_glob('docker_events*', limit=8000)
        if events:
            data['events'] = events

        networks = self._parse_table_file('docker_network_ls')
        if networks:
            data['networks'] = networks

        volumes = self._parse_table_file('docker_volume_ls')
        if volumes:
            data['volumes'] = volumes

        network_inspect = self._parse_network_inspect()
        if network_inspect:
            data['network_inspect'] = network_inspect

        container_inspect = self._collect_container_inspect()
        if container_inspect:
            data['container_inspect'] = container_inspect

        image_inspect = self._collect_image_inspect()
        if image_inspect:
            data['image_inspect'] = image_inspect

        journal = self._read_text_glob('journalctl*docker*', limit=10000)
        if journal:
            data['journal'] = journal

        config_listing = self._read_text_glob('ls*docker*', limit=10000)
        if config_listing:
            data['config_listing'] = config_listing

        return data

    # ------------------------------------------------------------------
    # Helpers

    def _read_text(self, filename: str, limit: Optional[int] = None) -> str:
        """Read a file inside sos_commands/docker."""
        if not self.docker_dir:
            return ''
        path = self.docker_dir / filename
        if not path.is_file():
            return ''
        return self._safe_read(path, limit)

    def _read_text_glob(self, pattern: str, limit: Optional[int] = None) -> str:
        """Read first file matching glob pattern."""
        path = self._first_matching_path(pattern)
        return self._safe_read(path, limit) if path else ''

    def _safe_read(self, path: Path, limit: Optional[int]) -> str:
        try:
            text = path.read_text(encoding='utf-8', errors='ignore').strip()
            if limit is not None:
                return text[:limit]
            return text
        except Exception:
            return ''

    def _first_matching_path(self, pattern: str) -> Optional[Path]:
        if not self.docker_dir:
            return None
        for candidate in sorted(self.docker_dir.glob(pattern)):
            if candidate.is_file():
                return candidate
        return None

    def _parse_table_file(self, filename: str, max_rows: int = 50) -> Optional[Dict[str, Any]]:
        """Parse whitespace-delimited tables (docker ps/images/etc)."""
        if not self.docker_dir:
            return None
        path = self.docker_dir / filename
        if not path.is_file():
            return None
        return self._parse_table_from_path(path, max_rows)

    def _parse_table_glob(self, pattern: str, max_rows: int = 50) -> Optional[Dict[str, Any]]:
        path = self._first_matching_path(pattern)
        if not path:
            return None
        return self._parse_table_from_path(path, max_rows)

    def _parse_table_from_path(self, path: Path, max_rows: int) -> Optional[Dict[str, Any]]:
        try:
            lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            return None

        clean_lines = [line.rstrip() for line in lines if line.strip()]
        if not clean_lines:
            return None

        header = re.split(r'\s{2,}', clean_lines[0].strip())
        # If only one column is detected, keep raw output for rendering.
        if len(header) <= 1 and len(clean_lines) == 1:
            return {'raw': clean_lines[0]}

        rows: List[List[str]] = []
        for line in clean_lines[1:]:
            cells = re.split(r'\s{2,}', line.strip())
            if cells:
                rows.append(cells)
            if len(rows) >= max_rows:
                break

        return {'headers': header, 'rows': rows}

    def _parse_network_inspect(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        if not self.docker_dir:
            return entries

        for path in sorted(self.docker_dir.glob('docker_network_inspect_*')):
            summary = self._summarize_network_inspect(path)
            if summary:
                entries.append(summary)
        return entries

    def _summarize_network_inspect(self, path: Path) -> Optional[Dict[str, Any]]:
        name = path.name.replace('docker_network_inspect_', '', 1)
        text = self._safe_read(path, limit=8000)
        if not text:
            return None

        try:
            payload = json.loads(text)
            if isinstance(payload, list) and payload:
                payload = payload[0]
        except Exception:
            return {'name': name, 'raw': text}

        if not isinstance(payload, dict):
            return {'name': name, 'raw': text}

        ipam = payload.get('IPAM') or {}
        ipam_cfg = ipam.get('Config') or []
        subnet = ', '.join(filter(None, [cfg.get('Subnet') for cfg in ipam_cfg if isinstance(cfg, dict)]))
        gateway = ', '.join(filter(None, [cfg.get('Gateway') for cfg in ipam_cfg if isinstance(cfg, dict)]))
        containers = payload.get('Containers') or {}

        return {
            'name': payload.get('Name') or name,
            'id': payload.get('Id'),
            'driver': payload.get('Driver'),
            'scope': payload.get('Scope'),
            'internal': payload.get('Internal'),
            'attachable': payload.get('Attachable'),
            'subnet': subnet or None,
            'gateway': gateway or None,
            'containers': len(containers) if isinstance(containers, dict) else None,
        }

    def _collect_container_inspect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if not self.docker_dir:
            return result
        inspect_dir = self.docker_dir / 'containers'
        if not inspect_dir.is_dir():
            return result

        structured: List[Dict[str, Any]] = []
        raw_entries: List[Dict[str, Any]] = []

        for idx, path in enumerate(sorted(inspect_dir.glob('*'))):
            if idx >= 40:
                break
            if not path.is_file():
                continue
            summary = self._summarize_container_inspect(path)
            if summary:
                if 'raw' in summary:
                    raw_entries.append(summary)
                else:
                    structured.append(summary)

        if structured:
            result['entries'] = structured
        if raw_entries:
            result['raw'] = raw_entries
        return result

    def _summarize_container_inspect(self, path: Path) -> Optional[Dict[str, Any]]:
        text = self._safe_read(path, limit=12000)
        if not text:
            return None

        try:
            payload = json.loads(text)
            if isinstance(payload, list) and payload:
                payload = payload[0]
        except Exception:
            return {'source': path.name, 'raw': text}

        if not isinstance(payload, dict):
            return {'source': path.name, 'raw': text}

        state = payload.get('State') or {}
        net_settings = payload.get('NetworkSettings') or {}
        name = (payload.get('Name') or '').lstrip('/')
        image = payload.get('Config', {}).get('Image') or payload.get('Image')
        ip_addr = net_settings.get('IPAddress') or self._primary_network_ip(net_settings.get('Networks'))

        summary: Dict[str, Any] = {
            'source': path.name,
            'name': name or path.stem,
            'id': payload.get('Id'),
            'image': image,
            'created': payload.get('Created'),
            'state': state.get('Status'),
            'running': state.get('Running'),
            'started_at': state.get('StartedAt'),
            'finished_at': state.get('FinishedAt'),
            'restart_count': state.get('RestartCount'),
            'ip_address': ip_addr,
            'ports': self._format_ports(net_settings.get('Ports')),
        }

        # Drop empty keys to avoid clutter.
        return {k: v for k, v in summary.items() if v not in (None, '', [])}

    def _collect_image_inspect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if not self.docker_dir:
            return result
        inspect_dir = self.docker_dir / 'images'
        if not inspect_dir.is_dir():
            return result

        structured: List[Dict[str, Any]] = []
        raw_entries: List[Dict[str, Any]] = []

        for idx, path in enumerate(sorted(inspect_dir.glob('*'))):
            if idx >= 40:
                break
            if not path.is_file():
                continue
            summary = self._summarize_image_inspect(path)
            if summary:
                if 'raw' in summary:
                    raw_entries.append(summary)
                else:
                    structured.append(summary)

        if structured:
            result['entries'] = structured
        if raw_entries:
            result['raw'] = raw_entries
        return result

    def _summarize_image_inspect(self, path: Path) -> Optional[Dict[str, Any]]:
        text = self._safe_read(path, limit=8000)
        if not text:
            return None

        try:
            payload = json.loads(text)
            if isinstance(payload, list) and payload:
                payload = payload[0]
        except Exception:
            return {'source': path.name, 'raw': text}

        if not isinstance(payload, dict):
            return {'source': path.name, 'raw': text}

        summary: Dict[str, Any] = {
            'source': path.name,
            'id': payload.get('Id'),
            'repo_tags': ', '.join(payload.get('RepoTags', [])[:5]) if payload.get('RepoTags') else None,
            'created': payload.get('Created'),
            'size': self._format_bytes(payload.get('Size')),
            'architecture': payload.get('Architecture'),
            'os': payload.get('Os'),
        }
        return {k: v for k, v in summary.items() if v not in (None, '', [])}

    def _primary_network_ip(self, networks: Any) -> Optional[str]:
        if isinstance(networks, dict):
            for net in networks.values():
                if isinstance(net, dict) and net.get('IPAddress'):
                    return net.get('IPAddress')
        return None

    def _format_ports(self, ports: Any) -> Optional[str]:
        if isinstance(ports, dict):
            render: List[str] = []
            for container_port, host_entries in ports.items():
                if not host_entries:
                    render.append(str(container_port))
                    continue
                if isinstance(host_entries, list):
                    host_text = ','.join(
                        f"{entry.get('HostIp', '')}:{entry.get('HostPort', '')}"
                        for entry in host_entries if isinstance(entry, dict)
                    )
                else:
                    host_text = str(host_entries)
                render.append(f"{host_text}->{container_port}")
            return ', '.join(render)
        return None

    def _format_bytes(self, value: Any) -> Optional[str]:
        try:
            num = int(value)
        except (TypeError, ValueError):
            return value if value else None
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        size = float(num)
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}EB"
