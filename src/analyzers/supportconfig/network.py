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
        return {
            'interfaces': self.get_interfaces(),
            'routes': self.get_routes(),
            'dns': self.get_dns_config(),
            'hosts': self.get_hosts(),
            'firewall': self.get_firewall_info(),
        }
    
    def get_interfaces(self) -> Dict[str, Any]:
        """Extract network interface information."""
        interfaces = {}
        
        # Get ip addr output
        ip_addr = self.parser.get_command_output('network.txt', '/bin/ip addr')
        if ip_addr:
            interfaces['ip_addr'] = ip_addr
        
        # Get ifconfig output (if available)
        ifconfig = self.parser.get_command_output('network.txt', '/sbin/ifconfig')
        if ifconfig:
            interfaces['ifconfig'] = ifconfig
        
        # Get wicked/network status
        wicked_status = self.parser.get_command_output('network.txt', 'systemctl status network.service')
        if not wicked_status:
            wicked_status = self.parser.get_command_output('network.txt', 'systemctl status wicked.service')
        if wicked_status:
            interfaces['status'] = wicked_status
        
        return interfaces
    
    def get_routes(self) -> Dict[str, Any]:
        """Extract routing information."""
        routes = {}
        
        # Get ip route output
        ip_route = self.parser.get_command_output('network.txt', '/bin/ip route')
        if ip_route:
            routes['ip_route'] = ip_route
        
        # Get routing table
        route_n = self.parser.get_command_output('network.txt', '/sbin/route -n')
        if route_n:
            routes['route_table'] = route_n
        
        return routes
    
    def get_dns_config(self) -> Dict[str, Any]:
        """Extract DNS configuration."""
        dns = {}
        
        # Get /etc/resolv.conf
        resolv_conf = self.parser.get_file_listing('etc.txt', '/etc/resolv.conf')
        if resolv_conf:
            dns['resolv_conf'] = resolv_conf
        
        # Get nsswitch.conf
        nsswitch = self.parser.get_file_listing('etc.txt', '/etc/nsswitch.conf')
        if nsswitch:
            dns['nsswitch'] = nsswitch
        
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
        
        # Try to get firewalld status
        firewalld_status = self.parser.get_command_output('network.txt', 'systemctl status firewalld')
        if firewalld_status:
            firewall['firewalld'] = firewalld_status
        
        # Get iptables rules
        iptables = self.parser.get_command_output('network.txt', '/usr/sbin/iptables -L')
        if iptables:
            firewall['iptables'] = iptables
        
        # Get iptables-save
        iptables_save = self.parser.get_command_output('network.txt', '/usr/sbin/iptables-save')
        if iptables_save:
            firewall['iptables_save'] = iptables_save
        
        return firewall
