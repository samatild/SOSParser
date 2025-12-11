#!/usr/bin/env python3
"""Network analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any, List
from .parser import SupportconfigParser


class SupportconfigNetwork:
    """Analyzer for supportconfig network information."""
    
    def __init__(self, root_path: Path):
        """
        Initialize network analyzer.
        
        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete network analysis.
        
        Returns:
            Dictionary with network information
        """
        routes = self.get_routes()
        return {
            'interfaces': self.get_interfaces(),
            'routes': routes,      # backward compatibility
            'routing': routes,     # matches template usage
            'dns': self.get_dns_config(),
            'hosts': self.get_hosts(),
            'firewall': self.get_firewall_info(),
            'connectivity': self.get_connectivity(),
        }
    
    def get_interfaces(self) -> Dict[str, Any]:
        """Extract network interface information."""
        interfaces = {}
        
        # Get ip addr output
        ip_addr = self.parser.get_command_output('network.txt', '/sbin/ip addr')
        if ip_addr:
            interfaces['ip_addr'] = ip_addr

        # Link statistics
        ip_link = self.parser.get_command_output('network.txt', '/sbin/ip -stats link')
        if ip_link:
            interfaces['ip_link'] = ip_link
        
        # Wicked/network status
        wicked_status = self.parser.get_command_output('network.txt', '/bin/systemctl status network.service')
        if not wicked_status:
            wicked_status = self.parser.get_command_output('network.txt', '/bin/systemctl status wicked.service')
        if wicked_status:
            interfaces['status'] = wicked_status

        # Wicked detailed status/config
        wicked_ifstatus = self.parser.get_command_output('network.txt', '/usr/sbin/wicked ifstatus --verbose all')
        if wicked_ifstatus:
            interfaces['wicked_ifstatus'] = wicked_ifstatus
        wicked_show_config = self.parser.get_command_output('network.txt', '/usr/sbin/wicked show-config')
        if wicked_show_config:
            interfaces['wicked_show_config'] = wicked_show_config
        
        # Hardware info
        hwinfo = self.parser.get_command_output('network.txt', '/usr/sbin/hwinfo --netcard')
        if hwinfo:
            interfaces['hwinfo'] = hwinfo
        
        return interfaces
    
    def get_routes(self) -> Dict[str, Any]:
        """Extract routing information."""
        routes = {}
        
        # Get ip route outputs
        ip_route = self.parser.get_command_output('network.txt', '/sbin/ip route')
        if ip_route:
            routes['ip_route'] = ip_route
        ip_route_v6 = self.parser.get_command_output('network.txt', '/sbin/ip -6 route')
        if ip_route_v6:
            routes['ip6_route'] = ip_route_v6
        local_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table local')
        if local_route:
            routes['route_table_local'] = local_route
        main_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table main')
        if main_route:
            routes['route_table_main'] = main_route
        default_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table default')
        if default_route:
            routes['route_table_default'] = default_route
        cache_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table cache')
        if cache_route:
            routes['route_table_cache'] = cache_route
        cache_route_v6 = self.parser.get_command_output('network.txt', '/sbin/ip -6 route show table cache')
        if cache_route_v6:
            routes['route_table_cache_v6'] = cache_route_v6
        
        return routes
    
    def get_dns_config(self) -> Dict[str, Any]:
        """Extract DNS configuration."""
        dns = {}
        
        # Prefer network.txt for DNS-related configuration
        net_content = self.parser.read_file('network.txt')
        if net_content:
            net_sections = self.parser.extract_sections(net_content)
            for section in net_sections:
                lines = section.get('content', '').split('\n')
                if not lines:
                    continue
                first = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
                if '/etc/resolv.conf' in first:
                    dns['resolv_conf'] = body
                elif '/etc/nsswitch.conf' in first:
                    dns['nsswitch'] = body
                elif '/etc/hosts' in first:
                    dns['hosts'] = body

        # Fallback to etc.txt for resolv.conf / nsswitch / hosts if missing
        if 'resolv_conf' not in dns:
            resolv_conf = self.parser.get_file_listing('etc.txt', '/etc/resolv.conf')
            if resolv_conf:
                dns['resolv_conf'] = resolv_conf
        if 'nsswitch' not in dns:
            nsswitch = self.parser.get_file_listing('etc.txt', '/etc/nsswitch.conf')
            if nsswitch:
                dns['nsswitch'] = nsswitch
        if 'hosts' not in dns:
            hosts = self.get_hosts()
            if hosts:
                dns['hosts'] = hosts

        # Get nscd status
        nscd_status = self.parser.get_command_output('network.txt', 'systemctl status nscd.service')
        if nscd_status:
            dns['nscd_status'] = nscd_status
        
        return dns
    
    def get_hosts(self) -> str:
        """Extract /etc/hosts file."""
        hosts = self.parser.get_file_listing('etc.txt', '/etc/hosts')
        return hosts if hosts else ""
    
    def get_firewall_info(self) -> Dict[str, Any]:
        """Extract firewall information."""
        firewall = {}
        
        # Try to get firewalld status (may be missing in supportconfig)
        firewalld_status = self.parser.get_command_output('network.txt', 'firewall-cmd --state')
        if not firewalld_status:
            firewalld_status = self.parser.get_command_output('network.txt', 'systemctl status firewalld')
        if firewalld_status:
            firewall['firewalld'] = firewalld_status
        
        # iptables / ip6tables outputs; in this supportconfig they are notes about modules
        iptables = self.parser.get_command_output('network.txt', 'iptables')
        if iptables:
            firewall['iptables'] = iptables
        ip6tables = self.parser.get_command_output('network.txt', 'ip6tables')
        if ip6tables:
            firewall['ip6tables'] = ip6tables
        
        return firewall

    def get_connectivity(self) -> Dict[str, Any]:
        """Extract connectivity tests (ping) from network.txt."""
        conn = {}
        ping_local = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 127.0.0.1')
        if ping_local:
            conn['ping_loopback'] = ping_local
        ping_self = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 10.0.0.10')
        if ping_self:
            conn['ping_self'] = ping_self
        ping_gateway = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 10.0.0.1')
        if ping_gateway:
            conn['ping_gateway'] = ping_gateway
        ping_dns = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 168.63.129.16')
        if ping_dns:
            conn['ping_dns'] = ping_dns
        return conn
