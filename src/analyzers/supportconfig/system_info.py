#!/usr/bin/env python3
"""System information analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any
import re
from .parser import SupportconfigParser


class SupportconfigSystemInfo:
    """Analyzer for supportconfig system information."""
    
    def __init__(self, root_path: Path):
        """
        Initialize system info analyzer.
        
        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.parser = SupportconfigParser(root_path)
        self.root_path = root_path
    
    def get_os_info(self) -> Dict[str, str]:
        """Extract OS information from basic-environment.txt."""
        os_info = {}
        
        # Get uname info from basic-environment.txt
        uname_output = self.parser.get_command_output('basic-environment.txt', '/bin/uname -a')
        if uname_output:
            os_info['uname'] = uname_output.strip()
            # Parse kernel version from uname
            parts = uname_output.split()
            if len(parts) >= 3:
                os_info['kernel'] = parts[2]
        
        # Look for OS identification strings in basic-environment.txt
        content = self.parser.read_file('basic-environment.txt')
        if content:
            for line in content.split('\n'):
                line = line.strip()
                # Look for PRETTY_NAME, ID, VERSION_ID, etc.
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Common os-release keys
                    if key in ['NAME', 'ID', 'ID_LIKE', 'VERSION', 'VERSION_ID', 
                               'PRETTY_NAME', 'CPE_NAME', 'HOME_URL', 'BUG_REPORT_URL']:
                        os_info[key] = value
                # Look for SUSE/Linux version strings
                elif 'SUSE Linux Enterprise' in line or 'openSUSE' in line:
                    if 'NAME' not in os_info:
                        os_info['NAME'] = line.strip()
        
        # If still no NAME, try to extract from uname or use generic
        if 'NAME' not in os_info and 'uname' in os_info:
            if 'sles' in os_info['uname'].lower() or 'suse' in os_info['uname'].lower():
                os_info['NAME'] = 'SUSE Linux Enterprise Server'
                os_info['ID'] = 'sles'
        
        return os_info
    
    def get_hostname(self) -> str:
        """Extract hostname from uname output."""
        uname_output = self.parser.get_command_output('basic-environment.txt', '/bin/uname -a')
        if uname_output:
            # Hostname is typically the second field in uname -a
            parts = uname_output.split()
            if len(parts) >= 2:
                return parts[1]
        
        # Fallback: try to find hostname command output
        content = self.parser.read_file('basic-environment.txt')
        if content:
            sections = self.parser.extract_sections(content)
            for section in sections:
                if 'hostname' in section['header'].lower():
                    return section['content'].strip()
        
        return "Unknown"
    
    def get_kernel_info(self) -> Dict[str, str]:
        """Extract kernel information."""
        kernel_info = {}
        
        # Get kernel version from uname
        uname = self.parser.get_command_output('basic-environment.txt', '/bin/uname -a')
        if uname:
            parts = uname.split()
            if len(parts) >= 3:
                kernel_info['version'] = parts[2]
                kernel_info['full'] = uname.strip()
        
        # Get running kernel from boot.txt
        content = self.parser.read_file('boot.txt')
        if content:
            sections = self.parser.extract_sections(content)
            for section in sections:
                if 'running kernel' in section['header'].lower():
                    kernel_info['running'] = section['content'].strip()
                    break
        
        return kernel_info
    
    def get_uptime(self) -> str:
        """Extract system uptime."""
        uptime_output = self.parser.get_command_output('basic-health-check.txt', '/usr/bin/uptime')
        if uptime_output:
            return uptime_output.strip()
        return "Unknown"
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Extract CPU information from hardware.txt."""
        cpu_info = {}
        
        lscpu_output = self.parser.get_command_output('hardware.txt', '/usr/bin/lscpu')
        if lscpu_output:
            lines = lscpu_output.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'CPU(s)':
                        cpu_info['count'] = value
                    elif key == 'Model name':
                        cpu_info['model'] = value
                    elif key == 'Architecture':
                        cpu_info['architecture'] = value
                    elif key == 'CPU MHz' or key == 'BogoMIPS':
                        cpu_info['speed'] = value
                    elif key == 'Hypervisor vendor':
                        cpu_info['hypervisor'] = value
                    elif key == 'Virtualization type':
                        cpu_info['virt_type'] = value
        
        # Get /proc/cpuinfo for additional details
        cpuinfo_content = self.parser.get_file_listing('hardware.txt', '/proc/cpuinfo')
        if cpuinfo_content and 'processor' in cpuinfo_content:
            # Count processors
            processor_count = cpuinfo_content.count('processor\t:')
            if processor_count > 0:
                cpu_info['processors'] = str(processor_count)
        
        return cpu_info
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Extract memory information from memory.txt or hardware.txt."""
        memory_info = {}
        
        # Try memory.txt first - look for meminfo in Configuration File sections
        for filename in ['memory.txt', 'hardware.txt']:
            content = self.parser.read_file(filename)
            if not content:
                continue
                
            sections = self.parser.extract_sections(content)
            for section in sections:
                # Check for Configuration File sections (file path is in content)
                if section['type'] == 'Configuration':
                    lines = section['content'].split('\n')
                    if lines and '/proc/meminfo' in lines[0]:
                        # Parse meminfo content (skip first line which is the path)
                        for line in lines[1:]:
                            if ':' in line:
                                key, value = line.split(':', 1)
                                key = key.strip()
                                value = value.strip()
                                
                                if key == 'MemTotal':
                                    memory_info['total'] = value
                                elif key == 'MemFree':
                                    memory_info['free'] = value
                                elif key == 'MemAvailable':
                                    memory_info['available'] = value
                                elif key == 'SwapTotal':
                                    memory_info['swap_total'] = value
                                elif key == 'SwapFree':
                                    memory_info['swap_free'] = value
                        
                        if memory_info:  # Found it, stop searching
                            return memory_info
        
        return memory_info
    
    def get_disk_info(self) -> Dict[str, Any]:
        """Extract disk information from fs-diskio.txt."""
        disk_info = {
            'devices': [],
            'partitions': []
        }
        
        # Get lsblk output
        lsblk = self.parser.get_command_output('fs-diskio.txt', 'lsblk')
        if lsblk:
            disk_info['lsblk'] = lsblk
        
        # Get df output from fs-diskio.txt
        df_output = self.parser.get_command_output('fs-diskio.txt', '/bin/df')
        if df_output:
            disk_info['df'] = df_output
        
        return disk_info
    
    def get_dmi_info(self) -> Dict[str, str]:
        """Extract DMI/BIOS information from hardware.txt."""
        dmi_info = {}
        
        content = self.parser.read_file('hardware.txt')
        if content:
            sections = self.parser.extract_sections(content)
            
            # Look for virtualization section
            for section in sections:
                if section['type'] == 'System' and 'Virtualization' in section['header']:
                    lines = section['content'].split('\n')
                    for line in lines:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            dmi_info[key.strip()] = value.strip()
            
            # Get dmidecode output if available
            dmidecode = self.parser.get_command_output('hardware.txt', 'dmidecode')
            if dmidecode:
                dmi_info['dmidecode'] = dmidecode[:500]  # Store first 500 chars
        
        return dmi_info
    
    def get_system_load(self) -> Dict[str, str]:
        """Extract system load information."""
        load_info = {}
        
        # Get vmstat from basic-health-check.txt
        vmstat = self.parser.get_command_output('basic-health-check.txt', '/usr/bin/vmstat')
        if vmstat:
            load_info['vmstat'] = vmstat
        
        # Get uptime for load average
        uptime = self.get_uptime()
        if 'load average' in uptime:
            match = re.search(r'load average:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)', uptime)
            if match:
                load_info['1min'] = match.group(1)
                load_info['5min'] = match.group(2)
                load_info['15min'] = match.group(3)
        
        return load_info

    def get_cpu_vulnerabilities(self) -> Dict[str, Any]:
        """Extract CPU vulnerabilities status from basic-health-check.txt."""
        vuln_info = {}

        content = self.parser.read_file('basic-health-check.txt')
        if content:
            lines = content.split('\n')

            for line in lines:
                line = line.strip()
                if '/sys/devices/system/cpu/vulnerabilities/' in line and ':' in line:
                    # Extract vulnerability name and status
                    parts = line.split('/vulnerabilities/')
                    if len(parts) == 2:
                        vuln_path = parts[1]
                        if ':' in vuln_path:
                            vuln_name, vuln_status = vuln_path.split(':', 1)
                            vuln_name = vuln_name.strip()
                            vuln_status = vuln_status.strip()
                            vuln_info[vuln_name] = vuln_status

        return vuln_info

    def get_kernel_tainted_status(self) -> str:
        """Extract kernel tainted status from basic-health-check.txt."""
        content = self.parser.read_file('basic-health-check.txt')
        if content:
            for line in content.split('\n'):
                if 'Kernel Status --' in line:
                    if 'Not Tainted' in line:
                        return 'Not Tainted'
                    elif 'Tainted' in line:
                        return 'Tainted'
        return 'Unknown'

    def get_supportconfig_info(self) -> Dict[str, str]:
        """Extract supportconfig metadata from basic-environment.txt."""
        info = {}

        content = self.parser.read_file('basic-environment.txt')
        if content:
            lines = content.split('\n')
            for line in lines[:10]:  # Check first 10 lines for metadata
                line = line.strip()
                if 'Script Version:' in line:
                    info['script_version'] = line.split('Script Version:')[-1].strip()
                elif 'Library Version:' in line:
                    info['library_version'] = line.split('Library Version:')[-1].strip()
                elif 'Script Date:' in line:
                    info['script_date'] = line.split('Script Date:')[-1].strip()

        return info

    def get_top_processes(self) -> Dict[str, Any]:
        """Extract top CPU and memory processes from basic-health-check.txt."""
        processes = {'cpu': [], 'memory': []}

        content = self.parser.read_file('basic-health-check.txt')
        if content:
            lines = content.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if 'Top 10 CPU Processes' in line:
                    current_section = 'cpu'
                    continue
                elif 'Top 10 Memory Processes' in line:
                    current_section = 'memory'
                    continue
                elif line.startswith('%CPU') and current_section == 'cpu':
                    # Skip header
                    continue
                elif line.startswith('%MEM') and current_section == 'memory':
                    # Skip header
                    continue
                elif current_section and line and not line.startswith('---') and not line.startswith('#'):
                    # Process line - should have at least 4 parts: pct, pid, user, cmd
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            pct = float(parts[0])
                            pid = parts[1]
                            user = parts[2]
                            cmd = ' '.join(parts[3:])

                            if current_section == 'cpu':
                                processes['cpu'].append({
                                    'cpu_pct': pct,
                                    'pid': pid,
                                    'user': user,
                                    'cmd': cmd
                                })
                            elif current_section == 'memory':
                                processes['memory'].append({
                                    'mem_pct': pct,
                                    'pid': pid,
                                    'user': user,
                                    'cmd': cmd
                                })
                        except (ValueError, IndexError):
                            # Skip lines that don't parse correctly
                            continue
                elif current_section and not line:
                    # Empty line might indicate end of section
                    current_section = None

        return processes

    def get_system_resources(self) -> Dict[str, str]:
        """Extract system resource information from basic-health-check.txt."""
        resources = {}

        # Extract df -h output
        df_output = self.parser.get_command_output('basic-health-check.txt', '/bin/df -h')
        if df_output:
            resources['df_h'] = df_output

        # Extract vmstat output
        vmstat_output = self.parser.get_command_output('basic-health-check.txt', '/usr/bin/vmstat')
        if vmstat_output:
            resources['vmstat'] = vmstat_output

        # Extract free output
        free_output = self.parser.get_command_output('basic-health-check.txt', '/usr/bin/free -k')
        if free_output:
            resources['free'] = free_output

        return resources
