#!/usr/bin/env python3
"""Cluster (Pacemaker/Corosync) analysis from supportconfig ha.txt"""

import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.logger import Logger


# Byte cap for cluster log content extracted from ha.txt
MAX_CLUSTER_LOG_BYTES = int(os.environ.get('MAX_CLUSTER_LOG_BYTES', str(5 * 1024 * 1024)))  # 5 MB
# Max lines to read from pacemaker.log section in ha.txt
MAX_PACEMAKER_LOG_LINES = int(os.environ.get('MAX_PACEMAKER_LOG_LINES', str(50000)))

# Section header pattern for supportconfig files
_SECTION_PATTERN = re.compile(r'^#==\[\s*(.+?)\s*\]={5,}#\s*$')


class SupportconfigClusterAnalyzer:
    """Analyze Pacemaker/Corosync cluster information from supportconfig ha.txt"""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Single-pass extraction of Configuration File / Log File sections
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_file_sections(ha_path: Path,
                               targets: Dict[str, Dict[str, Any]],
                               ) -> Dict[str, str]:
        """
        Stream through ha.txt once and extract Configuration File and Log File
        sections by matching the comment line (``# /path/to/file``) that follows
        the ``#==[ Type ]==#`` header.

        Args:
            ha_path:  Path to ha.txt
            targets:  Mapping of key → {'path': str, 'type': 'Configuration'|'Log',
                      'max_lines': int}.  ``path`` is the substring to match in the
                      comment line.

        Returns:
            Mapping of key → extracted content string.
        """
        results: Dict[str, str] = {}
        remaining = set(targets.keys())

        try:
            with open(ha_path, 'r', encoding='utf-8', errors='ignore') as fh:
                current_key: Optional[str] = None
                section_type: str = ''
                awaiting_comment = False  # True right after matching a section header
                content_lines: List[str] = []
                line_count = 0

                for line in fh:
                    header_m = _SECTION_PATTERN.match(line)

                    if header_m:
                        # Save any section we were collecting
                        if current_key is not None:
                            results[current_key] = '\n'.join(content_lines).strip()
                            remaining.discard(current_key)
                            if not remaining:
                                return results

                        header = header_m.group(1)
                        section_type = header.split()[0] if header else ''
                        current_key = None
                        content_lines = []
                        line_count = 0

                        # Mark that we should check the next comment line
                        if section_type in ('Configuration', 'Log'):
                            awaiting_comment = True
                        else:
                            awaiting_comment = False
                        continue

                    if awaiting_comment:
                        awaiting_comment = False
                        # Comment line looks like "# /etc/corosync/corosync.conf"
                        if line.startswith('#'):
                            comment = line.strip('# \n')
                            for key in remaining:
                                t = targets[key]
                                if t['type'] != section_type:
                                    continue
                                if t['path'] in comment:
                                    current_key = key
                                    break
                        continue

                    if current_key is not None:
                        content_lines.append(line.rstrip('\n'))
                        line_count += 1
                        max_lines = targets[current_key].get('max_lines', 100000)
                        if line_count >= max_lines:
                            results[current_key] = '\n'.join(content_lines).strip()
                            remaining.discard(current_key)
                            current_key = None
                            if not remaining:
                                return results

                # EOF — save last section if applicable
                if current_key is not None:
                    results[current_key] = '\n'.join(content_lines).strip()

        except Exception as exc:
            Logger.error(f"Error reading ha.txt file sections: {exc}")

        return results

    def analyze(self, base_path: Path) -> Dict[str, Any]:
        """
        Analyze cluster information from supportconfig ha.txt.

        Args:
            base_path: Path to extracted supportconfig directory

        Returns:
            Dictionary with cluster information, or dict with available=False
        """
        Logger.debug("Analyzing cluster information from supportconfig")

        ha_file = base_path / 'ha.txt'
        if not ha_file.exists():
            Logger.debug("No ha.txt found, skipping cluster analysis")
            return {'available': False}

        from analyzers.supportconfig.parser import SupportconfigParser
        parser = SupportconfigParser(base_path)

        # Get crm_mon -r -1 output (has "Full List of Resources:")
        crm_mon_r = parser.find_command_streaming('ha.txt', 'crm_mon -r -1')
        if not crm_mon_r:
            crm_mon_r = parser.find_command_streaming('ha.txt', 'crm_mon -r1')

        if not crm_mon_r:
            Logger.debug("No crm_mon output found in ha.txt, skipping cluster analysis")
            return {'available': False}

        # Check for connection errors (cluster not running)
        if 'Connection refused' in crm_mon_r or 'Could not connect' in crm_mon_r:
            Logger.debug("Cluster not running (connection refused), skipping cluster analysis")
            return {'available': False}

        # Parse the main cluster status
        data = {
            'available': True,
            **self._parse_crm_mon(crm_mon_r),
        }

        # Get crm_mon -A -1 for node attributes
        crm_mon_a = parser.find_command_streaming('ha.txt', 'crm_mon -A -1')
        if crm_mon_a:
            data['node_attributes'] = self._parse_node_attributes(crm_mon_a)
            data['failed_actions'] = self._parse_failed_actions(crm_mon_a)
        else:
            data['failed_actions'] = self._parse_failed_actions(crm_mon_r)

        # Raw crm_mon output for reference
        data['pcs_status_raw'] = crm_mon_r

        # Cluster configuration (crm configure show)
        crm_config = parser.find_command_streaming('ha.txt', 'crm configure show')
        data['properties'] = crm_config or ''

        # Parse cluster name from crm configure
        if crm_config and not data.get('cluster_name'):
            m = re.search(r'cluster-name=(\S+)', crm_config)
            if m:
                data['cluster_name'] = m.group(1)

        # Ring/link status from corosync-cfgtool -s (Command section — parser handles this)
        ring_status = parser.find_command_streaming('ha.txt', 'corosync-cfgtool -s')

        # Extract Configuration File and Log File sections in a single pass
        file_sections = self._extract_file_sections(ha_file, {
            'corosync_conf': {
                'path': '/etc/corosync/corosync.conf',
                'type': 'Configuration',
                'max_lines': 5000,
            },
            'sbd_config': {
                'path': '/etc/sysconfig/sbd',
                'type': 'Configuration',
                'max_lines': 500,
            },
            'pacemaker_log': {
                'path': '/var/log/pacemaker/pacemaker.log',
                'type': 'Log',
                'max_lines': MAX_PACEMAKER_LOG_LINES,
            },
        })

        # Quorum
        data['quorum'] = self._parse_quorum(
            file_sections.get('corosync_conf', ''), crm_mon_r
        )

        # Fencing / STONITH
        data['fencing'] = self._parse_fencing(file_sections.get('sbd_config', ''))

        # Corosync
        data['corosync'] = self._parse_corosync(
            file_sections.get('corosync_conf', ''), ring_status or ''
        )

        # Cluster logs
        data['logs'] = self._build_logs(file_sections.get('pacemaker_log', ''))

        return data

    # ------------------------------------------------------------------
    # crm_mon parsing
    # ------------------------------------------------------------------

    def _parse_crm_mon(self, raw: str) -> Dict[str, Any]:
        """Parse crm_mon -r -1 output into structured data."""
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

        # Stack
        m = re.search(r'\*\s*Stack:\s*(\S+)', raw)
        if m:
            result['stack'] = m.group(1)

        # DC node — crm_mon format: "Current DC: node (version X) - partition with quorum"
        m = re.search(r'\*\s*Current DC:\s*(\S+)\s+\(version\s+([^)]+)\)', raw)
        if m:
            result['dc_node'] = m.group(1)
            result['pacemaker_version'] = m.group(2)

        # Last updated / last change
        m = re.search(r'\*\s*Last updated:\s*(.+?)$', raw, re.MULTILINE)
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

        # Node list — crm_mon uses "* Online: [ node1 node2 ]" format
        for status_label in ['Online', 'OFFLINE', 'Standby', 'Maintenance']:
            m = re.search(
                rf'\*\s*{status_label}:\s*\[\s*([^\]]+)\s*\]',
                raw, re.IGNORECASE
            )
            if m:
                for node_name in m.group(1).split():
                    result['nodes'].append({
                        'name': node_name,
                        'id': '',
                        'status': status_label.lower(),
                    })

        # Resources — parse groups, clones, and primitives
        self._parse_resources(raw, result)

        return result

    def _parse_resources(self, raw: str, result: Dict[str, Any]):
        """Parse the Full List of Resources section from crm_mon output."""
        # crm_mon -r -1 uses "Full List of Resources:"
        # crm_mon -A -1 uses "Active Resources:"
        res_section = re.search(
            r'(?:Full List of Resources|Active Resources):\n(.*?)(?=\nNode Attributes:|\nFailed Resource Actions:|\nMigration Summary:|\nInactive Resources:|\Z)',
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

            # Clone "Started: [ node1 node2 ]" line
            started_m = re.match(r'\s*\*\s*Started:\s*\[\s*([^\]]+)\s*\]', stripped)
            if started_m and current_clone:
                for node_name in started_m.group(1).split():
                    result['clone_sets'][-1]['instances'].append({
                        'id': result['clone_sets'][-1]['resource_id'],
                        'type': '',
                        'status': 'Started',
                        'node': node_name,
                        'group': None,
                        'clone': current_clone,
                    })
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

            # Blank lines at top-level indent reset context
            if stripped == '':
                current_group = None
                current_clone = None

            i += 1

    def _parse_node_attributes(self, raw: str) -> Dict[str, Dict[str, str]]:
        """Parse Node Attributes section from crm_mon -A output."""
        node_attributes: Dict[str, Dict[str, str]] = {}

        attr_section = re.search(
            r'Node Attributes:\n(.*?)(?=\nFailed Resource Actions:|\nMigration Summary:|\Z)',
            raw, re.DOTALL
        )
        if not attr_section:
            return node_attributes

        current_node = None
        for line in attr_section.group(1).splitlines():
            node_m = re.match(r'\s*\*\s*Node:\s*(\S+)', line)
            if node_m:
                current_node = node_m.group(1).rstrip(':')
                node_attributes[current_node] = {}
            elif current_node:
                attr_m = re.match(r'\s*\*\s*(\S+)\s*:\s*(.+)', line)
                if attr_m:
                    node_attributes[current_node][attr_m.group(1)] = attr_m.group(2).strip()

        return node_attributes

    def _parse_failed_actions(self, raw: str) -> List[Dict[str, str]]:
        """Parse Failed Resource Actions from crm_mon output."""
        failed = []
        section = re.search(
            r'Failed Resource Actions:\n(.*?)(?=\n\n|\Z)',
            raw, re.DOTALL
        )
        if not section:
            return failed

        for line in section.group(1).strip().splitlines():
            line = line.strip()
            if line.startswith('*'):
                failed.append({'raw': line.lstrip('* ').strip()})

        return failed

    # ------------------------------------------------------------------
    # Quorum
    # ------------------------------------------------------------------

    def _parse_quorum(self, corosync_conf: str, crm_mon_raw: str) -> Dict[str, Any]:
        """Parse quorum information from corosync.conf and crm_mon output."""
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

        # Check if quorate from crm_mon output
        if 'partition with quorum' in crm_mon_raw:
            quorum['quorate'] = True
            quorum['available'] = True

        # Parse corosync.conf for quorum settings
        if corosync_conf:
            m = re.search(r'provider:\s*(\S+)', corosync_conf)
            if m:
                quorum['provider'] = m.group(1)
            m = re.search(r'expected_votes:\s*(\d+)', corosync_conf)
            if m:
                quorum['expected_votes'] = int(m.group(1))
                quorum['available'] = True

        # Get node count from crm_mon
        m = re.search(r'\*\s*(\d+)\s+nodes?\s+configured', crm_mon_raw)
        if m:
            quorum['nodes'] = int(m.group(1))

        # Extract members from nodelist in corosync.conf
        if corosync_conf:
            for node_m in re.finditer(
                r'node\s*\{[^}]*?ring0_addr:\s*(\S+)[^}]*?nodeid:\s*(\d+)',
                corosync_conf, re.DOTALL
            ):
                quorum['members'].append({
                    'nodeid': node_m.group(2),
                    'votes': '1',
                    'name': node_m.group(1),
                })

        return quorum

    # ------------------------------------------------------------------
    # Fencing / STONITH
    # ------------------------------------------------------------------

    def _parse_fencing(self, sbd_config: str) -> Dict[str, Any]:
        """Parse STONITH/SBD fencing information."""
        fencing: Dict[str, Any] = {
            'available': False,
            'devices': [],
            'sbd_status': '',
            'sbd_watchdog': '',
            'history': '',
        }

        if sbd_config:
            fencing['available'] = True
            sbd_summary_lines = []
            for key in ['SBD_DEVICE', 'SBD_PACEMAKER', 'SBD_STARTMODE',
                         'SBD_WATCHDOG_DEV', 'SBD_WATCHDOG_TIMEOUT',
                         'SBD_DELAY_START', 'SBD_TIMEOUT_ACTION']:
                m = re.search(rf'^{key}=(.+)$', sbd_config, re.MULTILINE)
                if m:
                    sbd_summary_lines.append(f"{key}={m.group(1)}")
            fencing['sbd_status'] = '\n'.join(sbd_summary_lines)

            m = re.search(r'^SBD_WATCHDOG_DEV=(.+)$', sbd_config, re.MULTILINE)
            if m:
                fencing['sbd_watchdog'] = m.group(1).strip()

        return fencing

    # ------------------------------------------------------------------
    # Corosync
    # ------------------------------------------------------------------

    def _parse_corosync(self, raw_conf: str, ring_status: str) -> Dict[str, Any]:
        """Parse corosync configuration and status."""
        corosync: Dict[str, Any] = {
            'available': False,
            'config': '',
            'ring_status': '',
            'transport': '',
            'cluster_name': '',
            'nodes': [],
        }

        if raw_conf:
            corosync['available'] = True
            corosync['config'] = raw_conf

            m = re.search(r'transport:\s*(\S+)', raw_conf)
            if m:
                corosync['transport'] = m.group(1)
            m = re.search(r'cluster_name:\s*(\S+)', raw_conf)
            if m:
                corosync['cluster_name'] = m.group(1)

            for m in re.finditer(
                r'node\s*\{[^}]*?ring0_addr:\s*(\S+)[^}]*?nodeid:\s*(\d+)',
                raw_conf, re.DOTALL
            ):
                corosync['nodes'].append({
                    'name': m.group(1),
                    'nodeid': m.group(2),
                })

        if ring_status:
            corosync['ring_status'] = ring_status
            if not corosync['available']:
                corosync['available'] = True

        return corosync

    # ------------------------------------------------------------------
    # Cluster logs
    # ------------------------------------------------------------------

    def _build_logs(self, pacemaker_log: str) -> Dict[str, Any]:
        """Build cluster logs dict for LogViewer display."""
        logs: Dict[str, Any] = {}

        if pacemaker_log and 'File not found' not in pacemaker_log:
            log_bytes = len(pacemaker_log.encode('utf-8', errors='replace'))
            if log_bytes > MAX_CLUSTER_LOG_BYTES:
                all_lines = pacemaker_log.splitlines()
                kept_lines: List[str] = []
                total_bytes = 0
                for line in reversed(all_lines):
                    line_bytes = len(line.encode('utf-8', errors='replace')) + 1
                    if total_bytes + line_bytes > MAX_CLUSTER_LOG_BYTES:
                        break
                    kept_lines.append(line)
                    total_bytes += line_bytes
                kept_lines.reverse()
                total_mb = log_bytes / (1024 * 1024)
                cap_mb = MAX_CLUSTER_LOG_BYTES / (1024 * 1024)
                pacemaker_log = (
                    f"[... Log truncated: showing last {cap_mb:.0f}MB of ~{total_mb:.1f}MB total ...]\n"
                    + '\n'.join(kept_lines)
                )
            logs['pacemaker'] = pacemaker_log

        return logs
