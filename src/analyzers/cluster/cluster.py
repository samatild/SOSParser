#!/usr/bin/env python3
"""Cluster (Pacemaker/Corosync) analysis from sosreport"""

import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.logger import Logger


# Byte cap for cluster log files (journal.log, events.txt, etc.)
MAX_CLUSTER_LOG_BYTES = int(os.environ.get('MAX_CLUSTER_LOG_BYTES', str(5 * 1024 * 1024)))  # 5 MB


class ClusterAnalyzer:
    """Analyze Pacemaker/Corosync cluster information from sosreport"""

    def __init__(self):
        pass

    def analyze(self, base_path: Path) -> Dict[str, Any]:
        """
        Analyze cluster information from sosreport.

        Args:
            base_path: Path to extracted sosreport directory

        Returns:
            Dictionary with cluster information, or dict with available=False
        """
        Logger.debug("Analyzing cluster information")

        pacemaker_dir = base_path / 'sos_commands' / 'pacemaker'
        corosync_dir = base_path / 'sos_commands' / 'corosync'

        # Quick availability check — need at least pacemaker dir with pcs_status
        pcs_status_file = pacemaker_dir / 'pcs_status_--full'
        if not pcs_status_file.exists():
            pcs_status_file = pacemaker_dir / 'pcs_status'
        if not pcs_status_file.exists():
            Logger.debug("No pcs_status found, skipping cluster analysis")
            return {'available': False}

        pcs_status_raw = self._read_file_safe(pcs_status_file)
        if not pcs_status_raw:
            return {'available': False}

        # Parse the structured data
        data = {
            'available': True,
            **self._parse_pcs_status(pcs_status_raw),
            'pcs_status_raw': pcs_status_raw,
        }

        # Quorum
        data['quorum'] = self._parse_quorum(pacemaker_dir, corosync_dir)

        # Fencing / STONITH
        data['fencing'] = self._parse_fencing(pacemaker_dir)

        # Cluster properties
        props_file = pacemaker_dir / 'pcs_property_config_--all'
        if not props_file.exists():
            props_file = pacemaker_dir / 'pcs_property_list_--all'
        data['properties'] = self._read_file_safe(props_file) or ''

        # Corosync configuration & status
        data['corosync'] = self._parse_corosync(base_path, corosync_dir)

        # Cluster logs for LogViewer
        data['logs'] = self._collect_cluster_logs(pacemaker_dir)

        return data

    # ------------------------------------------------------------------
    # pcs status parsing
    # ------------------------------------------------------------------

    def _parse_pcs_status(self, raw: str) -> Dict[str, Any]:
        """Parse pcs_status --full output into structured data."""
        result: Dict[str, Any] = {
            'cluster_name': '',
            'stack': '',
            'dc_node': '',
            'pacemaker_version': '',
            'last_updated': '',
            'last_change': '',
            'nodes_configured': 0,
            'resources_configured': 0,
            'nodes': [],
            'resources': [],
            'resource_groups': [],
            'clone_sets': [],
            'node_attributes': {},
            'migration_summary': '',
            'pcsd_status': [],
            'daemon_status': [],
            'warnings': '',
        }

        # Cluster name
        m = re.search(r'^Cluster name:\s*(.+)', raw, re.MULTILINE)
        if m:
            result['cluster_name'] = m.group(1).strip()

        # Warnings block
        warn_m = re.search(r'^WARNINGS:\n(.*?)(?=\nCluster Summary:|\nStack:)', raw, re.DOTALL | re.MULTILINE)
        if warn_m:
            result['warnings'] = warn_m.group(1).strip()

        # Stack & pacemaker state
        m = re.search(r'\*\s*Stack:\s*(\S+)\s*\((.+?)\)', raw)
        if m:
            result['stack'] = m.group(1)

        # DC node
        m = re.search(r'\*\s*Current DC:\s*(\S+)\s*\((\d+)\)\s*\(version\s+([^)]+)\)', raw)
        if m:
            result['dc_node'] = m.group(1)
            result['pacemaker_version'] = m.group(3)

        # Last updated / last change
        m = re.search(r'\*\s*Last updated:\s*(.+?)(?:\s+on\s+\S+)?$', raw, re.MULTILINE)
        if m:
            result['last_updated'] = m.group(1).strip()
        m = re.search(r'\*\s*Last change:\s*(.+?)(?:\s+by\s+)', raw)
        if m:
            result['last_change'] = m.group(1).strip()

        # Nodes/resources configured
        m = re.search(r'\*\s*(\d+)\s+nodes?\s+configured', raw)
        if m:
            result['nodes_configured'] = int(m.group(1))
        m = re.search(r'\*\s*(\d+)\s+resource instances?\s+configured', raw)
        if m:
            result['resources_configured'] = int(m.group(1))

        # Node list
        for m in re.finditer(
            r'\*\s*Node\s+(\S+)\s+\((\d+)\):\s*(\S+)',
            raw,
        ):
            result['nodes'].append({
                'name': m.group(1),
                'id': m.group(2),
                'status': m.group(3).rstrip(','),
            })

        # Resources — parse groups, clones, and primitives
        self._parse_resources(raw, result)

        # Node attributes
        attr_section = re.search(
            r'Node Attributes:\n(.*?)(?=\nMigration Summary:|\nTickets:|\nPCSD Status:|\Z)',
            raw, re.DOTALL
        )
        if attr_section:
            current_node = None
            for line in attr_section.group(1).splitlines():
                node_m = re.match(r'\s*\*\s*Node:\s*(\S+)', line)
                if node_m:
                    current_node = node_m.group(1)
                    result['node_attributes'][current_node] = {}
                elif current_node:
                    attr_m = re.match(r'\s*\*\s*(\S+)\s*:\s*(.+)', line)
                    if attr_m:
                        result['node_attributes'][current_node][attr_m.group(1)] = attr_m.group(2).strip()

        # Migration summary
        mig_section = re.search(
            r'Migration Summary:\n(.*?)(?=\nTickets:|\nPCSD Status:|\Z)',
            raw, re.DOTALL
        )
        if mig_section:
            result['migration_summary'] = mig_section.group(1).strip()

        # PCSD status
        pcsd_section = re.search(r'PCSD Status:\n(.*?)(?=\nDaemon Status:|\Z)', raw, re.DOTALL)
        if pcsd_section:
            for line in pcsd_section.group(1).strip().splitlines():
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    result['pcsd_status'].append({
                        'node': parts[0].strip(),
                        'status': parts[1].strip(),
                    })

        # Daemon status
        daemon_section = re.search(r'Daemon Status:\n(.*?)$', raw, re.DOTALL)
        if daemon_section:
            for line in daemon_section.group(1).strip().splitlines():
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    result['daemon_status'].append({
                        'name': parts[0].strip(),
                        'status': parts[1].strip(),
                    })

        return result

    def _parse_resources(self, raw: str, result: Dict[str, Any]):
        """Parse the Full List of Resources section."""
        res_section = re.search(
            r'Full List of Resources:\n(.*?)(?=\nNode Attributes:|\nMigration Summary:|\nTickets:|\nPCSD Status:|\Z)',
            raw, re.DOTALL
        )
        if not res_section:
            return

        lines = res_section.group(1).splitlines()
        i = 0
        current_group = None
        current_clone = None

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Resource Group
            group_m = re.match(r'\s*\*\s*Resource Group:\s*(\S+):', stripped)
            if group_m:
                current_group = group_m.group(1)
                current_clone = None
                group_entry = {'name': current_group, 'resources': []}
                result['resource_groups'].append(group_entry)
                i += 1
                continue

            # Clone Set
            clone_m = re.match(r'\s*\*\s*Clone Set:\s*(\S+)\s+\[(\S+)\]:', stripped)
            if clone_m:
                current_clone = clone_m.group(1)
                current_group = None
                clone_entry = {
                    'name': current_clone,
                    'resource_id': clone_m.group(2),
                    'instances': [],
                }
                result['clone_sets'].append(clone_entry)
                i += 1
                continue

            # Individual resource line
            res_m = re.match(
                r'\s*\*?\s*(\S+)\s+\(([^)]+)\):\s+(\S+)\s*(.*)',
                stripped
            )
            if res_m:
                res_entry = {
                    'id': res_m.group(1),
                    'type': res_m.group(2),
                    'status': res_m.group(3),
                    'node': res_m.group(4).strip() if res_m.group(4) else '',
                    'group': None,
                    'clone': None,
                }
                if current_group:
                    res_entry['group'] = current_group
                    result['resource_groups'][-1]['resources'].append(res_entry)
                elif current_clone:
                    res_entry['clone'] = current_clone
                    result['clone_sets'][-1]['instances'].append(res_entry)

                result['resources'].append(res_entry)

            # Blank or unmatched lines reset context (at top-level indent)
            if stripped == '' or (stripped.startswith('*') and not group_m and not clone_m and not res_m):
                if not stripped.startswith('    '):
                    current_group = None
                    current_clone = None

            i += 1

    # ------------------------------------------------------------------
    # Quorum
    # ------------------------------------------------------------------

    def _parse_quorum(self, pacemaker_dir: Path, corosync_dir: Path) -> Dict[str, Any]:
        """Parse quorum information from pcs or corosync-quorumtool."""
        quorum: Dict[str, Any] = {
            'available': False,
            'provider': '',
            'nodes': 0,
            'expected_votes': 0,
            'total_votes': 0,
            'quorum_votes': 0,
            'quorate': False,
            'members': [],
        }

        # Prefer pcs_quorum_status, fall back to corosync-quorumtool
        raw = None
        for f in [
            pacemaker_dir / 'pcs_quorum_status',
            corosync_dir / 'corosync-quorumtool_-s',
        ]:
            raw = self._read_file_safe(f)
            if raw:
                break

        if not raw:
            return quorum

        quorum['available'] = True

        m = re.search(r'Quorum provider:\s*(\S+)', raw)
        if m:
            quorum['provider'] = m.group(1)
        m = re.search(r'Nodes:\s*(\d+)', raw)
        if m:
            quorum['nodes'] = int(m.group(1))
        m = re.search(r'Expected votes:\s*(\d+)', raw)
        if m:
            quorum['expected_votes'] = int(m.group(1))
        m = re.search(r'Total votes:\s*(\d+)', raw)
        if m:
            quorum['total_votes'] = int(m.group(1))
        m = re.search(r'Quorum:\s*(\d+)', raw)
        if m:
            quorum['quorum_votes'] = int(m.group(1))
        m = re.search(r'Quorate:\s*(Yes|No)', raw, re.IGNORECASE)
        if m:
            quorum['quorate'] = m.group(1).lower() == 'yes'

        # Membership
        for m in re.finditer(r'^\s+(\d+)\s+(\d+)\s+(\S+)', raw, re.MULTILINE):
            quorum['members'].append({
                'nodeid': m.group(1),
                'votes': m.group(2),
                'name': m.group(3),
            })

        return quorum

    # ------------------------------------------------------------------
    # Fencing / STONITH
    # ------------------------------------------------------------------

    def _parse_fencing(self, pacemaker_dir: Path) -> Dict[str, Any]:
        """Parse STONITH/SBD fencing information."""
        fencing: Dict[str, Any] = {
            'available': False,
            'devices': [],
            'sbd_status': '',
            'sbd_watchdog': '',
            'history': '',
        }

        # STONITH devices — extract from pcs_status resources already parsed,
        # but also get SBD/history from dedicated files
        sbd_file = pacemaker_dir / 'pcs_stonith_sbd_status_--full'
        fencing['sbd_status'] = self._read_file_safe(sbd_file) or ''

        watchdog_file = pacemaker_dir / 'pcs_stonith_sbd_watchdog_list'
        fencing['sbd_watchdog'] = self._read_file_safe(watchdog_file) or ''

        history_file = pacemaker_dir / 'pcs_stonith_history_show'
        fencing['history'] = self._read_file_safe(history_file) or ''

        if fencing['sbd_status'] or fencing['history']:
            fencing['available'] = True

        return fencing

    # ------------------------------------------------------------------
    # Corosync
    # ------------------------------------------------------------------

    def _parse_corosync(self, base_path: Path, corosync_dir: Path) -> Dict[str, Any]:
        """Parse corosync configuration and status."""
        corosync: Dict[str, Any] = {
            'available': False,
            'config': '',
            'ring_status': '',
            'transport': '',
            'cluster_name': '',
            'nodes': [],
        }

        # corosync.conf — prefer /etc/corosync/corosync.conf
        conf_file = base_path / 'etc' / 'corosync' / 'corosync.conf'
        raw_conf = self._read_file_safe(conf_file) or ''
        corosync['config'] = raw_conf

        if raw_conf:
            corosync['available'] = True
            # Parse transport
            m = re.search(r'transport:\s*(\S+)', raw_conf)
            if m:
                corosync['transport'] = m.group(1)
            # Parse cluster name
            m = re.search(r'cluster_name:\s*(\S+)', raw_conf)
            if m:
                corosync['cluster_name'] = m.group(1)
            # Parse nodes from nodelist
            for m in re.finditer(
                r'node\s*\{[^}]*?name:\s*(\S+)[^}]*?nodeid:\s*(\d+)',
                raw_conf, re.DOTALL
            ):
                corosync['nodes'].append({
                    'name': m.group(1),
                    'nodeid': m.group(2),
                })

        # Ring/link status from corosync-cfgtool
        cfgtool_file = corosync_dir / 'corosync-cfgtool_-s'
        corosync['ring_status'] = self._read_file_safe(cfgtool_file) or ''

        return corosync

    # ------------------------------------------------------------------
    # Cluster logs
    # ------------------------------------------------------------------

    def _collect_cluster_logs(self, pacemaker_dir: Path) -> Dict[str, Any]:
        """Collect cluster-specific logs for LogViewer display."""
        logs: Dict[str, Any] = {}

        crm_report_dir = pacemaker_dir / 'crm_report'

        # events.txt — corosync start/stop events
        events_file = crm_report_dir / 'events.txt'
        logs['events'] = self._read_log_file(events_file)

        # analysis.txt — crm_report pattern matching analysis
        analysis_file = crm_report_dir / 'analysis.txt'
        logs['analysis'] = self._read_log_file(analysis_file)

        # Per-node journal logs — find the first node subdir with journal.log
        if crm_report_dir.exists():
            for child in sorted(crm_report_dir.iterdir()):
                if child.is_dir():
                    journal = child / 'journal.log'
                    if journal.exists():
                        logs['journal'] = self._read_log_file(journal)
                        logs['journal_node'] = child.name
                        break

        return logs

    # ------------------------------------------------------------------
    # File reading helpers
    # ------------------------------------------------------------------

    def _read_file_safe(self, path: Path) -> Optional[str]:
        """Read a file safely, returning None on any error."""
        if not path or not path.exists():
            return None
        try:
            return path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            Logger.warning(f"Failed to read {path}: {e}")
            return None

    def _read_log_file(self, path: Path) -> Optional[str]:
        """Read a log file with byte-cap for safe embedding in reports."""
        if not path or not path.exists():
            return None
        try:
            file_size = path.stat().st_size
            max_bytes = MAX_CLUSTER_LOG_BYTES

            if file_size <= max_bytes:
                return path.read_text(encoding='utf-8', errors='replace')

            # Tail-read for large files
            with open(path, 'rb') as f:
                f.seek(file_size - max_bytes)
                f.readline()  # skip partial first line
                content = f.read().decode('utf-8', errors='replace')

            total_mb = file_size / (1024 * 1024)
            cap_mb = max_bytes / (1024 * 1024)
            return f"[... File truncated: showing last {cap_mb:.0f}MB of {total_mb:.1f}MB total ...]\n{content}"
        except OSError as e:
            Logger.warning(f"Failed to read log {path}: {e}")
            return None
