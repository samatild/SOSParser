#!/usr/bin/env python3
"""
Updates analyzer for sosreport.

Analyzes package update information from:
- DNF (RHEL, Fedora, CentOS)
- YUM (older RHEL/CentOS)
- APT (Debian, Ubuntu)
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.logger import Logger


class UpdatesAnalyzer:
    """Analyze package updates information from sosreport."""

    def __init__(self):
        """Initialize the updates analyzer."""
        pass

    def analyze(self, base_path: Path) -> Dict[str, Any]:
        """
        Analyze updates information from sosreport.
        
        Args:
            base_path: Path to extracted sosreport directory
            
        Returns:
            Dictionary with updates information
        """
        Logger.debug("Analyzing updates information")
        
        data = {
            'package_manager': None,
            'dnf': {},
            'yum': {},
            'apt': {},
        }
        
        # Check for DNF (RHEL 8+, Fedora)
        dnf_dir = base_path / 'sos_commands' / 'dnf'
        if dnf_dir.exists():
            data['package_manager'] = 'dnf'
            data['dnf'] = self._analyze_dnf(dnf_dir)
        
        # Check for YUM (RHEL 7 and older)
        yum_dir = base_path / 'sos_commands' / 'yum'
        if yum_dir.exists() and not data['package_manager']:
            data['package_manager'] = 'yum'
            data['yum'] = self._analyze_yum(yum_dir)
        
        # Check for APT (Debian, Ubuntu)
        apt_dir = base_path / 'sos_commands' / 'apt'
        if apt_dir.exists():
            data['package_manager'] = 'apt'
            data['apt'] = self._analyze_apt(apt_dir)
            # Add sources/repository configuration from /etc/apt
            data['apt']['sources'] = self._analyze_apt_sources(base_path)
        
        return data

    def _analyze_dnf(self, dnf_dir: Path) -> Dict[str, Any]:
        """Analyze DNF package manager data."""
        Logger.debug("Analyzing DNF updates")
        
        dnf_data = {}
        
        # Available updates list
        updateinfo_list = self._find_file(dnf_dir, 'dnf_updateinfo_list_--available')
        if updateinfo_list:
            content = self._read_file(updateinfo_list)
            if content:
                dnf_data['available_updates'] = content
                dnf_data['update_summary'] = self._parse_update_summary(content)
        
        # Security advisories details
        updateinfo_security = self._find_file(dnf_dir, 'dnf_updateinfo_info_security')
        if updateinfo_security:
            content = self._read_file(updateinfo_security)
            if content:
                dnf_data['security_advisories'] = content
                dnf_data['security_summary'] = self._parse_security_summary(content)
        
        # Repository list
        repolist = self._find_file(dnf_dir, 'dnf_-C_repolist')
        if repolist:
            dnf_data['repolist'] = self._read_file(repolist)
        
        # Verbose repository info
        repolist_verbose = self._find_file(dnf_dir, 'dnf_-C_repolist_--verbose')
        if repolist_verbose:
            dnf_data['repolist_verbose'] = self._read_file(repolist_verbose)
        
        # Update history
        history = self._find_file(dnf_dir, 'dnf_history')
        if history:
            dnf_data['history'] = self._read_file(history)
        
        # DNF version
        version = self._find_file(dnf_dir, 'dnf_--version')
        if version:
            dnf_data['version'] = self._read_file(version)
        
        # Module list
        module_list = self._find_file(dnf_dir, 'dnf_module_list')
        if module_list:
            dnf_data['module_list'] = self._read_file(module_list)
        
        # Installed modules
        module_installed = self._find_file(dnf_dir, 'dnf_module_list_--installed')
        if module_installed:
            dnf_data['module_installed'] = self._read_file(module_installed)
        
        # Package problems
        problems = self._find_file(dnf_dir, 'package-cleanup_--problems')
        if problems:
            dnf_data['package_problems'] = self._read_file(problems)
        
        # Duplicate packages
        dupes = self._find_file(dnf_dir, 'package-cleanup_--dupes')
        if dupes:
            dnf_data['package_dupes'] = self._read_file(dupes)
        
        return dnf_data

    def _analyze_yum(self, yum_dir: Path) -> Dict[str, Any]:
        """Analyze YUM package manager data."""
        Logger.debug("Analyzing YUM updates")
        
        yum_data = {}
        
        # Check for security updates
        for pattern in ['yum_updateinfo*', 'yum_check-update*']:
            for f in yum_dir.glob(pattern):
                content = self._read_file(f)
                if content:
                    yum_data[f.name] = content
        
        # Repository list
        repolist = self._find_file(yum_dir, 'yum_repolist')
        if repolist:
            yum_data['repolist'] = self._read_file(repolist)
        
        # History
        history = self._find_file(yum_dir, 'yum_history')
        if history:
            yum_data['history'] = self._read_file(history)
        
        return yum_data

    def _analyze_apt(self, apt_dir: Path) -> Dict[str, Any]:
        """Analyze APT package manager data."""
        Logger.debug("Analyzing APT updates")
        
        apt_data = {}
        
        # APT policy (shows repositories and priorities)
        policy = self._find_file(apt_dir, 'apt-cache_policy')
        if policy:
            apt_data['policy'] = self._read_file(policy)
        
        # APT policy details
        policy_details = self._find_file(apt_dir, 'apt-cache_policy_details')
        if policy_details:
            apt_data['policy_details'] = self._read_file(policy_details)
        
        # Cache statistics
        stats = self._find_file(apt_dir, 'apt-cache_stats')
        if stats:
            apt_data['cache_stats'] = self._read_file(stats)
        
        # Held packages
        held = self._find_file(apt_dir, 'apt-mark_showhold')
        if held:
            content = self._read_file(held)
            apt_data['held_packages'] = content if content else 'No packages on hold'
        
        # APT configuration
        config = self._find_file(apt_dir, 'apt-config_dump')
        if config:
            apt_data['config'] = self._read_file(config)
        
        # APT get check
        check = self._find_file(apt_dir, 'apt-get_check')
        if check:
            apt_data['check'] = self._read_file(check)
        
        return apt_data

    def _analyze_apt_sources(self, base_path: Path) -> Dict[str, Any]:
        """Analyze APT sources/repository configuration from /etc/apt."""
        Logger.debug("Analyzing APT sources configuration")
        
        sources_data = {}
        etc_apt = base_path / 'etc' / 'apt'
        
        if not etc_apt.exists():
            return sources_data
        
        # Main sources.list
        sources_list = etc_apt / 'sources.list'
        if sources_list.exists():
            sources_data['sources_list'] = self._read_file(sources_list)
        
        # sources.list.d directory
        sources_list_d = etc_apt / 'sources.list.d'
        if sources_list_d.exists():
            source_files = {}
            for source_file in sorted(sources_list_d.iterdir()):
                if source_file.is_file() and source_file.suffix in ['.list', '.sources']:
                    content = self._read_file(source_file)
                    if content:
                        source_files[source_file.name] = content
            if source_files:
                sources_data['sources_list_d'] = source_files
        
        # Mirror configurations
        mirrors_dir = etc_apt / 'mirrors'
        if mirrors_dir.exists():
            mirrors = {}
            for mirror_file in sorted(mirrors_dir.iterdir()):
                if mirror_file.is_file():
                    content = self._read_file(mirror_file)
                    if content:
                        mirrors[mirror_file.name] = content
            if mirrors:
                sources_data['mirrors'] = mirrors
        
        # Preferences (pinning)
        preferences = etc_apt / 'preferences'
        if preferences.exists():
            sources_data['preferences'] = self._read_file(preferences)
        
        preferences_d = etc_apt / 'preferences.d'
        if preferences_d.exists():
            pref_files = {}
            for pref_file in sorted(preferences_d.iterdir()):
                if pref_file.is_file():
                    content = self._read_file(pref_file)
                    if content:
                        pref_files[pref_file.name] = content
            if pref_files:
                sources_data['preferences_d'] = pref_files
        
        return sources_data

    def _find_file(self, directory: Path, pattern: str) -> Optional[Path]:
        """Find a file matching pattern in directory."""
        # Try exact match first
        exact = directory / pattern
        if exact.exists():
            return exact
        
        # Try glob pattern
        matches = list(directory.glob(f'{pattern}*'))
        if matches:
            return matches[0]
        
        return None

    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file contents."""
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            Logger.warning(f"Failed to read {file_path}: {e}")
            return None

    def _parse_update_summary(self, content: str) -> Dict[str, Any]:
        """Parse update list and generate summary statistics."""
        summary = {
            'total': 0,
            'security': 0,
            'bugfix': 0,
            'enhancement': 0,
            'important': 0,
            'moderate': 0,
            'low': 0,
            'packages': []
        }
        
        if not content:
            return summary
        
        seen_packages = set()
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('Last metadata'):
                continue
            
            parts = line.split()
            if len(parts) >= 3:
                advisory = parts[0]
                severity_type = parts[1].lower()
                package = parts[2]
                
                # Count unique packages
                if package not in seen_packages:
                    seen_packages.add(package)
                    summary['total'] += 1
                    summary['packages'].append({
                        'advisory': advisory,
                        'type': severity_type,
                        'package': package
                    })
                    
                    # Categorize by type
                    if 'sec' in severity_type:
                        summary['security'] += 1
                    elif 'bugfix' in severity_type:
                        summary['bugfix'] += 1
                    elif 'enhancement' in severity_type:
                        summary['enhancement'] += 1
                    
                    # Categorize by severity
                    if 'important' in severity_type:
                        summary['important'] += 1
                    elif 'moderate' in severity_type:
                        summary['moderate'] += 1
                    elif 'low' in severity_type:
                        summary['low'] += 1
        
        return summary

    def _parse_security_summary(self, content: str) -> Dict[str, Any]:
        """Parse security advisories and extract CVE information."""
        summary = {
            'advisories': [],
            'cve_count': 0,
            'cves': []
        }
        
        if not content:
            return summary
        
        current_advisory = None
        cves = set()
        
        for line in content.split('\n'):
            line = line.strip()
            
            # New advisory section
            if line.startswith('Update ID:'):
                if current_advisory:
                    summary['advisories'].append(current_advisory)
                current_advisory = {
                    'id': line.replace('Update ID:', '').strip(),
                    'type': '',
                    'severity': '',
                    'cves': [],
                    'description': ''
                }
            elif current_advisory:
                if line.startswith('Type:'):
                    current_advisory['type'] = line.replace('Type:', '').strip()
                elif line.startswith('Severity:'):
                    current_advisory['severity'] = line.replace('Severity:', '').strip()
                elif line.startswith('CVEs:') or (line.startswith('CVE-') and ':' not in line):
                    cve = line.replace('CVEs:', '').strip()
                    if cve.startswith('CVE-'):
                        current_advisory['cves'].append(cve)
                        cves.add(cve)
                elif ': CVE-' in line:
                    # Extract CVE from lines like ": CVE-2025-12345"
                    for part in line.split():
                        if part.startswith('CVE-'):
                            current_advisory['cves'].append(part)
                            cves.add(part)
        
        # Add last advisory
        if current_advisory:
            summary['advisories'].append(current_advisory)
        
        summary['cve_count'] = len(cves)
        summary['cves'] = sorted(list(cves))
        
        return summary
