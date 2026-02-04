#!/usr/bin/env python3
"""SAR (System Activity Reporter) analyzer for sosreport"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import re
from utils.logger import Logger


class SarAnalyzer:
    """Analyze SAR data from /var/log/sa directory"""
    
    def analyze(self, base_path: Path) -> Dict[str, Any]:
        """Analyze SAR files from /var/log/sa directory"""
        Logger.debug("Analyzing SAR data")
        
        sa_dir = base_path / 'var' / 'log' / 'sa'
        
        if not sa_dir.exists():
            Logger.debug("SAR directory not found")
            return {'available': False}
        
        # Find all sar files (not sa files)
        sar_files = sorted([f for f in sa_dir.glob('sar*') if f.is_file()])
        
        if not sar_files:
            Logger.debug("No SAR files found")
            return {'available': False}
        
        Logger.debug(f"Found {len(sar_files)} SAR files")
        
        # Parse each SAR file
        sar_data = {}
        for sar_file in sar_files:
            day_number = self._extract_day_number(sar_file.name)
            if day_number:
                parsed_data = self._parse_sar_file(sar_file)
                if parsed_data:
                    sar_data[day_number] = {
                        'filename': sar_file.name,
                        'data': parsed_data
                    }
        
        if not sar_data:
            return {'available': False}
        
        # Get list of available days for navigation
        available_days = sorted(sar_data.keys())
        
        return {
            'available': True,
            'files': sar_data,
            'available_days': available_days,
            'total_days': len(available_days)
        }
    
    def _extract_day_number(self, filename: str) -> Optional[int]:
        """Extract day number from sar filename (e.g., sar29 -> 29)"""
        match = re.search(r'sar(\d+)', filename)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
    
    def _parse_sar_file(self, sar_file: Path) -> Dict[str, Any]:
        """Parse a single SAR file and extract metrics"""
        try:
            content = sar_file.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            Logger.warning(f"Failed to read SAR file {sar_file}: {e}")
            return {}
        
        parsed = {
            'header': None,
            'cpu': [],
            'load': [],
            'memory': [],
            'network': [],
            'disk': []
        }
        
        lines = content.split('\n')
        current_section = None
        section_headers = {}
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Parse header line
            if line.startswith('Linux ') and parsed['header'] is None:
                parsed['header'] = line
                i += 1
                continue
            
            # Detect section headers
            if 'CPU' in line and '%usr' in line:
                current_section = 'cpu'
                section_headers['cpu'] = line
                i += 1
                continue
            elif 'runq-sz' in line or 'ldavg' in line:
                current_section = 'load'
                section_headers['load'] = line
                i += 1
                continue
            elif 'kbmemfree' in line or 'memfree' in line or 'kbswpfree' in line:
                current_section = 'memory'
                section_headers['memory'] = line
                i += 1
                continue
            elif 'IFACE' in line or 'rxpck' in line or 'rxkB' in line:
                current_section = 'network'
                section_headers['network'] = line
                i += 1
                continue
            elif 'DEV' in line or 'tps' in line or 'rd_sec' in line:
                current_section = 'disk'
                section_headers['disk'] = line
                i += 1
                continue
            
            # Skip empty lines and average lines (we'll handle them separately)
            if not line or line.startswith('Average:'):
                i += 1
                continue
            
            # Parse data lines
            if current_section and line:
                # Check if line starts with time (HH:MM:SS format)
                time_match = re.match(r'^(\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    time_str = time_match.group(1)
                    data_line = self._parse_data_line(line, current_section)
                    if data_line:
                        data_line['time'] = time_str
                        parsed[current_section].append(data_line)
                # Also check for section transitions (new section headers)
                elif any(keyword in line for keyword in ['CPU', 'runq-sz', 'kbmemfree', 'IFACE', 'DEV']):
                    # This might be a new section starting, reset current_section
                    # But don't reset here, let the section detection above handle it
                    pass
            
            i += 1
        
        # Store section headers
        parsed['section_headers'] = section_headers
        
        return parsed
    
    def _parse_data_line(self, line: str, section: str) -> Optional[Dict[str, Any]]:
        """Parse a single data line based on section type"""
        parts = line.split()
        if len(parts) < 2:
            return None
        
        data = {}
        
        if section == 'cpu':
            # Format: HH:MM:SS CPU %usr %nice %sys %iowait %steal %irq %soft %guest %gnice %idle
            if len(parts) >= 11:
                try:
                    data['cpu'] = parts[1] if parts[1] != 'all' else 'all'
                    data['usr'] = float(parts[2])
                    data['nice'] = float(parts[3])
                    data['sys'] = float(parts[4])
                    data['iowait'] = float(parts[5])
                    data['steal'] = float(parts[6])
                    data['irq'] = float(parts[7])
                    data['soft'] = float(parts[8])
                    data['guest'] = float(parts[9])
                    data['gnice'] = float(parts[10])
                    data['idle'] = float(parts[11])
                    data['utilization'] = 100.0 - data['idle']  # Calculate utilization
                except (ValueError, IndexError):
                    return None
        
        elif section == 'load':
            # Format: HH:MM:SS runq-sz plist-sz ldavg-1 ldavg-5 ldavg-15 blocked
            if len(parts) >= 7:
                try:
                    data['runq_sz'] = int(parts[1])
                    data['plist_sz'] = int(parts[2])
                    data['ldavg_1'] = float(parts[3])
                    data['ldavg_5'] = float(parts[4])
                    data['ldavg_15'] = float(parts[5])
                    data['blocked'] = int(parts[6])
                except (ValueError, IndexError):
                    return None
        
        elif section == 'memory':
            # Format varies, common: HH:MM:SS kbmemfree kbavail kbmemused %memused kbbuffers kbcached kbcommit %commit kbactive kbinact kbdirty
            # Or: HH:MM:SS kbswpfree kbswpused %swpused kbswpcad
            if len(parts) >= 3:
                try:
                    # Store all numeric values as raw data
                    raw_values = []
                    for part in parts[1:]:
                        try:
                            # Try to convert to float
                            val = float(part)
                            raw_values.append(val)
                        except ValueError:
                            raw_values.append(part)
                    
                    data['raw'] = raw_values
                    
                    # Try to identify specific fields if we have enough data
                    if len(raw_values) >= 3:
                        # Common pattern: free, available, used
                        data['kbmemfree'] = raw_values[0] if isinstance(raw_values[0], (int, float)) else 0
                        if len(raw_values) > 1:
                            data['kbavail'] = raw_values[1] if isinstance(raw_values[1], (int, float)) else 0
                        if len(raw_values) > 2:
                            data['kbmemused'] = raw_values[2] if isinstance(raw_values[2], (int, float)) else 0
                except (ValueError, IndexError) as e:
                    Logger.debug(f"Error parsing memory line: {e}")
                    return None
        
        elif section == 'network':
            # Format: HH:MM:SS IFACE rxpck/s txpck/s rxkB/s txkB/s rxcmp/s txcmp/s rxmcst/s
            if len(parts) >= 3:
                try:
                    data['iface'] = parts[1]
                    if len(parts) >= 8:
                        data['rxpck'] = float(parts[2])
                        data['txpck'] = float(parts[3])
                        data['rxkB'] = float(parts[4])
                        data['txkB'] = float(parts[5])
                except (ValueError, IndexError):
                    return None
        
        elif section == 'disk':
            # Format: HH:MM:SS DEV tps rd_sec/s wr_sec/s avgrq-sz avgqu-sz await svctm %util
            if len(parts) >= 3:
                try:
                    data['device'] = parts[1]
                    if len(parts) >= 10:
                        data['tps'] = float(parts[2])
                        data['rd_sec'] = float(parts[3])
                        data['wr_sec'] = float(parts[4])
                        data['avgrq_sz'] = float(parts[5])
                        data['avgqu_sz'] = float(parts[6])
                        data['await'] = float(parts[7])
                        data['svctm'] = float(parts[8])
                        data['util'] = float(parts[9])
                except (ValueError, IndexError):
                    return None
        
        return data if data else None
