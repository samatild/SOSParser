#!/usr/bin/env python3
"""File operation utilities for SOSReport analyzer"""

import re
import tarfile
import gzip
import bz2
from datetime import datetime
from pathlib import Path
from utils.logger import Logger


def extract_tarball(tarball_path: Path, extract_to: Path) -> Path:
    """
    Extract a tarball (tar, tar.gz, tar.xz, tar.bz2) to target directory.
    Returns the path to the extracted sosreport directory.
    """
    Logger.info(f"Extracting tarball: {tarball_path}")
    
    try:
        with tarfile.open(tarball_path, 'r:*') as tar:
            # Filter members to prevent Tar Slip / path traversal attacks
            resolved_base = extract_to.resolve()
            safe_members = []
            for member in tar.getmembers():
                member_dest = (resolved_base / member.name).resolve()
                try:
                    member_dest.relative_to(resolved_base)
                    safe_members.append(member)
                except ValueError:
                    Logger.error(f"Skipping potentially malicious tar entry: {member.name!r}")

            # Extract only the validated members
            tar.extractall(path=extract_to, members=safe_members)

            # Find the root sosreport directory
            members = safe_members
            if members:
                # Get the top-level directory name
                root_name = members[0].name.split('/')[0]
                extracted_dir = extract_to / root_name
                
                if extracted_dir.exists():
                    Logger.debug(f"Extracted to: {extracted_dir}")
                    return extracted_dir
        
        Logger.error("Could not find extracted sosreport directory")
        raise Exception("Extraction failed: no root directory found")
        
    except Exception as e:
        Logger.error(f"Failed to extract tarball: {e}")
        raise


def validate_tarball(tarball_path: Path) -> bool:
    """Validate that the file is a valid tarball"""
    Logger.debug(f"Validating tarball: {tarball_path}")
    
    if not tarball_path.exists():
        raise FileNotFoundError(f"Tarball not found: {tarball_path}")
    
    if not tarball_path.is_file():
        raise ValueError(f"Not a file: {tarball_path}")
    
    # Try to open as tarball
    try:
        with tarfile.open(tarball_path, 'r:*') as tar:
            # Just check if we can read the first member
            members = tar.getmembers()
            if not members:
                raise ValueError("Tarball is empty")
        Logger.debug("Tarball validation successful")
        return True
    except Exception as e:
        Logger.error(f"Tarball validation failed: {e}")
        raise ValueError(f"Invalid tarball: {e}")


def get_sosreport_timestamp(tarball_path: Path) -> str:
    """Get timestamp from sosreport filename or file mtime"""
    try:
        # Try to parse from filename
        # sosreport-hostname-YYYY-MM-DD-random.tar.xz
        name = tarball_path.stem
        if '.tar' in name:
            name = name.split('.tar')[0]
        
        parts = name.split('-')
        # Look for date pattern YYYY-MM-DD or YYYYMMDD
        for i in range(len(parts) - 2):
            if len(parts[i]) == 4 and parts[i].isdigit():
                if len(parts[i+1]) == 2 and len(parts[i+2]) == 2:
                    date_str = f"{parts[i]}-{parts[i+1]}-{parts[i+2]}"
                    return date_str
        
        # Fallback to file modification time
        from datetime import datetime
        mtime = tarball_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception:
        return "Unknown"


def get_diagnostic_date_from_content(extracted_dir: Path, format_type: str) -> str:
    """
    Extract the actual date when the sosreport or supportconfig was collected
    from the content of the extracted files.
    
    For sosreport: Parses sos_logs/ui.log for timestamp
    For supportconfig: Parses basic-environment.txt for /bin/date command output
    
    Args:
        extracted_dir: Path to the extracted diagnostic directory
        format_type: Either 'sosreport' or 'supportconfig'
        
    Returns:
        Date string when diagnostic was collected, or "Unknown" if not found
    """
    import re
    from datetime import datetime
    
    try:
        if format_type == 'sosreport':
            # Parse sos_logs/ui.log
            # Format example: 2025-12-16 12:01:29,195 INFO: sos report (version 4.10.1)
            ui_log_path = extracted_dir / 'sos_logs' / 'ui.log'
            if ui_log_path.exists():
                with open(ui_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # Look for timestamp pattern: YYYY-MM-DD HH:MM:SS
                        match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                        if match:
                            return match.group(1)
            Logger.debug("Could not find timestamp in sos_logs/ui.log")
            
        elif format_type == 'supportconfig':
            # Parse basic-environment.txt for /bin/date command output
            # Format example after #==[ Command ]== # /bin/date
            # Mon Dec 15 06:48:21 EST 2025
            basic_env_path = extracted_dir / 'basic-environment.txt'
            if basic_env_path.exists():
                with open(basic_env_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Look for the /bin/date command section
                date_pattern = r'#==\[\s*Command\s*\]=+#\s*\n#\s*/bin/date\s*\n([^\n#]+)'
                match = re.search(date_pattern, content)
                if match:
                    date_str = match.group(1).strip()
                    # Try to parse various date formats and normalize
                    # Example: Mon Dec 15 06:48:21 EST 2025
                    try:
                        # Parse common date format with timezone
                        # Handle formats like: Mon Dec 15 06:48:21 EST 2025
                        date_parts = date_str.split()
                        if len(date_parts) >= 5:
                            # Reconstruct without timezone for parsing
                            # Format: Weekday Month Day HH:MM:SS [TZ] Year
                            if date_parts[-1].isdigit():  # Year at end
                                year = date_parts[-1]
                                # Check if second-to-last is timezone (alpha) or time
                                if date_parts[-2].replace(':', '').replace('.', '').isdigit():
                                    # No timezone - format: Weekday Month Day HH:MM:SS Year
                                    time_str = date_parts[-2]
                                else:
                                    # Has timezone - format: Weekday Month Day HH:MM:SS TZ Year  
                                    time_str = date_parts[-3] if len(date_parts) >= 5 else "00:00:00"
                                
                                month = date_parts[1]
                                day = date_parts[2]
                                
                                # Parse to datetime
                                parsed = datetime.strptime(f"{month} {day} {year} {time_str}", 
                                                          "%b %d %Y %H:%M:%S")
                                return parsed.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, IndexError) as e:
                        Logger.debug(f"Could not parse date '{date_str}': {e}")
                        # Return the raw date string if parsing fails
                        return date_str
                        
            Logger.debug("Could not find timestamp in basic-environment.txt")
                    
    except Exception as e:
        Logger.debug(f"Error extracting diagnostic date: {e}")
    
    return "Unknown"

def peek_sar_files(tarball_path: Path) -> dict:
    """
    Inspect a tarball for SAR files without fully extracting it.

    Returns:
        dict with keys:
          'format': 'sosreport' | 'supportconfig' | 'unknown'
          'files':  list of dicts, each containing:
                      name         – bare filename  (e.g. 'sar20251118.xz')
                      date_display – human-readable (e.g. 'Nov 18, 2025')
                    supportconfig extra: 'date' (YYYYMMDD string)
                    sosreport extra:     'day'  (day-number string, e.g. '1')
    """
    result = {'format': 'unknown', 'files': []}
    try:
        with tarfile.open(str(tarball_path), 'r:*') as tf:
            names = tf.getnames()
    except Exception as e:
        Logger.debug(f"peek_sar_files: could not open tarball: {e}")
        return result

    sc_files, sos_files = [], []
    for name in names:
        # Supportconfig: .../sar/sar20XXXXXXXX or .../sar/sar20XXXXXXXX.xz
        sc_m = re.search(r'(?:^|/)sar/sar(\d{8})(\.xz)?$', name)
        if sc_m:
            date_str = sc_m.group(1)
            try:
                disp = datetime.strptime(date_str, '%Y%m%d').strftime('%b %d, %Y')
            except ValueError:
                disp = date_str
            sc_files.append({
                'name': Path(name).name,
                'date': date_str,
                'date_display': disp,
            })
            continue

        # SOSReport: .../var/log/sa/sarNN (day number, 1–2 digits)
        sos_m = re.search(r'(?:^|/)var/log/sa/sar(\d{1,2})$', name)
        if sos_m:
            day = sos_m.group(1)
            sos_files.append({
                'name': Path(name).name,
                'day': day,
                'date_display': f'Day {int(day):02d}',
            })

    if sc_files:
        sc_files.sort(key=lambda x: x['date'])
        result['format'] = 'supportconfig'
        result['files'] = sc_files
    elif sos_files:
        sos_files.sort(key=lambda x: int(x['day']))
        result['format'] = 'sosreport'
        result['files'] = sos_files

    return result