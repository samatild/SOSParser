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

        content = self.parser.read_file('boot.txt')
        if not content:
            return boot_info

        sections = self.parser.extract_sections(content)

        def _parse_grub_cfg(lines: List[str]):
            """Parse grub.cfg content for menu entries and store truncated cfg."""
            if not lines:
                return
            # Store truncated grub.cfg (first 5000 chars to avoid bloating report)
            cfg_body = '\n'.join(lines[1:]).strip()
            if cfg_body:
                boot_info['grub_cfg'] = cfg_body[:5000]
            # Capture menuentry names
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("menuentry "):
                    # Format: menuentry 'NAME' ... {
                    name_part = stripped.split("menuentry", 1)[1].strip()
                    if name_part.startswith("'"):
                        name = name_part.split("'", 2)[1]
                        if name not in boot_info['loader_entries']:
                            boot_info['loader_entries'].append(name)

        for section in sections:
            if section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue

                header_line = lines[0].strip()
                header_lower = header_line.lower()

                # /etc/default/grub -> parse key/values for GRUB defaults
                if '/etc/default/grub' in header_line and 'not found' not in header_lower:
                    for line in lines[1:]:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            boot_info['grub_config'][key] = value
                            if key in ('GRUB_CMDLINE_LINUX_DEFAULT', 'GRUB_CMDLINE_LINUX'):
                                # Prefer GRUB default if cmdline not already set
                                if not boot_info['cmdline']:
                                    boot_info['cmdline'] = value

                # grub.cfg content and menu entries
                elif '/boot/grub2/grub.cfg' in header_line and 'not found' not in header_lower:
                    boot_info['grub_cfg_path'] = header_line
                    _parse_grub_cfg(lines)

                # /proc/cmdline -> running kernel command line
                elif '/proc/cmdline' in header_line and 'not found' not in header_lower:
                    cmdline = '\n'.join(lines[1:]).strip()
                    if cmdline:
                        boot_info['cmdline'] = cmdline

            elif section['type'] == 'Verification':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header_lower = lines[0].lower()
                # Capture rpm -V output for grub2
                if 'grub2' in header_lower:
                    for line in lines:
                        if 'Verification Status:' in line:
                            boot_info['grub_verification'] = line.split(':', 1)[1].strip()
                        elif line and not line.startswith('#'):
                            boot_info.setdefault('verification_details', []).append(line.strip())
            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                # Secure Boot state
                if 'mokutil --sb-state' in cmd_line:
                    state = '\n'.join(lines[1:]).strip()
                    if state:
                        boot_info['secure_boot'] = state

                # SBAT revocations
                elif 'mokutil --list-sbat-revocations' in cmd_line:
                    revos = [l.strip() for l in lines[1:] if l.strip()]
                    if revos:
                        boot_info['sbat_revocations'] = revos

                # EFI boot manager info
                elif 'efibootmgr -v' in cmd_line:
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('BootCurrent:'):
                            boot_info['efi_boot_current'] = line.split(':', 1)[1].strip()
                        elif line.startswith('BootOrder:'):
                            order = line.split(':', 1)[1].strip()
                            boot_info['efi_boot_order'] = [o.strip() for o in order.split(',') if o.strip()]
                        elif line.startswith('Boot'):
                            # Keep the full line for context
                            boot_info['efi_boot_entries'].append(line)

        return boot_info
