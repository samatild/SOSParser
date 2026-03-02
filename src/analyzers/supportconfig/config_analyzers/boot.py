"""
Supportconfig Boot Configuration Analyzer

Analyzes boot and GRUB configuration from boot.txt.
"""

from typing import Dict, Any, List
from pathlib import Path
from ..parser import SupportconfigParser


class BootConfigAnalyzer:
    """Analyzer for boot and GRUB configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract boot and GRUB configuration from boot.txt for supportconfig.

        Uses streaming to read boot.txt without loading entire file into memory.

        Returns:
            Dictionary shaped like the report template expects:
              - cmdline: kernel command line (from /proc/cmdline or GRUB default)
              - loader_entries: list of GRUB menu entries (names only)
              - grub_cfg: truncated grub.cfg content for quick inspection
              - grub_config: parsed /etc/default/grub key/value pairs (extra detail)
              - grub_verification: rpm -V status for grub2 (if present)
              - secure_boot: Secure Boot state (mokutil)
              - sbat_revocations: SBAT revocation list (mokutil)
              - efi_boot_current: current EFI boot entry
              - efi_boot_order: list of EFI boot order entries
              - efi_boot_entries: detailed EFI entries from efibootmgr -v
        """
        boot_info: Dict[str, Any] = {
            'cmdline': '',
            'loader_entries': [],
            'grub_cfg': '',
            'grub_config': {},
            'grub_cfg_path': '',
            'grub_verification': '',
            'secure_boot': '',
            'sbat_revocations': [],
            'efi_boot_current': '',
            'efi_boot_order': [],
            'efi_boot_entries': [],
        }

        # Use streaming to find specific sections without loading entire boot.txt
        # boot.txt can be very large (hundreds of MB)
        section_filters = [
            {'key': 'default_grub', 'header_match': '/etc/default/grub', 'section_type': 'Configuration'},
            {'key': 'grub_cfg', 'header_match': '/boot/grub2/grub.cfg', 'section_type': 'Configuration'},
            {'key': 'proc_cmdline', 'header_match': '/proc/cmdline', 'section_type': 'Configuration'},
            {'key': 'grub_verify', 'header_match': 'grub2', 'section_type': 'Verification'},
            {'key': 'mokutil_sb', 'header_match': 'mokutil --sb-state', 'section_type': 'Command'},
            {'key': 'mokutil_sbat', 'header_match': 'mokutil --list-sbat-revocations', 'section_type': 'Command'},
            {'key': 'efibootmgr', 'header_match': 'efibootmgr -v', 'section_type': 'Command'},
        ]
        
        sections = self.parser.find_sections_streaming('boot.txt', section_filters)
        if not sections:
            return boot_info
        
        # Process the sections we found
        self._process_sections(boot_info, sections)
        
        return boot_info
    
    def _process_sections(self, boot_info: Dict[str, Any], sections: Dict[str, Dict[str, str]]):
        """Process the streamed sections into boot_info."""
        
        # /etc/default/grub -> parse key/values for GRUB defaults
        if 'default_grub' in sections:
            content = sections['default_grub']['content']
            for line in content.split('\n'):
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    boot_info['grub_config'][key] = value
                    if key in ('GRUB_CMDLINE_LINUX_DEFAULT', 'GRUB_CMDLINE_LINUX'):
                        if not boot_info['cmdline']:
                            boot_info['cmdline'] = value
        
        # grub.cfg content and menu entries
        if 'grub_cfg' in sections:
            header = sections['grub_cfg']['header']
            content = sections['grub_cfg']['content']
            lines = content.split('\n')
            
            boot_info['grub_cfg_path'] = header
            # Store truncated grub.cfg (first 5000 chars)
            if content:
                boot_info['grub_cfg'] = content[:5000]
            # Capture menuentry names
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("menuentry "):
                    name_part = stripped.split("menuentry", 1)[1].strip()
                    if name_part.startswith("'"):
                        name = name_part.split("'", 2)[1]
                        if name not in boot_info['loader_entries']:
                            boot_info['loader_entries'].append(name)
        
        # /proc/cmdline -> running kernel command line
        if 'proc_cmdline' in sections:
            cmdline = sections['proc_cmdline']['content'].strip()
            if cmdline:
                boot_info['cmdline'] = cmdline
        
        # rpm -V output for grub2
        if 'grub_verify' in sections:
            content = sections['grub_verify']['content']
            for line in content.split('\n'):
                if 'Verification Status:' in line:
                    boot_info['grub_verification'] = line.split(':', 1)[1].strip()
                elif line and not line.startswith('#'):
                    boot_info.setdefault('verification_details', []).append(line.strip())
        
        # Secure Boot state
        if 'mokutil_sb' in sections:
            # Skip first line (command itself)
            lines = sections['mokutil_sb']['content'].split('\n')
            cmd_output = '\n'.join(lines[1:] if lines[0].startswith('#') else lines).strip()
            if cmd_output:
                boot_info['secure_boot'] = cmd_output
        
        # SBAT revocations
        if 'mokutil_sbat' in sections:
            lines = sections['mokutil_sbat']['content'].split('\n')
            revos = [l.strip() for l in lines[1:] if l.strip() and not l.startswith('#')]
            if revos:
                boot_info['sbat_revocations'] = revos
        
        # EFI boot manager info
        if 'efibootmgr' in sections:
            lines = sections['efibootmgr']['content'].split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('BootCurrent:'):
                    boot_info['efi_boot_current'] = line.split(':', 1)[1].strip()
                elif line.startswith('BootOrder:'):
                    order = line.split(':', 1)[1].strip()
                    boot_info['efi_boot_order'] = [o.strip() for o in order.split(',') if o.strip()]
                elif line.startswith('Boot'):
                    boot_info['efi_boot_entries'].append(line)
