"""
Supportconfig System Configuration Analyzer

Analyzes system configuration from supportconfig format including:
- Boot and GRUB configuration
- SSH configuration
- Authentication settings
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from .parser import SupportconfigParser


class SupportconfigSystemConfig:
    """Analyzer for supportconfig system configuration."""
    
    def __init__(self, root_path: Path):
        """Initialize with root path of extracted supportconfig."""
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """Run all system config analysis."""
        return {
            'boot': self.get_boot_config(),
            'ssh': self.get_ssh_config(),
        }
    
    def get_boot_config(self) -> Dict[str, Any]:
        """
        Extract boot and GRUB configuration from boot.txt.
        
        Returns:
            Dictionary with grub_config, kernel_cmdline, boot_entries
        """
        boot_info = {
            'grub_config': {},
            'kernel_cmdline': '',
            'grub_cfg_path': '',
            'grub_verification': '',
        }
        
        content = self.parser.read_file('boot.txt')
        if not content:
            return boot_info
        
        sections = self.parser.extract_sections(content)
        
        for section in sections:
            # Extract GRUB default config from /etc/default/grub
            if section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if lines and '/etc/default/grub' in lines[0] and 'not found' not in lines[0].lower():
                    # Parse GRUB configuration
                    for line in lines[1:]:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            boot_info['grub_config'][key] = value
                            
                            # Extract kernel command line
                            if key == 'GRUB_CMDLINE_LINUX_DEFAULT':
                                boot_info['kernel_cmdline'] = value
            
            # Extract GRUB verification status
            elif section['type'] == 'Verification':
                lines = section['content'].split('\n')
                if lines and 'grub2' in lines[0]:
                    # Get verification status
                    for line in lines:
                        if 'Verification Status:' in line:
                            boot_info['grub_verification'] = line.split(':', 1)[1].strip()
                        elif not line.startswith('#') and line.strip():
                            # Show any differences found
                            if 'grub_verification' in boot_info and boot_info['grub_verification']:
                                if 'differences' not in boot_info:
                                    boot_info['differences'] = []
                                boot_info['differences'].append(line.strip())
        
        return boot_info
    
    def get_ssh_config(self) -> Dict[str, Any]:
        """
        Extract SSH and authentication configuration from ssh.txt.
        
        Returns:
            Dictionary with sshd_config, service_status, pam_config
        """
        ssh_info = {
            'service_status': {},
            'sshd_config': {},
            'ssh_client_config': {},
            'pam_config': [],
            'listening_ports': [],
        }
        
        content = self.parser.read_file('ssh.txt')
        if not content:
            return ssh_info
        
        sections = self.parser.extract_sections(content)
        
        for section in sections:
            if section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                    
                cmd_line = lines[0].strip('# ').strip()
                
                # Extract SSH service status
                if 'systemctl status sshd' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    # Parse systemctl output
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('Loaded:'):
                            ssh_info['service_status']['loaded'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Active:'):
                            ssh_info['service_status']['active'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Main PID:'):
                            ssh_info['service_status']['pid'] = line.split(':', 1)[1].strip()
                
                # Extract listening ports
                elif 'ss -nlp' in cmd_line or 'grep sshd' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    for line in output.split('\n'):
                        if 'sshd' in line and line.strip():
                            ssh_info['listening_ports'].append(line.strip())
            
            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                
                file_path = lines[0].strip('# ').strip()
                
                # Extract sshd_config
                if '/etc/ssh/sshd_config' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse SSH config directives
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                key, value = parts
                                ssh_info['sshd_config'][key] = value
                            elif parts:  # Handle directives without values
                                ssh_info['sshd_config'][parts[0]] = 'enabled'
                
                # Extract ssh_config (client)
                elif '/etc/ssh/ssh_config' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('Host'):
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                key, value = parts
                                ssh_info['ssh_client_config'][key] = value
                
                # Extract PAM config
                elif '/etc/pam.d/sshd' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ssh_info['pam_config'].append(line)
        
        return ssh_info
