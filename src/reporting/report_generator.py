#!/usr/bin/env python3
"""Report generation utilities for SOSReport analyzer"""

from typing import Dict, List, Any
from analyzers.scenarios.scenario_analyzer import ScenarioResult
from __version__ import __version__


def get_os_logo(os_info: Dict[str, str]) -> str:
    """
    Determine the OS logo based on OS information.
    Returns the relative path to the logo image.
    """
    os_id = os_info.get('ID', '').lower()
    os_name = os_info.get('NAME', '').lower()
    
    # Map OS ID to logo file
    if 'ubuntu' in os_id or 'ubuntu' in os_name:
        return 'images/ubuntulogo.svg'
    elif 'rhel' in os_id or 'red hat' in os_name:
        return 'images/redhat_logo.png'
    elif 'centos' in os_id or 'centos' in os_name:
        return 'images/centoslogo.png'
    elif 'suse' in os_id or 'suse' in os_name or 'sles' in os_id:
        return 'images/SUSE_Linux_GmbH_Logo.svg'
    elif 'oracle' in os_id or 'oracle' in os_name:
        return 'images/oraclelinux.svg'
    else:
        return None


def prepare_report_data(
    os_info: Dict[str, str],
    hostname: str,
    kernel_info: Dict[str, str],
    uptime: str,
    cpu_info: Dict[str, Any],
    memory_info: Dict[str, Any],
    disk_info: Dict[str, Any],
    system_load: Dict[str, Any],
    dmi_info: Dict[str, Any],
    system_config: Dict[str, Any],
    filesystem: Dict[str, Any],
    network: Dict[str, Any],
    logs: Dict[str, Any],
    cloud: Dict[str, Any],
    scenario_results: List[ScenarioResult],
    format_scenario_results: callable,
    execution_timestamp: str,
    diagnostic_timestamp: str = None,
    enhanced_summary: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Prepare the report data dictionary.
    
    Args:
        os_info: OS information dictionary
        hostname: System hostname
        kernel_info: Kernel information dictionary
        uptime: System uptime
        system_config: System configuration analysis results
        filesystem: Filesystem analysis results
        network: Network analysis results
        logs: Log analysis results
        scenario_results: Scenario analysis results
        format_scenario_results: Function to format scenario results as HTML
        execution_timestamp: Timestamp when analyzer was executed
        diagnostic_timestamp: Timestamp when sosreport was generated
        
    Returns:
        Dictionary containing all report data
    """
    # Get OS logo
    os_logo = get_os_logo(os_info)
    
    return {
        'version': __version__,
        'diagnostic_timestamp': diagnostic_timestamp or 'Unknown',
        'execution_timestamp': execution_timestamp,
        'os_logo': os_logo,
        'summary': {
            'hostname': hostname,
            'os_info': os_info,
            'kernel_info': kernel_info,
            'uptime': uptime,
            'cpu_info': cpu_info,
            'memory_info': memory_info,
            'disk_info': disk_info,
            'system_load': system_load,
            'dmi_info': dmi_info,
            # Enhanced summary data (for supportconfig)
            **(enhanced_summary or {}),
        },
        'system_config': system_config,
        'filesystem': filesystem,
        'network': network,
        'logs': logs,
        'cloud': cloud,
        'scenarios': format_scenario_results(scenario_results),
    }


def format_scenario_results_html(
    results: List[ScenarioResult],
    scenario_analyzers: List[Any]
) -> str:
    """
    Format scenario analysis results as HTML.
    
    Args:
        results: List of scenario analysis results
        scenario_analyzers: List of scenario analyzers
        
    Returns:
        HTML string containing formatted scenario results
    """
    if not results:
        return "<p>No scenario analysis results found.</p>"
    
    html = "<div class='scenario-analysis'>"
    for analyzer in scenario_analyzers:
        analyzer_results = [
            r for r in results
            if r.scenario_name == analyzer.config['ScenarioName']
        ]
        if analyzer_results:
            html += analyzer.format_results_html(analyzer_results)
    html += "</div>"
    return html
