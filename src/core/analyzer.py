#!/usr/bin/env python3
"""Main analyzer for SOSReport and Supportconfig files"""

import tempfile
import shutil
import tarfile
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# SOSReport analyzers
from analyzers.system.system_info import (
    get_hostname,
    get_os_release,
    get_kernel_info,
    get_uptime,
    get_execution_timestamp,
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_system_load,
    get_dmidecode_info
)
from analyzers.system.system_config import SystemConfigAnalyzer
from analyzers.filesystem.filesystem import FilesystemAnalyzer
from analyzers.network.network import NetworkAnalyzer
from analyzers.logs.logs import LogAnalyzer
from analyzers.cloud.cloud import CloudAnalyzer
from analyzers.scenarios.scenario_analyzer import BaseScenarioAnalyzer

# Supportconfig analyzers
from analyzers.supportconfig.system_info import SupportconfigSystemInfo
from analyzers.supportconfig.system_config import SupportconfigSystemConfig
from analyzers.supportconfig.network import SupportconfigNetwork
from analyzers.supportconfig.filesystem import SupportconfigFilesystem
from analyzers.supportconfig.cloud import SupportconfigCloud
from analyzers.supportconfig.logs import SupportconfigLogs

from reporting.report_generator import (
    prepare_report_data,
    format_scenario_results_html
)
from utils.logger import Logger
from utils.file_operations import (
    validate_tarball,
    extract_tarball,
    get_sosreport_timestamp
)
from utils.output_manager import setup_output_directory
from utils.format_detector import detect_format, get_format_info


class SOSReportAnalyzer:
    """Main analyzer class for SOSReport files"""
    
    def __init__(self, tarball_path, save_next_to_tarball: bool = True,
                 output_dir_override: str | None = None):
        Logger.debug(
            f"Initializing SOSReportAnalyzer with tarball_path: {tarball_path}"
        )
        self.tarball_path = Path(tarball_path)
        self.save_next_to_tarball = bool(save_next_to_tarball)
        self.output_dir_override = Path(output_dir_override).resolve() if output_dir_override else None
        self.template_dir = Path(__file__).parent.parent / 'templates'
        self.static_dir = Path(__file__).parent.parent / 'static'
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml"))
        )
        
        # Create output directory name based on tarball filename
        tarball_name = self.tarball_path.stem
        # Remove .tar from .tar.xz or .tar.gz
        if '.tar' in tarball_name:
            tarball_name = tarball_name.split('.tar')[0]
        
        if self.output_dir_override:
            self.output_dir = self.output_dir_override / f"SOSParser_{tarball_name}"
        elif self.save_next_to_tarball:
            self.output_dir = self.tarball_path.parent / f"SOSParser_{tarball_name}"
        else:
            self.output_dir = Path(f"SOSParser_{tarball_name}")
        
        Logger.debug(f"Output directory set to: {self.output_dir}")
        
        # Create temporary directory for extraction
        self.temp_dir = Path(tempfile.mkdtemp())
        Logger.debug(f"Temporary extraction directory: {self.temp_dir}")
        
        # Initialize analyzers
        self.system_config_analyzer = SystemConfigAnalyzer()
        self.filesystem_analyzer = FilesystemAnalyzer()
        self.network_analyzer = NetworkAnalyzer()
        self.log_analyzer = LogAnalyzer()
        self.cloud_analyzer = CloudAnalyzer()
        Logger.debug("Analyzers initialized.")
        
        # Initialize scenario analyzers
        self.scenario_analyzers = []
        scenarios_dir = Path(__file__).parent.parent / 'scenarios'
        Logger.debug(f"Loading scenario analyzers from: {scenarios_dir}")
        
        # Load scenarios from directory and subdirectories
        if scenarios_dir.exists():
            for scenario_file in scenarios_dir.rglob('*.json'):
                Logger.debug(f"Loading scenario: {scenario_file}")
                self.scenario_analyzers.append(BaseScenarioAnalyzer(scenario_file))
        
        Logger.debug(f"Total scenarios loaded: {len(self.scenario_analyzers)}")
    
    def cleanup(self):
        """Clean up temporary directory after analysis is complete"""
        try:
            if self.temp_dir.exists():
                Logger.debug(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
                Logger.debug("Temporary directory cleanup completed.")
        except Exception as e:
            Logger.warning(f"Failed to cleanup temporary directory {self.temp_dir}: {str(e)}")
    
    def analyze_supportconfig(self, extracted_dir: Path):
        """
        Analyze a supportconfig format file.
        
        Args:
            extracted_dir: Path to extracted supportconfig directory
            
        Returns:
            Tuple of (system_info, system_config, filesystem, network, logs, cloud)
        """
        Logger.info("Analyzing supportconfig format")
        
        # Initialize supportconfig analyzers
        sys_analyzer = SupportconfigSystemInfo(extracted_dir)
        config_analyzer = SupportconfigSystemConfig(extracted_dir)
        net_analyzer = SupportconfigNetwork(extracted_dir)
        fs_analyzer = SupportconfigFilesystem(extracted_dir)
        cloud_analyzer = SupportconfigCloud(extracted_dir)
        logs_analyzer = SupportconfigLogs(extracted_dir)
        
        # Get system information
        hostname = sys_analyzer.get_hostname()
        os_info = sys_analyzer.get_os_info()
        kernel_info = sys_analyzer.get_kernel_info()
        uptime = sys_analyzer.get_uptime()
        cpu_info = sys_analyzer.get_cpu_info()
        memory_info = sys_analyzer.get_memory_info()
        disk_info = sys_analyzer.get_disk_info()
        system_load = sys_analyzer.get_system_load()
        dmi_info = sys_analyzer.get_dmi_info()
        
        # Get system configuration
        Logger.debug("Analyzing system configuration (supportconfig)")
        config_data = config_analyzer.analyze()
        system_config = {
            'general': config_data.get('general', {}),
            'boot': config_data.get('boot', {}),
            'authentication': config_data.get('authentication', {}),
            'ssh_runtime': config_data.get('ssh_runtime', {}),
            'services': config_data.get('services', {}),
            'cron': config_data.get('cron', {}),
            'security': config_data.get('security', {}),
            'packages': config_data.get('packages', {}),
            'kernel_modules': config_data.get('kernel_modules', {}),
            'containers': config_data.get('containers', {}),
            'users_groups': {},
        }
        
        # Analyze filesystem
        filesystem = fs_analyzer.analyze()
        
        # Analyze network
        network = net_analyzer.analyze()

        # Analyze logs
        logs = logs_analyzer.analyze()

        # Analyze cloud information
        cloud = cloud_analyzer.analyze()
        
        return (hostname, os_info, kernel_info, uptime, cpu_info, memory_info, 
                disk_info, system_load, dmi_info, system_config, filesystem, network, logs, cloud)
    
    def generate_report(self):
        """Generate the analysis report"""
        Logger.debug("Starting report generation.")
        
        try:
            # Extract the tarball
            Logger.debug("Extracting tarball.")
            extracted_dir = extract_tarball(self.tarball_path, self.temp_dir)
            Logger.debug(f"Extracted to: {extracted_dir}")
            
            # Detect format
            format_type = detect_format(extracted_dir)
            format_info = get_format_info(format_type)
            Logger.info(f"Detected format: {format_info['name']} ({format_type})")
            
            if format_type == 'unknown':
                raise ValueError(f"Unknown or unsupported diagnostic file format at {extracted_dir}")
            
            # Get diagnostic timestamp
            Logger.debug("Getting diagnostic timestamp.")
            if format_type == 'sosreport':
                diagnostic_timestamp = get_sosreport_timestamp(self.tarball_path)
            else:
                # For supportconfig, use current time or extract from file
                from datetime import datetime
                diagnostic_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            Logger.debug(f"Diagnostic timestamp: {diagnostic_timestamp}")
            
            # Route to appropriate analyzer based on format
            if format_type == 'sosreport':
                Logger.debug("Using SOSReport analyzers")
                # Get system information
                Logger.debug("Getting system information.")
                hostname = get_hostname(extracted_dir)
                os_info = get_os_release(extracted_dir)
                kernel_info = get_kernel_info(extracted_dir)
                uptime = get_uptime(extracted_dir)
                cpu_info = get_cpu_info(extracted_dir)
                memory_info = get_memory_info(extracted_dir)
                disk_info = get_disk_info(extracted_dir)
                system_load = get_system_load(extracted_dir)
                dmi_info = get_dmidecode_info(extracted_dir)
                
                # Analyze system configuration
                Logger.debug("Analyzing system configuration.")
                system_config = {
                    'general': self.system_config_analyzer.analyze_general(extracted_dir),
                    'boot': self.system_config_analyzer.analyze_boot(extracted_dir),
                    'authentication': self.system_config_analyzer.analyze_authentication(extracted_dir),
                    'ssh_runtime': self.system_config_analyzer.analyze_ssh_runtime(extracted_dir),
                    'services': self.system_config_analyzer.analyze_services(extracted_dir),
                    'cron': self.system_config_analyzer.analyze_cron(extracted_dir),
                    'security': self.system_config_analyzer.analyze_security(extracted_dir),
                    'packages': self.system_config_analyzer.analyze_packages(extracted_dir),
                    'kernel_modules': self.system_config_analyzer.analyze_kernel_modules(extracted_dir),
                    'users_groups': self.system_config_analyzer.analyze_users_groups(extracted_dir),
                    'containers': self.system_config_analyzer.analyze_containers(extracted_dir),
                }
                
                # Analyze filesystem
                Logger.debug("Analyzing filesystem.")
                filesystem = {
                    'mounts': self.filesystem_analyzer.analyze_mounts(extracted_dir),
                    'lvm': self.filesystem_analyzer.analyze_lvm(extracted_dir),
                    'disk_usage': self.filesystem_analyzer.analyze_disk_usage(extracted_dir),
                    'filesystems': self.filesystem_analyzer.analyze_filesystems(extracted_dir),
                }
                
                # Analyze network
                Logger.debug("Analyzing network.")
                network = {
                    'interfaces': self.network_analyzer.analyze_interfaces(extracted_dir),
                    'routing': self.network_analyzer.analyze_routing(extracted_dir),
                    'dns': self.network_analyzer.analyze_dns(extracted_dir),
                    'firewall': self.network_analyzer.analyze_firewall(extracted_dir),
                    'networkmanager': self.network_analyzer.analyze_networkmanager(extracted_dir),
                }
                
                # Analyze logs
                Logger.debug("Analyzing logs.")
                logs = {
                    'system': self.log_analyzer.analyze_system_logs(extracted_dir),
                    'kernel': self.log_analyzer.analyze_kernel_logs(extracted_dir),
                    'auth': self.log_analyzer.analyze_auth_logs(extracted_dir),
                    'services': self.log_analyzer.analyze_service_logs(extracted_dir),
                }
                
                # Analyze cloud services
                Logger.debug("Analyzing cloud services.")
                cloud_provider = self.cloud_analyzer.detect_cloud_provider(extracted_dir)
                cloud = None
                
                if cloud_provider:
                    Logger.info(f"Cloud provider detected: {cloud_provider}")
                    cloud = {
                        'provider': cloud_provider,
                        'virtualization': self.cloud_analyzer.analyze_general_virtualization(extracted_dir),
                        'cloud_init': self.cloud_analyzer.analyze_cloud_init(extracted_dir),
                    }
                    
                    # Add provider-specific analysis
                    if cloud_provider == 'aws':
                        cloud['aws'] = self.cloud_analyzer.analyze_aws(extracted_dir)
                    elif cloud_provider == 'azure':
                        cloud['azure'] = self.cloud_analyzer.analyze_azure(extracted_dir)
                    elif cloud_provider == 'gcp':
                        cloud['gcp'] = self.cloud_analyzer.analyze_gcp(extracted_dir)
                    elif cloud_provider == 'oracle':
                        cloud['oracle'] = self.cloud_analyzer.analyze_oracle_cloud(extracted_dir)
                else:
                    Logger.debug("No cloud provider detected, skipping cloud analysis.")
                    
            elif format_type == 'supportconfig':
                Logger.debug("Using Supportconfig analyzers")
                (hostname, os_info, kernel_info, uptime, cpu_info, memory_info, 
                 disk_info, system_load, dmi_info, system_config, filesystem, 
                 network, logs, cloud) = self.analyze_supportconfig(extracted_dir)
            
            # Analyze scenarios (optional, can be disabled)
            Logger.debug("Analyzing scenarios.")
            scenario_results = []
            # for analyzer in self.scenario_analyzers:
            #     Logger.debug(f"Running scenario analyzer: {analyzer.scenario_config_path}")
            #     results = analyzer.analyze(extracted_dir)
            #     if results:
            #         Logger.debug(f"Scenario {analyzer.scenario_config_path} found {len(results)} results.")
            #         scenario_results.extend(results)
            
            # Generate execution timestamp
            execution_timestamp = get_execution_timestamp()
            
            # Prepare report data
            Logger.debug("Preparing report data for template.")
            report_data = prepare_report_data(
                os_info=os_info,
                hostname=hostname,
                kernel_info=kernel_info,
                uptime=uptime,
                cpu_info=cpu_info,
                memory_info=memory_info,
                disk_info=disk_info,
                system_load=system_load,
                dmi_info=dmi_info,
                system_config=system_config,
                filesystem=filesystem,
                network=network,
                logs=logs,
                cloud=cloud,
                scenario_results=scenario_results,
                format_scenario_results=lambda r: format_scenario_results_html(
                    r, self.scenario_analyzers
                ),
                execution_timestamp=execution_timestamp,
                diagnostic_timestamp=diagnostic_timestamp,
            )
            
            # Generate the report
            Logger.debug("Rendering HTML report from template.")
            template = self.env.get_template('report_template.html')
            html_content = template.render(**report_data)
            
            # Write the report to the output file
            output_path = self.output_dir / 'report.html'
            Logger.debug(f"Writing report to: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            Logger.debug("Report generation complete.")
            return output_path
            
        except Exception as e:
            Logger.error(f"Error generating report: {str(e)}")
            raise


def run_analysis(input_path, debug_mode=False, save_next_to_tarball: bool = True,
                 output_dir_override: str | None = None):
    """
    Run the SOSReport analysis.
    
    Args:
        input_path: Path to the sosreport tarball
        debug_mode: Enable debug logging
        save_next_to_tarball: Save output next to tarball (or in current dir)
        output_dir_override: Override output directory location
        
    Returns:
        Path to the generated report HTML file
    """
    Logger.info(f"Starting analysis for: {input_path}")
    Logger.debug("Instantiating SOSReportAnalyzer.")
    
    analyzer = SOSReportAnalyzer(
        input_path,
        save_next_to_tarball=save_next_to_tarball,
        output_dir_override=output_dir_override
    )
    
    # Validate tarball
    validate_tarball(Path(input_path))
    Logger.debug("Tarball validated.")
    
    # Set up debug logging if requested
    if debug_mode and not Logger._debug_enabled:
        debug_file_path = analyzer.output_dir / "debug.log"
        Logger.set_debug(True, str(debug_file_path))
        Logger.debug("Debug mode enabled for analysis")
    
    # Set up output directory
    setup_output_directory(
        analyzer.output_dir,
        analyzer.template_dir,
        analyzer.static_dir
    )
    Logger.debug("Output directory set up.")
    
    # Generate report
    output_path = analyzer.generate_report()
    Logger.info(f"Report generated successfully in: {output_path}")
    
    # Clean up temporary directory
    analyzer.cleanup()
    
    return output_path


def generate_supportconfig_example_report(
    example_tarball_path: str | None = None,
    output_dir: str | None = None,
    recreate_tarball: bool = False,
):
    """
    Generate a supportconfig report using the bundled example data.
    
    This mimics the upload flow by calling run_analysis on a .txz archive and
    writes the report into a dedicated test directory under examples/.
    
    Args:
        example_tarball_path: Optional path to a supportconfig .txz file. If not
            provided, defaults to examples/scc_sles15_251211_1144.txz.
        output_dir: Optional directory where the report will be written. If not
            provided, defaults to examples/test_reports/supportconfig_boot.
        recreate_tarball: When True and the tarball path does not exist, package
            the decompressed example folder into a new .txz for testing.
    
    Returns:
        Path to the generated report HTML file.
    """
    project_root = Path(__file__).resolve().parents[2]
    default_example = project_root / "examples" / "scc_sles15_251211_1144.txz"
    tarball_path = Path(example_tarball_path) if example_tarball_path else default_example
    extracted_example = project_root / "examples" / "scc_sles15_251211_1144"

    if not tarball_path.exists():
        if not extracted_example.exists():
            raise FileNotFoundError(
                f"Example data missing at {extracted_example}; cannot build supportconfig archive."
            )
        if recreate_tarball:
            Logger.info(f"Creating supportconfig test archive at {tarball_path}")
            tarball_path.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tarball_path, "w:xz") as tar:
                tar.add(extracted_example, arcname=extracted_example.name)
        else:
            raise FileNotFoundError(
                f"Supportconfig archive not found at {tarball_path}. "
                "Pass recreate_tarball=True to build it from the decompressed example."
            )

    report_output_dir = (
        Path(output_dir)
        if output_dir
        else project_root / "examples" / "test_reports" / "supportconfig_boot"
    )
    report_output_dir.mkdir(parents=True, exist_ok=True)
    Logger.info(
        f"Generating supportconfig test report from {tarball_path} into {report_output_dir}"
    )

    # Keep debug enabled to mimic the upload flow visibility.
    return run_analysis(
        str(tarball_path),
        debug_mode=True,
        save_next_to_tarball=False,
        output_dir_override=str(report_output_dir),
    )
