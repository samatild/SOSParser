#!/usr/bin/env python3
"""Network configuration analysis from sosreport"""

from pathlib import Path
from utils.logger import Logger


class NetworkAnalyzer:
    """Analyze network configuration from sosreport"""
    
    def analyze_interfaces(self, base_path: Path) -> dict:
        """Analyze network interfaces"""
        Logger.debug("Analyzing network interfaces")
        
        data = {}
        
        # IP address info
        ip_addr = base_path / 'sos_commands' / 'networking' / 'ip_-d_address'
        if not ip_addr.exists():
            ip_addr = base_path / 'sos_commands' / 'networking' / 'ip_address_show'
        if ip_addr.exists():
            data['ip_addr'] = ip_addr.read_text()
        
        # IP link info
        ip_link = base_path / 'sos_commands' / 'networking' / 'ip_-s_-d_link'
        if ip_link.exists():
            data['ip_link'] = ip_link.read_text()
        
        # Interface stats
        netstat = base_path / 'sos_commands' / 'networking' / 'netstat_-i'
        if netstat.exists():
            data['netstat'] = netstat.read_text()
        
        # Ethtool info
        ethtool_dir = base_path / 'sos_commands' / 'networking'
        if ethtool_dir.exists():
            ethtool_files = {}
            for eth_file in ethtool_dir.glob('ethtool_*'):
                try:
                    ethtool_files[eth_file.name] = eth_file.read_text()[:2000]
                except Exception:
                    pass
            if ethtool_files:
                data['ethtool'] = ethtool_files
        
        return data
    
    def analyze_routing(self, base_path: Path) -> dict:
        """Analyze routing configuration"""
        Logger.debug("Analyzing routing")
        
        data = {}
        
        # IP route
        ip_route = base_path / 'sos_commands' / 'networking' / 'ip_route_show_table_all'
        if not ip_route.exists():
            ip_route = base_path / 'sos_commands' / 'networking' / 'ip_route'
        if ip_route.exists():
            data['ip_route'] = ip_route.read_text()
        
        # IPv6 route
        ip6_route = base_path / 'sos_commands' / 'networking' / 'ip_-6_route_show_table_all'
        if ip6_route.exists():
            data['ip6_route'] = ip6_route.read_text()
        
        # Routing table
        route_table = base_path / 'sos_commands' / 'networking' / 'route_-n'
        if route_table.exists():
            data['route_table'] = route_table.read_text()
        
        return data
    
    def analyze_dns(self, base_path: Path) -> dict:
        """Analyze DNS configuration"""
        Logger.debug("Analyzing DNS")
        
        data = {}
        
        # resolv.conf
        resolv_conf = base_path / 'etc' / 'resolv.conf'
        if resolv_conf.exists():
            data['resolv_conf'] = resolv_conf.read_text()
        
        # nsswitch.conf
        nsswitch = base_path / 'etc' / 'nsswitch.conf'
        if nsswitch.exists():
            data['nsswitch'] = nsswitch.read_text()
        
        # hosts file
        hosts = base_path / 'etc' / 'hosts'
        if hosts.exists():
            data['hosts'] = hosts.read_text()
        
        return data
    
    def analyze_firewall(self, base_path: Path) -> dict:
        """Analyze firewall configuration"""
        Logger.debug("Analyzing firewall")
        
        data = {}
        
        # Firewalld zones
        firewall_zones = base_path / 'sos_commands' / 'firewalld' / 'firewall-cmd_--list-all-zones'
        if firewall_zones.exists():
            data['firewall_zones'] = firewall_zones.read_text()
        
        # iptables rules
        iptables = base_path / 'sos_commands' / 'networking' / 'iptables_-vnxL'
        if iptables.exists():
            data['iptables'] = iptables.read_text()
        
        # ip6tables rules
        ip6tables = base_path / 'sos_commands' / 'networking' / 'ip6tables_-vnxL'
        if ip6tables.exists():
            data['ip6tables'] = ip6tables.read_text()
        
        return data
    
    def analyze_networkmanager(self, base_path: Path) -> dict:
        """Analyze NetworkManager configuration"""
        Logger.debug("Analyzing NetworkManager")
        
        data = {}
        
        # NetworkManager config
        nm_conf = base_path / 'etc' / 'NetworkManager' / 'NetworkManager.conf'
        if nm_conf.exists():
            data['nm_conf'] = nm_conf.read_text()
        
        # NetworkManager connections
        nm_connections = base_path / 'etc' / 'NetworkManager' / 'system-connections'
        if nm_connections.exists():
            connections = {}
            for conn_file in nm_connections.glob('*'):
                if conn_file.is_file():
                    try:
                        connections[conn_file.name] = conn_file.read_text()
                    except Exception:
                        pass
            if connections:
                data['connections'] = connections
        
        # NetworkManager status
        nm_status = base_path / 'sos_commands' / 'networkmanager' / 'nmcli_general_status'
        if nm_status.exists():
            data['nm_status'] = nm_status.read_text()
        
        # NetworkManager device status
        nm_devices = base_path / 'sos_commands' / 'networkmanager' / 'nmcli_device_show'
        if nm_devices.exists():
            data['nm_devices'] = nm_devices.read_text()
        
        return data
