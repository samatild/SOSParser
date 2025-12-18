# SOSParser Processing Checklist

## Table of Contents

- [SOSReport Processing](#sosreport-processing)
  - [System Summary Information](#sosreport-system-summary)
  - [System Configuration](#sosreport-system-config)
  - [Filesystem Analysis](#sosreport-filesystem)
  - [Network Analysis](#sosreport-network)
  - [Log Analysis](#sosreport-logs)
  - [Cloud Services Analysis](#sosreport-cloud)
  - [Not Currently Processed (SOSReport)](#sosreport-not-processed)


- [Supportconfig Processing](#supportconfig-processing)
  - [System Summary Information](#supportconfig-system-summary)
  - [System Configuration](#supportconfig-system-config)
  - [Filesystem Analysis](#supportconfig-filesystem)
  - [Network Analysis](#supportconfig-network)
  - [Log Analysis](#supportconfig-logs)
  - [Cloud Services Analysis](#supportconfig-cloud)
  - [Not Currently Processed (Supportconfig)](#supportconfig-not-processed)

## SOSReport Processing

### System Summary Information
- [x] **Hostname**
  - `etc/hostname`, `sos_commands/general/hostname`
- [x] **OS Information**
  - `etc/os-release`, `etc/redhat-release`, `etc/debian_version`
- [x] **Kernel Information**
  - `sos_commands/kernel/uname_-a`, `proc/version`, `boot/config-*`
- [x] **System Uptime**
  - `sos_commands/general/uptime`, `proc/uptime`
- [x] **CPU Information**
  - `proc/cpuinfo`, `sos_commands/processor/lscpu`, `sos_commands/cpu/cpu_info`
- [x] **Memory Information**
  - `proc/meminfo`, `sos_commands/memory/free`, `sos_commands/memory/meminfo`
- [x] **Disk Information**
  - `sos_commands/block/lsblk`, `sys/block/`, `sos_commands/block/parted`
- [x] **System Load**
  - `proc/loadavg`, `sos_commands/general/uptime`
- [x] **Hardware Information (DMI)**
  - `sos_commands/hardware/dmidecode`, `sys/class/dmi/id/`
- [x] **Top Processes**
  - `sos_commands/process/ps_auxwwwm`
- [x] **System Resources**
  - `df`, `free`, `vmstat`, `proc/vmstat`
- [x] **Top Processes**
  - `sos_commands/process/ps_auxwwwm`
- [x] **System Resources**
  - `df`, `free`, `vmstat`, `proc/vmstat`

### System Configuration
- [x] **General Configuration**
  - Hostname, timezone, locale, machine-id, environment variables
- [x] **Boot Configuration**
  - GRUB config, kernel command line, boot loader entries, dracut config
- [x] **Authentication Configuration**
  - NSSwitch, PAM config, SSH config, login.defs, authselect
- [x] **SSH Runtime Configuration**
  - `sshd -T` output (runtime SSH configuration)
- [x] **Systemd Services**
  - Service status, failed services, enabled services, timers
- [x] **Cron Jobs**
  - Crontab, cron.d files, at jobs
- [x] **Security Configuration**
  - SELinux/AppArmor status and config, audit rules, crypto-policies
- [x] **Kernel Modules**
  - Loaded modules, modprobe config, sysctl parameters
- [x] **Users and Groups**
  - passwd, group, shadow, sudoers, user/group databases
- [x] **Sysconfig/System Configuration**
  - System configuration files, environment settings
- [x] **udev Configuration**
  - Device manager rules and configuration

## Filesystem Analysis
- [x] **Mount Information**
  - fstab, proc/mounts, mount output, mountinfo
- [x] **LVM Configuration**
  - PV/VG/LV display, LVM config
- [x] **Disk Usage**
  - df output (inodes and space), diskstats
- [x] **Filesystem Types**
  - proc/filesystems, XFS/ext/btrfs info, blkid output
- [x] **Multipath Configuration**
  - Device mapper multipath setup (Supportconfig: `mpio.txt`)
- [x] **iSCSI Configuration**
  - iSCSI initiator/target configuration
- [x] **Software RAID**
  - MD RAID configuration and status

## Network Analysis
- [x] **Network Interfaces**
  - IP address/link info, interface stats, ethtool details
- [x] **Routing Configuration**
  - IP route tables, IPv6 routes, route command output
- [x] **DNS Configuration**
  - resolv.conf, nsswitch.conf, hosts file
- [x] **Firewall Configuration**
  - firewalld zones, iptables/ip6tables rules
- [x] **NetworkManager Configuration**
  - NM config, connections, device status
- [x] **Connectivity Testing**
  - Ping tests, network diagnostics
- [x] **Network Services**
  - DHCP client config, NTP config

## Log Analysis
- [x] **System Logs**
  - messages, syslog, boot.log (tail 200/100 lines)
- [x] **Kernel Logs**
  - dmesg, kern.log (tail 200 lines)
- [x] **Authentication Logs**
  - secure, auth.log, audit.log, lastlog
- [x] **Service Logs**
  - journalctl, cron, maillog, yum/dnf logs
- [x] **Application Logs**
  - Web server logs, database logs, application-specific logs
- [x] **Systemd Journal**
  - Journal entries with filtering and analysis

## Cloud Services Analysis
- [x] **Cloud Provider Detection**
  - DMI/BIOS, hypervisor UUID, agent logs
- [x] **Cloud-init Analysis**
  - cloud.cfg, cloud-init.log, user-data, instance metadata
- [x] **AWS Specific**
  - Instance metadata, SSM agent, CloudWatch agent, ENA driver
- [x] **Azure Specific**
  - WA Linux Agent, extensions, instance metadata, ovf-env.xml
- [x] **GCP Specific**
  - Guest agent, osconfig agent, instance metadata
- [x] **Oracle Cloud Specific**
  - Instance metadata
- [x] **General Virtualization**
  - virt-what, systemd-detect-virt, product name detection

### Not Currently Processed (SOSReport)
- [ ] **ATA/SMART Disk Health**
  - `sos_commands/ata/smartctl_*`, `sos_commands/ata/hdparm_*`
- [ ] **Ansible Configuration**
  - `etc/ansible/`, `sos_commands/ansible/*`
- [ ] **AIDE File Integrity**
  - `etc/aide.conf`, `sos_commands/aide/*`
- [ ] **Java Environment**
  - `sos_commands/java/*`, `sos_commands/jars/*`
- [ ] **Mellanox Firmware**
  - `sos_commands/mellanox_firmware/*`
- [ ] **TPM2 Information**
  - `sos_commands/tpm2/*`
- [ ] **VDO Deduplication**
  - `sos_commands/vdo/*`
- [ ] **eBPF Programs**
  - `sos_commands/ebpf/*`
- [ ] **Red Hat Connector**
  - `sos_commands/rhc/*`
- [ ] **Elasticsearch Configuration**
  - `etc/elasticsearch/`, `sos_commands/elastic/*`
- [ ] **Cockpit Configuration**
  - `etc/cockpit/`, `sos_commands/cockpit/*`
- [ ] **Kdump Configuration**
  - `sos_commands/kdump/*`
- [ ] **GRUB2 Advanced Configuration**
  - `sos_commands/grub2/*`

## Supportconfig Processing

### System Summary Information
- [x] **Hostname**
  - `basic-environment.txt` (uname output)
- [x] **OS Information**
  - `basic-environment.txt` (os-release equivalent)
- [x] **Kernel Information**
  - `basic-environment.txt`, `boot.txt`
- [x] **System Uptime**
  - `basic-health-check.txt`
- [x] **CPU Information**
  - `hardware.txt` (lscpu output)
- [x] **Memory Information**
  - `memory.txt`, `basic-health-check.txt`
- [x] **Disk Information**
  - `fs-diskio.txt` (lsblk, df output)
- [x] **System Load**
  - `basic-health-check.txt`
- [x] **Hardware Information (DMI)**
  - `hardware.txt` (dmidecode)
- [x] **CPU Vulnerabilities**
  - `basic-health-check.txt`
- [x] **Kernel Tainted Status**
  - `basic-health-check.txt`
- [x] **Top Processes**
  - `basic-health-check.txt`
- [x] **System Resources**
  - `basic-health-check.txt` (vmstat, free, df)

### System Configuration
- [x] **General Configuration**
  - `basic-environment.txt` (collection time, uname, virtualization)
- [x] **Boot Configuration**
  - `boot.txt` (GRUB, running kernel)
- [x] **SSH Runtime Configuration**
  - `ssh.txt` (sshd -T equivalent)
- [x] **Authentication Configuration**
  - `pam.txt` (PAM modules)
- [x] **Systemd Services**
  - `systemd.txt`, `systemd-status.txt`
- [x] **Cron Jobs**
  - `cron.txt`
- [x] **Security Configuration**
  - `security-*.txt` (SELinux, AppArmor, audit)
- [x] **Package Management**
  - `rpm.txt` (RPM packages)
- [x] **Kernel Modules**
  - `env.txt` (sysctl, ulimit)
- [x] **Container Runtime**
  - `docker.txt`, `podman-root.txt`

### Filesystem Analysis
- [x] **LVM Configuration**
  - `lvm.txt` (pvs, vgs, lvs)
- [x] **Filesystem Types**
  - Various `fs-*.txt` files (btrfs, autofs, gfs2, etc.)
- [x] **Disk Usage**
  - `fs-diskio.txt` (df, disk stats)
- [x] **Multipath Configuration**
  - `mpio.txt` (device mapper multipath)
- [x] **NFS Configuration** (Supportconfig only - HTML report subtabs)
  - `nfs.txt` (NFS client/server config, services, exports)
- [x] **Samba Configuration** (Supportconfig only - HTML report subtabs)
  - `samba.txt` (SMB/CIFS packages and configuration)

### Network Analysis
- [x] **Network Configuration**
  - `network.txt` (interfaces, routing, DNS)
- [x] **DNS Configuration**
  - `dns.txt`
- [x] **DHCP Configuration**
  - `dhcp.txt`
- [x] **Firewall Configuration**
  - SUSE firewall rules
- [x] **Connectivity Testing**
  - Ping tests in `network.txt`

### Log Analysis
- [x] **System Logs**
  - `messages.txt` (system messages)
- [x] **Systemd Journal**
  - `systemd-status.txt` (journal entries)
- [x] **Local Warnings**
  - `messages_localwarn.txt`
- [x] **Messages Configuration**
  - `messages_config.txt` (syslog config)
- [x] **Service Logs**
  - Various service-specific logs

### Cloud Services Analysis
- [x] **Public Cloud Information**
  - `plugin-suse_public_cloud.txt`, `public_cloud/` directory
- [x] **Cloud Registration**
  - SUSE Cloud registration status
- [x] **Cloud Billing**
  - Billing flavor and adapter configuration
- [x] **Update Infrastructure**
  - Cloud update servers and repositories

### Not Currently Processed (Supportconfig)
- [ ] **Advanced Application Logs**
  - `y2log.txt` (YaST logs)
  - `updates-curl-trace_*.txt` (update traces)
- [ ] **Advanced SUSE Features**
  - `slert.txt` (SUSE Real Time)
  - `transactional-update.txt` (transactional updates)
  - `livepatch.txt` (kernel live patching)
- [ ] **High Availability**
  - `ha.txt` (HA cluster configuration)
- [ ] **OCFS2**
  - `ocfs2.txt` (Oracle Cluster Filesystem)
- [ ] **CIMOM**
  - `cimom.txt` (Common Information Model)
- [ ] **Crash Analysis**
  - `crash.txt` (system crash dumps)
- [ ] **BPF Analysis**
  - `bpf.txt` (eBPF programs)
- [ ] **LDAP Configuration**
  - `ldap.txt` (LDAP client config)
- [ ] **SSSD Configuration**
  - `sssd.txt` (System Security Services)
- [ ] **NTP Configuration**
  - `ntp.txt` (Network Time Protocol)
- [ ] **Web Services**
  - `web.txt` (Apache/Nginx configuration)
- [ ] **Email Services**
  - `email.txt` (Postfix/Sendmail config)
- [ ] **Print Services**
  - `print.txt` (CUPS printing)
- [ ] **udev Configuration**
  - `udev.txt` (device manager rules)
- [ ] **Plymouth**
  - `plymouth.txt` (boot splash)
- [ ] **Environment Variables**
  - `env.txt` (system environment)
- [ ] **Sysconfig**
  - `sysconfig.txt` (system config files)
- [ ] **Proc Information**
  - `proc.txt` (proc filesystem contents)
- [ ] **Sysfs Information**
  - `sysfs.txt` (sysfs filesystem)
- [ ] **Open Files**
  - `open-files.txt` (open file descriptors)
- [ ] **SLP Configuration**
  - `slp.txt` (Service Location Protocol)
- [ ] **SMT Configuration**
  - `smt.txt` (SUSE Manager/Subscription Mgmt)
- [ ] **DBus Configuration**
  - `dbus.txt` (D-Bus system config)
- [ ] **X Window System**
  - `x.txt` (X11 configuration)
