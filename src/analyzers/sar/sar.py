#!/usr/bin/env python3
"""SAR (System Activity Reporter) analyzer for sosreport and supportconfig"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from calendar import monthrange
import re
import lzma
import tempfile
from utils.logger import Logger


class SarAnalyzer:
    """Analyze SAR data from /var/log/sa directory"""
    
    # Section detection patterns - order matters for proper detection
    SECTION_PATTERNS = [
        # CPU Utilization - must check before other CPU patterns
        ('cpu', lambda l: 'CPU' in l and '%usr' in l and '%idle' in l),
        # Interrupt Statistics (INTR) - skip this section, just detect it
        ('intr', lambda l: 'INTR' in l and 'intr/s' in l),
        # Process Creation
        ('process', lambda l: 'proc/s' in l and 'cswch/s' in l),
        # Swap Paging (pswpin/s pswpout/s) - must be before general paging
        ('swap_paging', lambda l: 'pswpin/s' in l and 'pswpout/s' in l),
        # Paging Statistics  
        ('paging', lambda l: 'pgpgin/s' in l or ('fault/s' in l and 'pgfree/s' in l)),
        # I/O Transfer Rates
        ('io_transfer', lambda l: ('tps' in l and 'bread/s' in l) or ('rtps' in l and 'wtps' in l)),
        # Memory Utilization
        ('memory', lambda l: 'kbmemfree' in l and 'kbmemused' in l),
        # Swap Utilization
        ('swap', lambda l: 'kbswpfree' in l and 'kbswpused' in l),
        # Hugepages Utilization
        ('hugepages', lambda l: 'kbhugfree' in l and 'kbhugused' in l),
        # Filesystem Utilization
        ('filesystem', lambda l: 'dentunusd' in l or 'file-nr' in l),
        # Load Average
        ('load', lambda l: 'runq-sz' in l and 'ldavg-1' in l),
        # Serial/TTY
        ('tty', lambda l: 'TTY' in l and 'rcvin/s' in l),
        # Block Device Statistics
        ('block_device', lambda l: 'DEV' in l and '%util' in l and 'await' in l),
        # Network Interface Stats
        ('network', lambda l: 'IFACE' in l and 'rxpck/s' in l and '%ifutil' in l),
        # Network Error Stats
        ('network_errors', lambda l: 'IFACE' in l and 'rxerr/s' in l),
        # NFS Client RPC Stats
        ('nfs_client', lambda l: 'call/s' in l and 'retrans/s' in l and 'read/s' in l and 'scall/s' not in l),
        # NFS Server RPC Stats
        ('nfs_server', lambda l: 'scall/s' in l and 'badcall/s' in l),
        # Socket Usage
        ('sockets', lambda l: 'totsck' in l and 'tcpsck' in l),
        # Softnet Stats
        ('softnet', lambda l: 'CPU' in l and 'total/s' in l and 'dropd/s' in l),
        # IP Statistics (skip - just detect to avoid misparsing)
        ('ip_stats', lambda l: 'irec/s' in l and 'fwddgm/s' in l),
        # IP Error Statistics (skip)
        ('ip_errors', lambda l: 'ihdrerr/s' in l or 'iadrerr/s' in l),
        # ICMP Statistics (skip)
        ('icmp_stats', lambda l: 'imsg/s' in l and 'omsg/s' in l),
        # ICMP Error Statistics (skip)
        ('icmp_errors', lambda l: 'ierr/s' in l and 'oerr/s' in l and 'idstunr/s' in l),
        # TCP Statistics (skip)
        ('tcp_stats', lambda l: 'active/s' in l and 'passive/s' in l and 'iseg/s' in l),
        # TCP Error Statistics (skip)
        ('tcp_errors', lambda l: 'atmptf/s' in l or 'estres/s' in l),
        # UDP Statistics (skip)
        ('udp_stats', lambda l: 'idgm/s' in l and 'odgm/s' in l and 'noport/s' in l),
        # IPv6 Statistics (skip)
        ('ipv6_stats', lambda l: 'irec6/s' in l or 'fwddgm6/s' in l),
        # IPv6 Error Statistics (skip)
        ('ipv6_errors', lambda l: 'ihdrer6/s' in l or 'iadrer6/s' in l),
        # ICMPv6 Statistics (skip)
        ('icmpv6_stats', lambda l: 'imsg6/s' in l and 'omsg6/s' in l),
        # UDP6 Statistics (skip)
        ('udp6_stats', lambda l: 'idgm6/s' in l and 'odgm6/s' in l),
    ]
    
    def analyze(self, base_path: Path, allowed_files: list | None = None) -> Dict[str, Any]:
        """
        Analyze SAR files from sosreport or supportconfig.

        Args:
            base_path:     Root of the extracted bundle.
            allowed_files: Optional list of bare filenames to include (e.g.
                           ['sar20251118.xz', 'sar20251119.xz']).  Pass an
                           empty list to skip SAR entirely.  None = no filter.

        Supports two formats:
        - SOSReport: /var/log/sa/sar* (uncompressed, day number in filename)
        - Supportconfig: /sar/sar* (compressed .xz or uncompressed, full date in filename)
        """
        Logger.info("Analyzing SAR data")

        # Detect format and find SAR files
        format_type, sar_files = self._find_sar_files(base_path)

        if not sar_files:
            Logger.debug("No SAR files found")
            return {'available': False}

        # Apply per-file filter when the caller supplied an explicit list
        if allowed_files is not None:
            sar_files = [(f, c) for f, c in sar_files if f.name in allowed_files]
            if not sar_files:
                Logger.debug("SAR analysis skipped: no files remain after applying filter")
                return {'available': False}

        Logger.debug(f"Found {len(sar_files)} SAR files ({format_type} format)")
        
        # Get collection date for sosreport (supportconfig has date in filename/header)
        collection_date = None
        if format_type == 'sosreport':
            collection_date = self._get_collection_date(base_path)
            Logger.debug(f"Collection date: {collection_date}")
        
        # Parse each SAR file
        sar_data = {}
        for sar_file, is_compressed in sar_files:
            if format_type == 'supportconfig':
                # Supportconfig: parse using dedicated method
                parsed_data = self._parse_supportconfig_sar_file(sar_file, compressed=is_compressed)
                if parsed_data:
                    # Extract date from header or filename
                    file_date = parsed_data.get('file_date')
                    if file_date:
                        day_key = int(file_date.strftime('%Y%m%d'))  # Use full date as key
                        # Remove file_date from data to avoid JSON serialization issues
                        parsed_data.pop('file_date', None)
                        sar_data[day_key] = {
                            'filename': sar_file.name,
                            'data': parsed_data,
                            'date': file_date.strftime('%Y-%m-%d'),
                            'date_display': file_date.strftime('%b %d, %Y')
                        }
            else:
                # SOSReport: day number in filename
                day_number = self._extract_day_number(sar_file.name)
                if day_number:
                    parsed_data = self._parse_sar_file(sar_file, compressed=False)
                    if parsed_data:
                        # Calculate actual date for this SAR file
                        actual_date = self._calculate_sar_date(day_number, collection_date)
                        sar_data[day_number] = {
                            'filename': sar_file.name,
                            'data': parsed_data,
                            'date': actual_date.strftime('%Y-%m-%d') if actual_date else None,
                            'date_display': actual_date.strftime('%b %d, %Y') if actual_date else f'Day {day_number}'
                        }
        
        if not sar_data:
            return {'available': False}
        
        # Get list of available days for navigation (sorted by actual date)
        available_days = sorted(sar_data.keys(), 
                               key=lambda d: sar_data[d].get('date') or str(d))
        
        return {
            'available': True,
            'files': sar_data,
            'available_days': available_days,
            'total_days': len(available_days),
            'collection_date': collection_date.strftime('%Y-%m-%d') if collection_date else None,
            'format': format_type
        }
    
    def _find_sar_files(self, base_path: Path) -> Tuple[str, List[Tuple[Path, bool]]]:
        """
        Find SAR files in the extracted archive.
        
        Returns:
            Tuple of (format_type, list of (sar_file_path, is_compressed) tuples)
        """
        # Check for supportconfig format first (sar/ directory)
        scc_sar_dir = base_path / 'sar'
        if scc_sar_dir.exists():
            sar_files = []
            # Look for both compressed (.xz) and uncompressed files
            for f in scc_sar_dir.iterdir():
                if f.is_file() and f.name.startswith('sar'):
                    # Match sar files with date pattern (sarYYYYMMDD or sarYYYYMMDD.xz)
                    if re.match(r'sar\d{8}(\.xz)?$', f.name):
                        is_compressed = f.suffix == '.xz'
                        sar_files.append((f, is_compressed))
            
            if sar_files:
                # Sort by filename (which contains date)
                sar_files.sort(key=lambda x: x[0].name)
                Logger.debug(f"Found {len(sar_files)} supportconfig SAR files")
                return ('supportconfig', sar_files)
        
        # Check for sosreport format (/var/log/sa/)
        sos_sa_dir = base_path / 'var' / 'log' / 'sa'
        if sos_sa_dir.exists():
            sar_files = []
            for f in sos_sa_dir.iterdir():
                if f.is_file() and f.name.startswith('sar'):
                    # Match sar files with day number pattern (sar01, sar02, etc.)
                    if re.match(r'sar\d{1,2}$', f.name):
                        sar_files.append((f, False))  # sosreport files are not compressed
            
            if sar_files:
                # Sort by day number
                sar_files.sort(key=lambda x: int(re.search(r'sar(\d+)', x[0].name).group(1)))
                Logger.debug(f"Found {len(sar_files)} sosreport SAR files")
                return ('sosreport', sar_files)
        
        return ('unknown', [])
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """
        Extract date from supportconfig SAR filename.
        
        Filename format: sar20251118.xz -> 2025-11-18
        """
        # Remove .xz extension if present
        name = filename.replace('.xz', '')
        
        # Match sarYYYYMMDD format
        match = re.search(r'sar(\d{8})', name)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                Logger.debug(f"Invalid date in filename: {filename}")
        
        return None
    
    def _get_collection_date(self, base_path: Path) -> Optional[datetime]:
        """
        Get the collection date from the sosreport/supportconfig.
        
        Tries multiple sources:
        1. sos_commands/date/date_--utc (sosreport)
        2. basic-environment.txt (supportconfig) 
        3. date.txt (supportconfig)
        """
        # Try sosreport date file
        date_file = base_path / 'sos_commands' / 'date' / 'date_--utc'
        if date_file.exists():
            try:
                content = date_file.read_text(encoding='utf-8', errors='ignore').strip()
                # Format: "Tue Dec 16 12:01:36 UTC 2025"
                # Parse: weekday month day time timezone year
                parsed = datetime.strptime(content, '%a %b %d %H:%M:%S %Z %Y')
                return parsed
            except (ValueError, OSError) as e:
                Logger.debug(f"Failed to parse date file: {e}")
        
        # Try alternate sosreport date file (without UTC)
        date_file_alt = base_path / 'sos_commands' / 'date' / 'date'
        if date_file_alt.exists():
            try:
                content = date_file_alt.read_text(encoding='utf-8', errors='ignore').strip()
                # Try various date formats
                for fmt in ['%a %b %d %H:%M:%S %Z %Y', '%a %b %d %H:%M:%S %Y']:
                    try:
                        parsed = datetime.strptime(content, fmt)
                        return parsed
                    except ValueError:
                        continue
            except OSError as e:
                Logger.debug(f"Failed to read alt date file: {e}")
        
        # Try supportconfig basic-environment.txt
        basic_env = base_path / 'basic-environment.txt'
        if basic_env.exists():
            try:
                content = basic_env.read_text(encoding='utf-8', errors='ignore')
                # Look for date line like "# /bin/date"
                for line in content.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        # Try to parse as date
                        for fmt in ['%a %b %d %H:%M:%S %Z %Y', '%a %b %d %H:%M:%S %Y']:
                            try:
                                parsed = datetime.strptime(line.strip(), fmt)
                                return parsed
                            except ValueError:
                                continue
            except OSError as e:
                Logger.debug(f"Failed to read basic-environment.txt: {e}")
        
        Logger.debug("Could not determine collection date")
        return None
    
    def _calculate_sar_date(self, day_number: int, collection_date: Optional[datetime]) -> Optional[datetime]:
        """
        Calculate the actual date for a SAR file based on its day number.
        
        SAR files are named by day of month (sar01-sar31).
        If day_number > collection_day, it's from the previous month.
        """
        if not collection_date:
            return None
        
        collection_day = collection_date.day
        collection_month = collection_date.month
        collection_year = collection_date.year
        
        if day_number <= collection_day:
            # Same month as collection
            try:
                return datetime(collection_year, collection_month, day_number)
            except ValueError:
                # Invalid day for this month
                return None
        else:
            # Previous month
            if collection_month == 1:
                prev_month = 12
                prev_year = collection_year - 1
            else:
                prev_month = collection_month - 1
                prev_year = collection_year
            
            # Validate the day exists in previous month
            _, max_day = monthrange(prev_year, prev_month)
            if day_number <= max_day:
                try:
                    return datetime(prev_year, prev_month, day_number)
                except ValueError:
                    return None
            else:
                return None
    
    def _extract_day_number(self, filename: str) -> Optional[int]:
        """Extract day number from sar filename (e.g., sar29 -> 29)"""
        match = re.search(r'sar(\d+)', filename)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
    
    def _detect_section(self, line: str) -> Optional[str]:
        """Detect section type from header line"""
        for section_name, pattern_func in self.SECTION_PATTERNS:
            if pattern_func(line):
                return section_name
        return None
    
    def _read_sar_content(self, sar_file: Path, compressed: bool = False) -> Optional[str]:
        """
        Read SAR file content, handling both compressed and uncompressed files.
        
        Args:
            sar_file: Path to the SAR file
            compressed: Whether the file is xz compressed
            
        Returns:
            File content as string, or None on error
        """
        try:
            if compressed:
                # Decompress xz file
                with lzma.open(sar_file, 'rt', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                return sar_file.read_text(encoding='utf-8', errors='ignore')
        except lzma.LZMAError as e:
            Logger.warning(f"Failed to decompress SAR file {sar_file}: {e}")
            return None
        except Exception as e:
            Logger.warning(f"Failed to read SAR file {sar_file}: {e}")
            return None
    
    def _parse_supportconfig_sar_file(self, sar_file: Path, compressed: bool = False) -> Dict[str, Any]:
        """
        Parse a supportconfig SAR file and extract metrics.
        
        Supportconfig SAR files have a different format:
        - Header contains date: Linux 5.14.21-... (hostname) 	2025-12-11 	_x86_64_	(2 CPU)
        - Device names are like dev8-0 instead of sda
        - Date is embedded in the header line or filename
        
        Args:
            sar_file: Path to the SAR file
            compressed: Whether the file is xz compressed
        """
        content = self._read_sar_content(sar_file, compressed)
        if not content:
            return {}
        
        parsed = {
            'header': None,
            'file_date': None,
            'cpu': [],
            'intr': [],  # Interrupt stats - not charted but detected to avoid misparsing
            'process': [],
            'swap_paging': [],
            'paging': [],
            'io_transfer': [],
            'memory': [],
            'swap': [],
            'hugepages': [],
            'filesystem': [],
            'load': [],
            'tty': [],
            'block_device': [],
            'network': [],
            'network_errors': [],
            'nfs_client': [],
            'nfs_server': [],
            'sockets': [],
            'softnet': []
        }
        
        lines = content.split('\n')
        current_section = None
        section_headers = {}
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Parse header line and extract date
            # Format: Linux 5.14.21-150500.55.124-default (azlibppw1ap01) 	2025-12-11 	_x86_64_	(2 CPU)
            if line.startswith('Linux ') and parsed['header'] is None:
                parsed['header'] = line
                # Extract date from header
                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', line)
                if date_match:
                    try:
                        parsed['file_date'] = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    except ValueError:
                        pass
                
                # If no date in header, try to extract from filename
                if not parsed['file_date']:
                    parsed['file_date'] = self._extract_date_from_filename(sar_file.name)
                
                i += 1
                continue
            
            # Skip empty lines and average lines
            if not line or line.startswith('Average:'):
                i += 1
                continue
            
            # Try to detect section header
            detected_section = self._detect_section(line)
            if detected_section:
                current_section = detected_section
                section_headers[current_section] = line
                i += 1
                continue
            
            # Parse data lines
            if current_section and line:
                # Check if line starts with time (HH:MM:SS format)
                time_match = re.match(r'^(\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    time_str = time_match.group(1)
                    data_line = self._parse_supportconfig_data_line(line, current_section)
                    if data_line:
                        data_line['time'] = time_str
                        parsed[current_section].append(data_line)
            
            i += 1
        
        # Store section headers
        parsed['section_headers'] = section_headers
        
        return parsed
    
    def _parse_supportconfig_data_line(self, line: str, section: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single data line from supportconfig SAR format.
        
        Supportconfig SAR format may have slightly different column layouts
        for some sections (e.g., block_device uses dev8-0 style names).
        """
        parts = line.split()
        if len(parts) < 2:
            return None
        
        data = {}
        
        try:
            if section == 'cpu':
                # Format: HH:MM:SS CPU %usr %nice %sys %iowait %steal %irq %soft %guest %gnice %idle
                if len(parts) >= 12:
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
                    data['utilization'] = 100.0 - data['idle']
                    
            elif section == 'process':
                # Format: HH:MM:SS proc/s cswch/s
                if len(parts) >= 3:
                    data['proc_s'] = float(parts[1])
                    data['cswch_s'] = float(parts[2])
            
            elif section == 'swap_paging':
                # Format: HH:MM:SS pswpin/s pswpout/s
                if len(parts) >= 3:
                    data['pswpin_s'] = float(parts[1])
                    data['pswpout_s'] = float(parts[2])
                    
            elif section == 'paging':
                # Format: HH:MM:SS pgpgin/s pgpgout/s fault/s majflt/s pgfree/s pgscank/s pgscand/s pgsteal/s %vmeff
                if len(parts) >= 10:
                    data['pgpgin_s'] = float(parts[1])
                    data['pgpgout_s'] = float(parts[2])
                    data['fault_s'] = float(parts[3])
                    data['majflt_s'] = float(parts[4])
                    data['pgfree_s'] = float(parts[5])
                    data['pgscank_s'] = float(parts[6])
                    data['pgscand_s'] = float(parts[7])
                    data['pgsteal_s'] = float(parts[8])
                    data['vmeff'] = float(parts[9])
                    
            elif section == 'io_transfer':
                # Format: HH:MM:SS tps rtps wtps bread/s bwrtn/s
                if len(parts) >= 6:
                    data['tps'] = float(parts[1])
                    data['rtps'] = float(parts[2])
                    data['wtps'] = float(parts[3])
                    data['bread_s'] = float(parts[4])
                    data['bwrtn_s'] = float(parts[5])
                    
            elif section == 'memory':
                # Format: HH:MM:SS kbmemfree kbavail kbmemused %memused kbbuffers kbcached kbcommit %commit kbactive kbinact kbdirty kbanonpg kbslab kbkstack kbpgtbl kbvmused
                if len(parts) >= 17:
                    data['kbmemfree'] = float(parts[1])
                    data['kbavail'] = float(parts[2])
                    data['kbmemused'] = float(parts[3])
                    data['memused_pct'] = float(parts[4])
                    data['kbbuffers'] = float(parts[5])
                    data['kbcached'] = float(parts[6])
                    data['kbcommit'] = float(parts[7])
                    data['commit_pct'] = float(parts[8])
                    data['kbactive'] = float(parts[9])
                    data['kbinact'] = float(parts[10])
                    data['kbdirty'] = float(parts[11])
                elif len(parts) >= 5:
                    # Minimal memory format
                    data['kbmemfree'] = float(parts[1])
                    data['kbavail'] = float(parts[2]) if len(parts) > 2 else 0
                    data['kbmemused'] = float(parts[3]) if len(parts) > 3 else 0
                    data['memused_pct'] = float(parts[4]) if len(parts) > 4 else 0
                    
            elif section == 'swap':
                # Format: HH:MM:SS kbswpfree kbswpused %swpused kbswpcad %swpcad
                if len(parts) >= 6:
                    data['kbswpfree'] = float(parts[1])
                    data['kbswpused'] = float(parts[2])
                    data['swpused_pct'] = float(parts[3])
                    data['kbswpcad'] = float(parts[4])
                    data['swpcad_pct'] = float(parts[5])
                    
            elif section == 'hugepages':
                # Format: HH:MM:SS kbhugfree kbhugused %hugused
                if len(parts) >= 4:
                    data['kbhugfree'] = float(parts[1])
                    data['kbhugused'] = float(parts[2])
                    data['hugused_pct'] = float(parts[3])
                    
            elif section == 'filesystem':
                # Format: HH:MM:SS dentunusd file-nr inode-nr pty-nr
                if len(parts) >= 5:
                    data['dentunusd'] = int(parts[1])
                    data['file_nr'] = int(parts[2])
                    data['inode_nr'] = int(parts[3])
                    data['pty_nr'] = int(parts[4])
                    
            elif section == 'load':
                # Format: HH:MM:SS runq-sz plist-sz ldavg-1 ldavg-5 ldavg-15 blocked
                if len(parts) >= 7:
                    data['runq_sz'] = int(parts[1])
                    data['plist_sz'] = int(parts[2])
                    data['ldavg_1'] = float(parts[3])
                    data['ldavg_5'] = float(parts[4])
                    data['ldavg_15'] = float(parts[5])
                    data['blocked'] = int(parts[6])
                    
            elif section == 'tty':
                # Format: HH:MM:SS TTY rcvin/s txmtin/s framerr/s prtyerr/s brk/s ovrun/s
                if len(parts) >= 8:
                    data['tty'] = parts[1]
                    data['rcvin_s'] = float(parts[2])
                    data['txmtin_s'] = float(parts[3])
                    data['framerr_s'] = float(parts[4])
                    data['prtyerr_s'] = float(parts[5])
                    data['brk_s'] = float(parts[6])
                    data['ovrun_s'] = float(parts[7])
                    
            elif section == 'block_device':
                # Supportconfig format: HH:MM:SS DEV tps rkB/s wkB/s areq-sz aqu-sz await svctm %util
                # Device names are like dev8-0, dev8-16, dev254-0, etc.
                if len(parts) >= 10:
                    data['device'] = parts[1]  # e.g., dev8-0
                    data['tps'] = float(parts[2])
                    data['rkB_s'] = float(parts[3])
                    data['wkB_s'] = float(parts[4])
                    data['areq_sz'] = float(parts[5])
                    data['aqu_sz'] = float(parts[6])
                    data['await'] = float(parts[7])
                    data['svctm'] = float(parts[8])
                    data['util'] = float(parts[9])
                    
            elif section == 'network':
                # Format: HH:MM:SS IFACE rxpck/s txpck/s rxkB/s txkB/s rxcmp/s txcmp/s rxmcst/s %ifutil
                if len(parts) >= 10:
                    data['iface'] = parts[1]
                    data['rxpck_s'] = float(parts[2])
                    data['txpck_s'] = float(parts[3])
                    data['rxkB_s'] = float(parts[4])
                    data['txkB_s'] = float(parts[5])
                    data['rxcmp_s'] = float(parts[6])
                    data['txcmp_s'] = float(parts[7])
                    data['rxmcst_s'] = float(parts[8])
                    data['ifutil'] = float(parts[9])
                    
            elif section == 'network_errors':
                # Format: HH:MM:SS IFACE rxerr/s txerr/s coll/s rxdrop/s txdrop/s txcarr/s rxfram/s rxfifo/s txfifo/s
                if len(parts) >= 11:
                    data['iface'] = parts[1]
                    data['rxerr_s'] = float(parts[2])
                    data['txerr_s'] = float(parts[3])
                    data['coll_s'] = float(parts[4])
                    data['rxdrop_s'] = float(parts[5])
                    data['txdrop_s'] = float(parts[6])
                    data['txcarr_s'] = float(parts[7])
                    data['rxfram_s'] = float(parts[8])
                    data['rxfifo_s'] = float(parts[9])
                    data['txfifo_s'] = float(parts[10])
                    
            elif section == 'nfs_client':
                # Format: HH:MM:SS call/s retrans/s read/s write/s access/s getatt/s
                if len(parts) >= 7:
                    data['call_s'] = float(parts[1])
                    data['retrans_s'] = float(parts[2])
                    data['read_s'] = float(parts[3])
                    data['write_s'] = float(parts[4])
                    data['access_s'] = float(parts[5])
                    data['getatt_s'] = float(parts[6])
                    
            elif section == 'nfs_server':
                # Format: HH:MM:SS scall/s badcall/s packet/s udp/s tcp/s hit/s miss/s sread/s swrite/s saccess/s sgetatt/s
                if len(parts) >= 12:
                    data['scall_s'] = float(parts[1])
                    data['badcall_s'] = float(parts[2])
                    data['packet_s'] = float(parts[3])
                    data['udp_s'] = float(parts[4])
                    data['tcp_s'] = float(parts[5])
                    data['hit_s'] = float(parts[6])
                    data['miss_s'] = float(parts[7])
                    data['sread_s'] = float(parts[8])
                    data['swrite_s'] = float(parts[9])
                    data['saccess_s'] = float(parts[10])
                    data['sgetatt_s'] = float(parts[11])
                    
            elif section == 'sockets':
                # Format: HH:MM:SS totsck tcpsck udpsck rawsck ip-frag tcp-tw
                if len(parts) >= 7:
                    data['totsck'] = int(parts[1])
                    data['tcpsck'] = int(parts[2])
                    data['udpsck'] = int(parts[3])
                    data['rawsck'] = int(parts[4])
                    data['ip_frag'] = int(parts[5])
                    data['tcp_tw'] = int(parts[6])
                    
            elif section == 'softnet':
                # Format: HH:MM:SS CPU total/s dropd/s squeezd/s rx_rps/s flw_lim/s
                if len(parts) >= 7:
                    data['cpu'] = parts[1] if parts[1] != 'all' else 'all'
                    data['total_s'] = float(parts[2])
                    data['dropd_s'] = float(parts[3])
                    data['squeezd_s'] = float(parts[4])
                    data['rx_rps_s'] = float(parts[5])
                    data['flw_lim_s'] = float(parts[6])
                    
        except (ValueError, IndexError) as e:
            Logger.debug(f"Error parsing supportconfig {section} line: {e}")
            return None
        
        return data if data else None
    
    def _parse_sar_file(self, sar_file: Path, compressed: bool = False) -> Dict[str, Any]:
        """
        Parse a single SAR file and extract metrics.
        
        Args:
            sar_file: Path to the SAR file
            compressed: Whether the file is xz compressed (supportconfig format)
        """
        content = self._read_sar_content(sar_file, compressed)
        if not content:
            return {}
        
        parsed = {
            'header': None,
            'cpu': [],
            'intr': [],  # Interrupt stats - not charted but detected to avoid misparsing
            'process': [],
            'swap_paging': [],
            'paging': [],
            'io_transfer': [],
            'memory': [],
            'swap': [],
            'hugepages': [],
            'filesystem': [],
            'load': [],
            'tty': [],
            'block_device': [],
            'network': [],
            'network_errors': [],
            'nfs_client': [],
            'nfs_server': [],
            'sockets': [],
            'softnet': []
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
            
            # Skip empty lines and average lines
            if not line or line.startswith('Average:'):
                i += 1
                continue
            
            # Try to detect section header
            detected_section = self._detect_section(line)
            if detected_section:
                current_section = detected_section
                section_headers[current_section] = line
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
        
        try:
            if section == 'cpu':
                # Format: HH:MM:SS CPU %usr %nice %sys %iowait %steal %irq %soft %guest %gnice %idle
                if len(parts) >= 12:
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
                    data['utilization'] = 100.0 - data['idle']
                    
            elif section == 'process':
                # Format: HH:MM:SS proc/s cswch/s
                if len(parts) >= 3:
                    data['proc_s'] = float(parts[1])
                    data['cswch_s'] = float(parts[2])
            
            elif section == 'swap_paging':
                # Format: HH:MM:SS pswpin/s pswpout/s
                if len(parts) >= 3:
                    data['pswpin_s'] = float(parts[1])
                    data['pswpout_s'] = float(parts[2])
                    
            elif section == 'paging':
                # Format: HH:MM:SS pgpgin/s pgpgout/s fault/s majflt/s pgfree/s pgscank/s pgscand/s pgsteal/s %vmeff
                if len(parts) >= 10:
                    data['pgpgin_s'] = float(parts[1])
                    data['pgpgout_s'] = float(parts[2])
                    data['fault_s'] = float(parts[3])
                    data['majflt_s'] = float(parts[4])
                    data['pgfree_s'] = float(parts[5])
                    data['pgscank_s'] = float(parts[6])
                    data['pgscand_s'] = float(parts[7])
                    data['pgsteal_s'] = float(parts[8])
                    data['vmeff'] = float(parts[9])
                    
            elif section == 'io_transfer':
                # Format: HH:MM:SS tps rtps wtps bread/s bwrtn/s
                if len(parts) >= 6:
                    data['tps'] = float(parts[1])
                    data['rtps'] = float(parts[2])
                    data['wtps'] = float(parts[3])
                    data['bread_s'] = float(parts[4])
                    data['bwrtn_s'] = float(parts[5])
                    
            elif section == 'memory':
                # Format: HH:MM:SS kbmemfree kbavail kbmemused %memused kbbuffers kbcached kbcommit %commit kbactive kbinact kbdirty kbanonpg kbslab kbkstack kbpgtbl kbvmused
                if len(parts) >= 17:
                    data['kbmemfree'] = float(parts[1])
                    data['kbavail'] = float(parts[2])
                    data['kbmemused'] = float(parts[3])
                    data['memused_pct'] = float(parts[4])
                    data['kbbuffers'] = float(parts[5])
                    data['kbcached'] = float(parts[6])
                    data['kbcommit'] = float(parts[7])
                    data['commit_pct'] = float(parts[8])
                    data['kbactive'] = float(parts[9])
                    data['kbinact'] = float(parts[10])
                    data['kbdirty'] = float(parts[11])
                elif len(parts) >= 5:
                    # Minimal memory format
                    data['kbmemfree'] = float(parts[1])
                    data['kbavail'] = float(parts[2]) if len(parts) > 2 else 0
                    data['kbmemused'] = float(parts[3]) if len(parts) > 3 else 0
                    data['memused_pct'] = float(parts[4]) if len(parts) > 4 else 0
                    
            elif section == 'swap':
                # Format: HH:MM:SS kbswpfree kbswpused %swpused kbswpcad %swpcad
                if len(parts) >= 6:
                    data['kbswpfree'] = float(parts[1])
                    data['kbswpused'] = float(parts[2])
                    data['swpused_pct'] = float(parts[3])
                    data['kbswpcad'] = float(parts[4])
                    data['swpcad_pct'] = float(parts[5])
                    
            elif section == 'hugepages':
                # Format: HH:MM:SS kbhugfree kbhugused %hugused
                if len(parts) >= 4:
                    data['kbhugfree'] = float(parts[1])
                    data['kbhugused'] = float(parts[2])
                    data['hugused_pct'] = float(parts[3])
                    
            elif section == 'filesystem':
                # Format: HH:MM:SS dentunusd file-nr inode-nr pty-nr
                if len(parts) >= 5:
                    data['dentunusd'] = int(parts[1])
                    data['file_nr'] = int(parts[2])
                    data['inode_nr'] = int(parts[3])
                    data['pty_nr'] = int(parts[4])
                    
            elif section == 'load':
                # Format: HH:MM:SS runq-sz plist-sz ldavg-1 ldavg-5 ldavg-15 blocked
                if len(parts) >= 7:
                    data['runq_sz'] = int(parts[1])
                    data['plist_sz'] = int(parts[2])
                    data['ldavg_1'] = float(parts[3])
                    data['ldavg_5'] = float(parts[4])
                    data['ldavg_15'] = float(parts[5])
                    data['blocked'] = int(parts[6])
                    
            elif section == 'tty':
                # Format: HH:MM:SS TTY rcvin/s txmtin/s framerr/s prtyerr/s brk/s ovrun/s
                if len(parts) >= 8:
                    data['tty'] = parts[1]
                    data['rcvin_s'] = float(parts[2])
                    data['txmtin_s'] = float(parts[3])
                    data['framerr_s'] = float(parts[4])
                    data['prtyerr_s'] = float(parts[5])
                    data['brk_s'] = float(parts[6])
                    data['ovrun_s'] = float(parts[7])
                    
            elif section == 'block_device':
                # Format: HH:MM:SS DEV tps rkB/s wkB/s areq-sz aqu-sz await svctm %util
                if len(parts) >= 10:
                    data['device'] = parts[1]
                    data['tps'] = float(parts[2])
                    data['rkB_s'] = float(parts[3])
                    data['wkB_s'] = float(parts[4])
                    data['areq_sz'] = float(parts[5])
                    data['aqu_sz'] = float(parts[6])
                    data['await'] = float(parts[7])
                    data['svctm'] = float(parts[8])
                    data['util'] = float(parts[9])
                    
            elif section == 'network':
                # Format: HH:MM:SS IFACE rxpck/s txpck/s rxkB/s txkB/s rxcmp/s txcmp/s rxmcst/s %ifutil
                if len(parts) >= 10:
                    data['iface'] = parts[1]
                    data['rxpck_s'] = float(parts[2])
                    data['txpck_s'] = float(parts[3])
                    data['rxkB_s'] = float(parts[4])
                    data['txkB_s'] = float(parts[5])
                    data['rxcmp_s'] = float(parts[6])
                    data['txcmp_s'] = float(parts[7])
                    data['rxmcst_s'] = float(parts[8])
                    data['ifutil'] = float(parts[9])
                    
            elif section == 'network_errors':
                # Format: HH:MM:SS IFACE rxerr/s txerr/s coll/s rxdrop/s txdrop/s txcarr/s rxfram/s rxfifo/s txfifo/s
                if len(parts) >= 11:
                    data['iface'] = parts[1]
                    data['rxerr_s'] = float(parts[2])
                    data['txerr_s'] = float(parts[3])
                    data['coll_s'] = float(parts[4])
                    data['rxdrop_s'] = float(parts[5])
                    data['txdrop_s'] = float(parts[6])
                    data['txcarr_s'] = float(parts[7])
                    data['rxfram_s'] = float(parts[8])
                    data['rxfifo_s'] = float(parts[9])
                    data['txfifo_s'] = float(parts[10])
                    
            elif section == 'nfs_client':
                # Format: HH:MM:SS call/s retrans/s read/s write/s access/s getatt/s
                if len(parts) >= 7:
                    data['call_s'] = float(parts[1])
                    data['retrans_s'] = float(parts[2])
                    data['read_s'] = float(parts[3])
                    data['write_s'] = float(parts[4])
                    data['access_s'] = float(parts[5])
                    data['getatt_s'] = float(parts[6])
                    
            elif section == 'nfs_server':
                # Format: HH:MM:SS scall/s badcall/s packet/s udp/s tcp/s hit/s miss/s sread/s swrite/s saccess/s sgetatt/s
                if len(parts) >= 12:
                    data['scall_s'] = float(parts[1])
                    data['badcall_s'] = float(parts[2])
                    data['packet_s'] = float(parts[3])
                    data['udp_s'] = float(parts[4])
                    data['tcp_s'] = float(parts[5])
                    data['hit_s'] = float(parts[6])
                    data['miss_s'] = float(parts[7])
                    data['sread_s'] = float(parts[8])
                    data['swrite_s'] = float(parts[9])
                    data['saccess_s'] = float(parts[10])
                    data['sgetatt_s'] = float(parts[11])
                    
            elif section == 'sockets':
                # Format: HH:MM:SS totsck tcpsck udpsck rawsck ip-frag tcp-tw
                if len(parts) >= 7:
                    data['totsck'] = int(parts[1])
                    data['tcpsck'] = int(parts[2])
                    data['udpsck'] = int(parts[3])
                    data['rawsck'] = int(parts[4])
                    data['ip_frag'] = int(parts[5])
                    data['tcp_tw'] = int(parts[6])
                    
            elif section == 'softnet':
                # Format: HH:MM:SS CPU total/s dropd/s squeezd/s rx_rps/s flw_lim/s
                if len(parts) >= 7:
                    data['cpu'] = parts[1] if parts[1] != 'all' else 'all'
                    data['total_s'] = float(parts[2])
                    data['dropd_s'] = float(parts[3])
                    data['squeezd_s'] = float(parts[4])
                    data['rx_rps_s'] = float(parts[5])
                    data['flw_lim_s'] = float(parts[6])
                    
        except (ValueError, IndexError) as e:
            Logger.debug(f"Error parsing {section} line: {e}")
            return None
        
        return data if data else None
