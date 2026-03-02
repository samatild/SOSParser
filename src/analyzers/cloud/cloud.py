#!/usr/bin/env python3
"""Cloud services analyzer for SOSReport"""

from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import Logger


class CloudAnalyzer:
    """Analyze cloud-related configurations and services"""
    
    def detect_cloud_provider(self, base_path: Path) -> Optional[str]:
        """
        Detect which cloud provider the system is running on.
        Returns: 'aws', 'azure', 'gcp', 'oracle', 'alibaba', or None
        """
        Logger.debug("Detecting cloud provider")
        
        # Check DMI/BIOS information
        dmi_system = base_path / 'dmidecode'
        if not dmi_system.exists():
            dmi_system = base_path / 'sos_commands' / 'hardware' / 'dmidecode'
        
        if dmi_system.exists():
            try:
                content = dmi_system.read_text().lower()
                
                # AWS detection
                if 'amazon' in content or 'amazon ec2' in content:
                    Logger.info("Detected cloud provider: AWS")
                    return 'aws'
                
                # Azure detection
                if 'microsoft corporation' in content and ('virtual machine' in content or 'azure' in content):
                    Logger.info("Detected cloud provider: Azure")
                    return 'azure'
                
                # GCP detection
                if 'google' in content and 'compute engine' in content:
                    Logger.info("Detected cloud provider: GCP")
                    return 'gcp'
                
                # Oracle Cloud
                if 'oraclecloud' in content or 'oracle cloud' in content:
                    Logger.info("Detected cloud provider: Oracle Cloud")
                    return 'oracle'
                
            except Exception as e:
                Logger.warning(f"Error reading DMI: {e}")
        
        # Check for cloud-specific files/directories
        # AWS: /sys/hypervisor/uuid starts with 'ec2'
        hypervisor_uuid = base_path / 'sys' / 'hypervisor' / 'uuid'
        if hypervisor_uuid.exists():
            try:
                uuid_content = hypervisor_uuid.read_text().strip()
                if uuid_content.startswith('ec2'):
                    Logger.info("Detected cloud provider: AWS (via hypervisor UUID)")
                    return 'aws'
            except Exception:
                pass
        
        # Azure: Check for waagent
        waagent_log = base_path / 'var' / 'log' / 'waagent.log'
        if waagent_log.exists():
            Logger.info("Detected cloud provider: Azure (via waagent)")
            return 'azure'
        
        # GCP: Check for google guest agent
        gcp_agent = base_path / 'var' / 'log' / 'google-guest-agent.log'
        if gcp_agent.exists():
            Logger.info("Detected cloud provider: GCP (via guest agent)")
            return 'gcp'
        
        Logger.debug("No cloud provider detected")
        return None
    
    def analyze_cloud_init(self, base_path: Path) -> dict:
        """Analyze cloud-init configuration and logs"""
        Logger.debug("Analyzing cloud-init")
        
        data = {}
        
        # Cloud-init configuration
        cloud_cfg = base_path / 'etc' / 'cloud' / 'cloud.cfg'
        if cloud_cfg.exists():
            data['cloud_cfg'] = cloud_cfg.read_text()
        
        # Cloud-init logs
        cloud_init_log = base_path / 'var' / 'log' / 'cloud-init.log'
        if cloud_init_log.exists():
            log_content = cloud_init_log.read_text()
            # Get last 100 lines
            lines = log_content.splitlines()
            data['cloud_init_log'] = '\n'.join(lines[-100:]) if len(lines) > 100 else log_content
        
        # Cloud-init output log
        cloud_init_output = base_path / 'var' / 'log' / 'cloud-init-output.log'
        if cloud_init_output.exists():
            output_content = cloud_init_output.read_text()
            lines = output_content.splitlines()
            data['cloud_init_output'] = '\n'.join(lines[-100:]) if len(lines) > 100 else output_content
        
        # Cloud-init status
        cloud_status = base_path / 'sos_commands' / 'cloud_init' / 'cloud-init_status_--long'
        if cloud_status.exists():
            data['cloud_status'] = cloud_status.read_text()
        
        # Cloud-init user-data
        user_data = base_path / 'var' / 'lib' / 'cloud' / 'instance' / 'user-data.txt'
        if user_data.exists():
            data['user_data'] = user_data.read_text()
        
        return data
    
    def analyze_aws(self, base_path: Path) -> dict:
        """Analyze AWS-specific services and configurations"""
        Logger.debug("Analyzing AWS services")
        
        data = {}
        
        # EC2 instance metadata
        instance_id = base_path / 'sos_commands' / 'cloud' / 'curl_-s_http:__169.254.169.254_latest_meta-data_instance-id'
        if instance_id.exists():
            data['instance_id'] = instance_id.read_text().strip()
        
        # Instance type
        instance_type = base_path / 'sos_commands' / 'cloud' / 'curl_-s_http:__169.254.169.254_latest_meta-data_instance-type'
        if instance_type.exists():
            data['instance_type'] = instance_type.read_text().strip()
        
        # Availability zone
        az = base_path / 'sos_commands' / 'cloud' / 'curl_-s_http:__169.254.169.254_latest_meta-data_placement_availability-zone'
        if az.exists():
            data['availability_zone'] = az.read_text().strip()
        
        # AWS Systems Manager agent
        ssm_log = base_path / 'var' / 'log' / 'amazon' / 'ssm' / 'amazon-ssm-agent.log'
        if ssm_log.exists():
            log_content = ssm_log.read_text()
            lines = log_content.splitlines()
            data['ssm_agent_log'] = '\n'.join(lines[-50:]) if len(lines) > 50 else log_content
        
        # CloudWatch agent
        cloudwatch_log = base_path / 'var' / 'log' / 'amazon' / 'amazon-cloudwatch-agent' / 'amazon-cloudwatch-agent.log'
        if cloudwatch_log.exists():
            log_content = cloudwatch_log.read_text()
            lines = log_content.splitlines()
            data['cloudwatch_agent_log'] = '\n'.join(lines[-50:]) if len(lines) > 50 else log_content
        
        # ENA driver info
        ena_info = base_path / 'sos_commands' / 'kernel' / 'modinfo_ena'
        if ena_info.exists():
            data['ena_driver'] = ena_info.read_text()
        
        return data
    
    def analyze_azure(self, base_path: Path) -> dict:
        """Analyze Azure-specific services and configurations"""
        Logger.debug("Analyzing Azure services")
        
        data = {}
        
        # WALinuxAgent (waagent)
        waagent_log = base_path / 'var' / 'log' / 'waagent.log'
        if waagent_log.exists():
            log_content = waagent_log.read_text()
            lines = log_content.splitlines()
            data['waagent_log'] = '\n'.join(lines[-100:]) if len(lines) > 100 else log_content
        
        # waagent configuration
        waagent_conf = base_path / 'etc' / 'waagent.conf'
        if waagent_conf.exists():
            data['waagent_conf'] = waagent_conf.read_text()
        
        # Azure VM extensions
        extensions_dir = base_path / 'var' / 'lib' / 'waagent'
        if extensions_dir.exists():
            extensions = []
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir() and 'Microsoft' in ext_dir.name:
                    extensions.append(ext_dir.name)
            if extensions:
                data['extensions'] = extensions
        
        # Azure instance metadata
        azure_metadata = base_path / 'sos_commands' / 'cloud' / 'curl_-H_Metadata:true_http:__169.254.169.254_metadata_instance_api-version=2021-02-01'
        if azure_metadata.exists():
            data['instance_metadata'] = azure_metadata.read_text()
        
        # Azure network configuration
        azure_net_conf = base_path / 'var' / 'lib' / 'waagent' / 'ovf-env.xml'
        if azure_net_conf.exists():
            data['ovf_env'] = azure_net_conf.read_text()
        
        return data
    
    def analyze_gcp(self, base_path: Path) -> dict:
        """Analyze Google Cloud Platform services"""
        Logger.debug("Analyzing GCP services")
        
        data = {}
        
        # Google Guest Agent
        guest_agent_log = base_path / 'var' / 'log' / 'google-guest-agent.log'
        if guest_agent_log.exists():
            log_content = guest_agent_log.read_text()
            lines = log_content.splitlines()
            data['guest_agent_log'] = '\n'.join(lines[-100:]) if len(lines) > 100 else log_content
        
        # Google OS Config Agent
        os_config_log = base_path / 'var' / 'log' / 'google-osconfig-agent.log'
        if os_config_log.exists():
            log_content = os_config_log.read_text()
            lines = log_content.splitlines()
            data['osconfig_agent_log'] = '\n'.join(lines[-50:]) if len(lines) > 50 else log_content
        
        # GCP instance metadata
        gcp_metadata = base_path / 'sos_commands' / 'cloud' / 'curl_-H_Metadata-Flavor:Google_http:__169.254.169.254_computeMetadata_v1_instance_'
        if gcp_metadata.exists():
            data['instance_metadata'] = gcp_metadata.read_text()
        
        return data
    
    def analyze_oracle_cloud(self, base_path: Path) -> dict:
        """Analyze Oracle Cloud Infrastructure services"""
        Logger.debug("Analyzing Oracle Cloud services")
        
        data = {}
        
        # OCI instance metadata
        oci_metadata = base_path / 'sos_commands' / 'cloud' / 'curl_http:__169.254.169.254_opc_v1_instance_'
        if oci_metadata.exists():
            data['instance_metadata'] = oci_metadata.read_text()
        
        return data
    
    def analyze_general_virtualization(self, base_path: Path) -> dict:
        """Analyze general virtualization information"""
        Logger.debug("Analyzing virtualization")
        
        data = {}
        
        # virt-what
        virt_what = base_path / 'sos_commands' / 'general' / 'virt-what'
        if virt_what.exists():
            data['virt_what'] = virt_what.read_text().strip()
        
        # systemd-detect-virt
        systemd_virt = base_path / 'sos_commands' / 'general' / 'systemd-detect-virt'
        if systemd_virt.exists():
            data['systemd_virt'] = systemd_virt.read_text().strip()
        
        # DMI product name
        dmi_product = base_path / 'sys' / 'class' / 'dmi' / 'id' / 'product_name'
        if dmi_product.exists():
            data['product_name'] = dmi_product.read_text().strip()
        
        return data
