#!/usr/bin/env python3
"""Base parser for SUSE supportconfig .txt files."""

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
        
    def read_file(self, filename: str) -> Optional[str]:
        """
        Read a supportconfig .txt file.
        
        Args:
            filename: Name of the .txt file (e.g., 'hardware.txt')
            
        Returns:
            File contents or None if file doesn't exist
        """
        file_path = self.root_path / filename
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
    
    def read_file_tail(self, filename: str, lines: int = 1000) -> Optional[str]:
        """
        Read the last N lines from a supportconfig .txt file.
        
        Args:
            filename: Name of the .txt file (e.g., 'messages.txt')
            lines: Number of lines to read from the end (default 1000)
            
        Returns:
            Last N lines of file contents or None if file doesn't exist
        """
        file_path = self.root_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return ''.join(tail_lines)
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
