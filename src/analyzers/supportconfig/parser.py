#!/usr/bin/env python3
"""Base parser for SUSE supportconfig .txt files."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SupportconfigParser:
    """
    Base parser for supportconfig .txt files.
    
    Supportconfig files have sections marked with:
    #==[ Type ]========================================#
    
    Types include: Command, File, System, Note, etc.
    """
    
    def __init__(self, root_path: Path):
        """
        Initialize parser with root path to supportconfig directory.
        
        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = Path(root_path)
        
    # Maximum file size to load into memory (default 50MB)
    # Files larger than this use streaming methods to prevent OOM
    MAX_FILE_SIZE_MB = int(os.environ.get('SCC_MAX_FILE_SIZE_MB', '50'))
    
    # Section header pattern for supportconfig files
    _SECTION_PATTERN = re.compile(r'^#==\[\s*(.+?)\s*\]={5,}#\s*$')
    
    def read_file(self, filename: str, max_size_mb: int = None) -> Optional[str]:
        """
        Read a supportconfig .txt file with size limit to prevent OOM.
        
        For large files, consider using find_section_streaming() instead.
        
        Args:
            filename: Name of the .txt file (e.g., 'hardware.txt')
            max_size_mb: Maximum file size in MB (default: MAX_FILE_SIZE_MB)
            
        Returns:
            File contents or None if file doesn't exist.
            Large files are truncated with a warning message appended.
        """
        if max_size_mb is None:
            max_size_mb = self.MAX_FILE_SIZE_MB
        max_bytes = max_size_mb * 1024 * 1024
        
        file_path = self.root_path / filename
        try:
            file_size = file_path.stat().st_size
            
            if file_size > max_bytes:
                # File too large - read only up to limit
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_bytes)
                return content + f"\n\n[TRUNCATED: File {filename} is {file_size / 1024 / 1024:.1f} MB, limit is {max_size_mb} MB]"
            
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
    
    def find_section_streaming(self, filename: str, header_match: str, 
                                section_type: str = None,
                                max_section_lines: int = 10000) -> Optional[str]:
        """
        Stream through a file to find a specific section without loading entire file.
        
        This is memory-efficient for large files - reads line by line and stops
        as soon as the matching section is found and read.
        
        Args:
            filename: Name of the .txt file
            header_match: String to search for in section header (case-insensitive)
            section_type: Optional section type filter (e.g., 'Command', 'File')
            max_section_lines: Maximum lines to read from a section (safety limit)
            
        Returns:
            Section content or None if not found
        """
        file_path = self.root_path / filename
        if not file_path.exists():
            return None
        
        header_match_lower = header_match.lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                in_target_section = False
                section_content = []
                
                for line in f:
                    match = self._SECTION_PATTERN.match(line)
                    
                    if match:
                        # Found a section header
                        if in_target_section:
                            # We were in the target section and hit the next one - done!
                            return '\n'.join(section_content).strip()
                        
                        # Check if this is the section we want
                        header = match.group(1)
                        current_type = header.split()[0] if header else ''
                        
                        if header_match_lower in header.lower():
                            if section_type is None or current_type == section_type:
                                in_target_section = True
                                section_content = []
                    elif in_target_section:
                        section_content.append(line.rstrip('\n'))
                        if len(section_content) >= max_section_lines:
                            # Safety limit reached
                            return '\n'.join(section_content).strip()
                
                # If we reached EOF while in target section
                if in_target_section:
                    return '\n'.join(section_content).strip()
                
        except Exception:
            pass
        
        return None
    
    def find_command_streaming(self, filename: str, command: str,
                               max_output_lines: int = 10000) -> Optional[str]:
        """
        Stream through a file to find a specific command output without loading entire file.
        
        Memory-efficient alternative to get_command_output() for large files.
        
        Args:
            filename: Name of the .txt file
            command: Command to search for (e.g., '/bin/uname -a' or just 'uname')
            max_output_lines: Maximum lines to read from command output
            
        Returns:
            Command output or None if not found
        """
        file_path = self.root_path / filename
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                in_command_section = False
                found_command = False
                output_lines = []
                
                for line in f:
                    match = self._SECTION_PATTERN.match(line)
                    
                    if match:
                        # Found a section header
                        if found_command:
                            # We were reading command output and hit next section - done!
                            return '\n'.join(output_lines).strip()
                        
                        header = match.group(1)
                        section_type = header.split()[0] if header else ''
                        in_command_section = (section_type == 'Command')
                        found_command = False
                        output_lines = []
                    elif in_command_section:
                        if not found_command:
                            # Look for the command line (starts with #)
                            if line.startswith('#'):
                                cmd_line = line.strip('# \n')
                                if command in cmd_line or cmd_line.endswith(command):
                                    found_command = True
                        else:
                            output_lines.append(line.rstrip('\n'))
                            if len(output_lines) >= max_output_lines:
                                return '\n'.join(output_lines).strip()
                
                # If we reached EOF while reading command output
                if found_command:
                    return '\n'.join(output_lines).strip()
                
        except Exception:
            pass
        
        return None
    
    def find_sections_streaming(self, filename: str, 
                                 section_filters: List[Dict[str, str]],
                                 max_section_lines: int = 5000) -> Dict[str, Dict[str, str]]:
        """
        Stream through a file to find multiple sections in one pass.
        
        Memory-efficient for large files - reads line by line and collects
        all matching sections without loading entire file.
        
        Args:
            filename: Name of the .txt file
            section_filters: List of filter dicts, each with:
                - 'key': unique identifier for this section in results
                - 'header_match': string to match in header (case-insensitive)
                - 'section_type': optional type filter (e.g., 'Command', 'Configuration')
            max_section_lines: Maximum lines per section (safety limit)
            
        Returns:
            Dict mapping filter keys to {'header': str, 'content': str, 'type': str}
        """
        file_path = self.root_path / filename
        results = {}
        
        if not file_path.exists():
            return results
        
        # Pre-process filters for efficiency
        filters = []
        for f in section_filters:
            filters.append({
                'key': f['key'],
                'header_match': f.get('header_match', '').lower(),
                'section_type': f.get('section_type'),
                'found': False
            })
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
                current_section = None
                current_content = []
                current_filter_key = None
                line_count = 0
                
                for line in fh:
                    match = self._SECTION_PATTERN.match(line)
                    
                    if match:
                        # Save previous section if it matched a filter
                        if current_filter_key and current_content:
                            results[current_filter_key] = {
                                'header': current_section['header'],
                                'type': current_section['type'],
                                'content': '\n'.join(current_content).strip()
                            }
                        
                        # Check new section against filters
                        header = match.group(1)
                        section_type = header.split()[0] if header else ''
                        header_lower = header.lower()
                        
                        current_section = {'header': header, 'type': section_type}
                        current_content = []
                        current_filter_key = None
                        line_count = 0
                        
                        # Find matching filter
                        for f in filters:
                            if f['found']:
                                continue
                            if f['header_match'] and f['header_match'] not in header_lower:
                                continue
                            if f['section_type'] and f['section_type'] != section_type:
                                continue
                            # Match found!
                            current_filter_key = f['key']
                            f['found'] = True
                            break
                        
                        # Check if all filters found - can exit early
                        if all(f['found'] for f in filters):
                            # Continue reading current section, then exit
                            pass
                            
                    elif current_filter_key:
                        current_content.append(line.rstrip('\n'))
                        line_count += 1
                        if line_count >= max_section_lines:
                            # Safety limit - save and stop collecting this section
                            results[current_filter_key] = {
                                'header': current_section['header'],
                                'type': current_section['type'],
                                'content': '\n'.join(current_content).strip()
                            }
                            current_filter_key = None
                
                # Handle last section
                if current_filter_key and current_content:
                    results[current_filter_key] = {
                        'header': current_section['header'],
                        'type': current_section['type'],
                        'content': '\n'.join(current_content).strip()
                    }
                    
        except Exception:
            pass
        
        return results
    
    def read_file_tail(self, filename: str, lines: int = 1000) -> Optional[str]:
        """
        Read the last N lines from a supportconfig .txt file.
        
        Uses memory-efficient tail algorithm to avoid loading entire file
        into memory for large log files.
        
        Args:
            filename: Name of the .txt file (e.g., 'messages.txt')
            lines: Number of lines to read from the end (default 1000)
            
        Returns:
            Last N lines of file contents or None if file doesn't exist
        """
        from collections import deque
        
        file_path = self.root_path / filename
        try:
            file_size = file_path.stat().st_size
            
            # For small files (< 1MB), just read the whole thing
            if file_size < 1024 * 1024:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return ''.join(tail_lines)
            
            # For larger files, use memory-efficient reverse reading
            chunk_size = 8192  # 8KB chunks
            result_lines = deque(maxlen=lines)
            
            with open(file_path, 'rb') as f:
                # Start from end of file
                f.seek(0, 2)  # Seek to end
                remaining_size = f.tell()
                buffer = b''
                
                while remaining_size > 0 and len(result_lines) < lines:
                    # Calculate how much to read
                    read_size = min(chunk_size, remaining_size)
                    remaining_size -= read_size
                    
                    # Seek and read
                    f.seek(remaining_size)
                    chunk = f.read(read_size)
                    buffer = chunk + buffer
                    
                    # Extract complete lines from buffer
                    while b'\n' in buffer and len(result_lines) < lines:
                        last_newline = buffer.rfind(b'\n')
                        if last_newline == len(buffer) - 1:
                            second_last = buffer.rfind(b'\n', 0, last_newline)
                            if second_last != -1:
                                line = buffer[second_last + 1:last_newline + 1]
                                buffer = buffer[:second_last + 1]
                                try:
                                    result_lines.appendleft(line.decode('utf-8', errors='ignore'))
                                except Exception:
                                    pass
                            else:
                                break
                        else:
                            line = buffer[last_newline + 1:]
                            buffer = buffer[:last_newline + 1]
                            if line:
                                try:
                                    result_lines.appendleft(line.decode('utf-8', errors='ignore'))
                                except Exception:
                                    pass
                
                # Handle any remaining buffer content
                if buffer and len(result_lines) < lines:
                    remaining_lines = buffer.decode('utf-8', errors='ignore').split('\n')
                    for line in reversed(remaining_lines):
                        if len(result_lines) >= lines:
                            break
                        if line:
                            result_lines.appendleft(line + '\n')
            
            return ''.join(result_lines)
        except Exception:
            return None
    
    def extract_sections(self, content: str) -> List[Dict[str, str]]:
        """
        Extract sections from supportconfig file content.
        
        Sections are marked with:
        #==[ Type ]========================================#
        
        Args:
            content: File content
            
        Returns:
            List of dictionaries with 'type', 'header', and 'content'
        """
        if not content:
            return []
        
        sections = []
        # Pattern: #==[ Type ]====...====#
        pattern = r'^#==\[\s*(.+?)\s*\]={5,}#\s*$'
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Save previous section
                if current_section:
                    sections.append({
                        'type': current_section['type'],
                        'header': current_section['header'],
                        'content': '\n'.join(current_content).strip()
                    })
                
                # Start new section
                header = match.group(1)
                section_type = header.split()[0] if header else 'Unknown'
                current_section = {
                    'type': section_type,
                    'header': header
                }
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                'type': current_section['type'],
                'header': current_section['header'],
                'content': '\n'.join(current_content).strip()
            })
        
        return sections
    
    def get_command_output(self, filename: str, command: str) -> Optional[str]:
        """
        Get output of a specific command from a supportconfig file.
        
        Args:
            filename: Name of the .txt file
            command: Command to search for (e.g., '/bin/uname -a' or just 'uname')
            
        Returns:
            Command output or None if not found
        """
        content = self.read_file(filename)
        if not content:
            return None
        
        sections = self.extract_sections(content)
        
        for section in sections:
            if section['type'] == 'Command':
                # The command is in the content, prefixed with #
                # Format: # /path/to/command args
                # followed by the output
                lines = section['content'].split('\n')
                if lines and lines[0].startswith('#'):
                    cmd_line = lines[0].strip('# ').strip()
                    # Check if this is the command we're looking for
                    if command in cmd_line or cmd_line.endswith(command):
                        # Return everything after the command line
                        return '\n'.join(lines[1:]).strip()
        
        return None
    
    def find_sections_by_type(self, content: str, section_type: str) -> List[Dict[str, str]]:
        """
        Find all sections of a specific type.
        
        Args:
            content: File content
            section_type: Section type to search for (e.g., 'Command', 'File')
            
        Returns:
            List of matching sections
        """
        sections = self.extract_sections(content)
        return [s for s in sections if s['type'] == section_type]
    
    def parse_table(self, content: str, delimiter: str = None) -> List[List[str]]:
        """
        Parse table-like output from command results.
        
        Args:
            content: Table content
            delimiter: Column delimiter (None for whitespace)
            
        Returns:
            List of rows, each row is a list of columns
        """
        if not content:
            return []
        
        lines = content.strip().split('\n')
        table = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if delimiter:
                columns = [col.strip() for col in line.split(delimiter)]
            else:
                columns = line.split()
            
            table.append(columns)
        
        return table
    
    def extract_key_value_pairs(self, content: str, separator: str = ':') -> Dict[str, str]:
        """
        Extract key-value pairs from content.
        
        Args:
            content: Content with key: value pairs
            separator: Separator between key and value
            
        Returns:
            Dictionary of key-value pairs
        """
        if not content:
            return {}
        
        pairs = {}
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if separator in line:
                key, value = line.split(separator, 1)
                pairs[key.strip()] = value.strip()
        
        return pairs
    
    def get_file_listing(self, filename: str, path: str) -> Optional[str]:
        """
        Get file listing from etc.txt or similar files.
        
        Args:
            filename: Name of the .txt file (e.g., 'etc.txt')
            path: Path to search for (e.g., '/etc/os-release')
            
        Returns:
            File content or None if not found
        """
        content = self.read_file(filename)
        if not content:
            return None
        
        sections = self.extract_sections(content)
        
        for section in sections:
            if section['type'] == 'File' and path in section['header']:
                return section['content']
        
        return None
