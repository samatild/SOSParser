#!/usr/bin/env python3
"""System information extraction from sosreport"""

from pathlib import Path
from datetime import datetime
from utils.logger import Logger


def get_hostname(base_path: Path) -> str:
    """Extract hostname from sosreport"""
    try:
        # Try etc/hostname first
        hostname_file = base_path / 'etc' / 'hostname'
        if hostname_file.exists():
            hostname = hostname_file.read_text().strip()
            if hostname:
                return hostname
        
        # Try sos_commands/general/hostname
        alt_hostname = base_path / 'sos_commands' / 'general' / 'hostname'
        if alt_hostname.exists():
            hostname = alt_hostname.read_text().strip()
            if hostname:
                return hostname
        
        return "Unknown"
    except Exception as e:
        Logger.warning(f"Failed to get hostname: {e}")
        return "Unknown"


def get_os_release(base_path: Path) -> dict:
    """Extract OS release information"""
    try:
        os_release_file = base_path / 'etc' / 'os-release'
        if not os_release_file.exists():
            # Try redhat-release
            redhat_release = base_path / 'etc' / 'redhat-release'
            if redhat_release.exists():
                release_text = redhat_release.read_text().strip()
                return {
                    'NAME': release_text,
                    'VERSION': 'Unknown',
                    'ID': 'rhel',
                    'PRETTY_NAME': release_text
                }
            return {
                'NAME': 'Unknown',
                'VERSION': 'Unknown',
                'ID': 'unknown',
                'PRETTY_NAME': 'Unknown Linux'
            }
        
        os_info = {}
        content = os_release_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                os_info[key] = value
        
        return os_info
    except Exception as e:
        Logger.warning(f"Failed to get OS release: {e}")
        return {'NAME': 'Unknown', 'VERSION': 'Unknown', 'ID': 'unknown'}


def get_kernel_info(base_path: Path) -> dict:
    """Extract kernel information"""
    try:
        kernel_info = {}
        
        # Try uname
        uname_file = base_path / 'sos_commands' / 'kernel' / 'uname_-a'
        if uname_file.exists():
            uname_output = uname_file.read_text().strip()
            kernel_info['uname'] = uname_output
            # Parse kernel version
            parts = uname_output.split()
            if len(parts) >= 3:
                kernel_info['version'] = parts[2]
        
        # Try proc/version
        proc_version = base_path / 'proc' / 'version'
        if proc_version.exists():
            kernel_info['proc_version'] = proc_version.read_text().strip()
        
        return kernel_info
    except Exception as e:
        Logger.warning(f"Failed to get kernel info: {e}")
        return {}


def get_uptime(base_path: Path) -> str:
    """Extract system uptime"""
    try:
        uptime_file = base_path / 'sos_commands' / 'general' / 'uptime'
        if not uptime_file.exists():
            uptime_file = base_path / 'proc' / 'uptime'
        
        if uptime_file.exists():
            return uptime_file.read_text().strip()
        
        return "Unknown"
    except Exception as e:
        Logger.warning(f"Failed to get uptime: {e}")
        return "Unknown"


def get_execution_timestamp() -> str:
    """Get current execution timestamp"""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def get_cpu_info(base_path: Path) -> dict:
    """Extract CPU information"""
    try:
        cpuinfo = {}
        cpuinfo_file = base_path / 'proc' / 'cpuinfo'
        if cpuinfo_file.exists():
            content = cpuinfo_file.read_text()
            lines = content.splitlines()
            
            # Count processors
            processor_count = content.count('processor')
            cpuinfo['processor_count'] = processor_count
            
            # Get model name
            for line in lines:
                if 'model name' in line:
                    cpuinfo['model'] = line.split(':', 1)[1].strip()
                    break
            
            # Get CPU MHz
            for line in lines:
                if 'cpu MHz' in line:
                    cpuinfo['mhz'] = line.split(':', 1)[1].strip()
                    break
        
        # Try lscpu
        lscpu_file = base_path / 'sos_commands' / 'processor' / 'lscpu'
        if lscpu_file.exists():
            cpuinfo['lscpu'] = lscpu_file.read_text()[:1000]
        
        return cpuinfo
    except Exception as e:
        Logger.warning(f"Failed to get CPU info: {e}")
        return {}


def get_memory_info(base_path: Path) -> dict:
    """Extract memory information"""
    try:
        meminfo = {}
        meminfo_file = base_path / 'proc' / 'meminfo'
        if meminfo_file.exists():
            content = meminfo_file.read_text()
            for line in content.splitlines():
                if 'MemTotal' in line:
                    meminfo['total'] = line.split(':', 1)[1].strip()
                elif 'MemFree' in line:
                    meminfo['free'] = line.split(':', 1)[1].strip()
                elif 'MemAvailable' in line:
                    meminfo['available'] = line.split(':', 1)[1].strip()
                elif 'SwapTotal' in line:
                    meminfo['swap_total'] = line.split(':', 1)[1].strip()
                elif 'SwapFree' in line:
                    meminfo['swap_free'] = line.split(':', 1)[1].strip()
        
        # Try free command
        free_file = base_path / 'sos_commands' / 'memory' / 'free'
        if free_file.exists():
            meminfo['free_output'] = free_file.read_text()
        
        return meminfo
    except Exception as e:
        Logger.warning(f"Failed to get memory info: {e}")
        return {}


def get_disk_info(base_path: Path) -> dict:
    """Extract disk information summary"""
    try:
        diskinfo = {}
        
        # Get disk list
        lsblk = base_path / 'sos_commands' / 'block' / 'lsblk'
        if lsblk.exists():
            diskinfo['lsblk'] = lsblk.read_text()[:1500]
        
        # Count disks
        block_dir = base_path / 'sys' / 'block'
        if block_dir.exists():
            disks = [d.name for d in block_dir.iterdir() if d.name.startswith(('sd', 'hd', 'vd', 'nvme'))]
            diskinfo['disk_count'] = len(disks)
            diskinfo['disks'] = disks[:10]  # Limit to 10
        
        return diskinfo
    except Exception as e:
        Logger.warning(f"Failed to get disk info: {e}")
        return {}


def get_system_load(base_path: Path) -> dict:
    """Extract system load information"""
    try:
        loadinfo = {}
        
        # Load average
        loadavg = base_path / 'proc' / 'loadavg'
        if loadavg.exists():
            loadinfo['loadavg'] = loadavg.read_text().strip()
        
        # Uptime with load
        uptime_file = base_path / 'sos_commands' / 'general' / 'uptime'
        if uptime_file.exists():
            loadinfo['uptime'] = uptime_file.read_text().strip()
        
        return loadinfo
    except Exception as e:
        Logger.warning(f"Failed to get system load: {e}")
        return {}


def get_dmidecode_info(base_path: Path) -> dict:
    """Extract hardware info from dmidecode"""
    try:
        dmi = {}
        dmidecode = base_path / 'sos_commands' / 'hardware' / 'dmidecode'
        if not dmidecode.exists():
            dmidecode = base_path / 'dmidecode'
        
        if dmidecode.exists():
            content = dmidecode.read_text()
            lines = content.splitlines()
            
            # Extract system info
            in_system = False
            for line in lines:
                if 'System Information' in line:
                    in_system = True
                elif in_system:
                    if 'Manufacturer:' in line:
                        dmi['manufacturer'] = line.split(':', 1)[1].strip()
                    elif 'Product Name:' in line:
                        dmi['product'] = line.split(':', 1)[1].strip()
                    elif 'Serial Number:' in line:
                        dmi['serial'] = line.split(':', 1)[1].strip()
                    elif line.strip() == '':
                        break
        
        return dmi
    except Exception as e:
        Logger.warning(f"Failed to get dmidecode info: {e}")
        return {}


def get_system_resources(base_path: Path) -> dict:
    """Extract system resource information from sosreport"""
    resources = {}

    try:
        # Extract df -h output
        df_file = base_path / 'df'
        if df_file.exists():
            resources['df_h'] = df_file.read_text().strip()

        # Extract vmstat output (raw proc file)
        vmstat_file = base_path / 'proc' / 'vmstat'
        if vmstat_file.exists():
            vmstat_content = vmstat_file.read_text().strip()
            # Format it nicely for display (show first 10 lines)
            lines = vmstat_content.split('\n')[:10]
            resources['vmstat'] = '\n'.join(lines)

        # Extract free output
        free_file = base_path / 'free'
        if free_file.exists():
            resources['free'] = free_file.read_text().strip()

    except Exception as e:
        Logger.warning(f"Failed to get system resources: {e}")

    return resources


def get_top_processes(base_path: Path) -> dict:
    """Extract top CPU and memory consuming processes from sosreport"""
    processes = {'cpu': [], 'memory': []}

    try:
        # Use the detailed ps command output
        ps_file = base_path / 'sos_commands' / 'process' / 'ps_auxwwwm'
        if ps_file.exists():
            content = ps_file.read_text()
            lines = content.split('\n')

            for line in lines[1:]:  # Skip header
                line = line.strip()
                if not line:
                    continue

                # Parse ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split()
                if len(parts) >= 11:  # Need at least USER, PID, %CPU, %MEM, and COMMAND
                    try:
                        user = parts[0]
                        pid = parts[1]
                        cpu_pct = float(parts[2])
                        mem_pct = float(parts[3])
                        # Command starts from part 10 (after VSZ RSS TTY STAT START TIME)
                        cmd = ' '.join(parts[10:])

                        # Add to CPU list
                        processes['cpu'].append({
                            'cpu_pct': cpu_pct,
                            'pid': pid,
                            'user': user,
                            'cmd': cmd
                        })

                        # Add to memory list
                        processes['memory'].append({
                            'mem_pct': mem_pct,
                            'pid': pid,
                            'user': user,
                            'cmd': cmd
                        })

                    except (ValueError, IndexError):
                        continue

    except Exception as e:
        Logger.warning(f"Failed to get top processes: {e}")

    # Sort by usage and take top 10
    processes['cpu'] = sorted(processes['cpu'], key=lambda x: x['cpu_pct'], reverse=True)[:10]
    processes['memory'] = sorted(processes['memory'], key=lambda x: x['mem_pct'], reverse=True)[:10]

    return processes
