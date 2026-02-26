#!/usr/bin/env python3
"""
Health Summary Analyzer

Aggregates findings from all analyzers and computes an overall system
health status for the top-line health summary card.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from utils.logger import Logger
from analyzers.rules_engine import evaluate_rules


# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------
CRITICAL = "critical"
WARNING = "warning"
OK = "ok"

# Disk-usage thresholds (percent)
DISK_CRITICAL_THRESHOLD = 95
DISK_WARNING_THRESHOLD = 85

# Memory thresholds (percent of *used* memory – i.e. available < X%)
MEM_CRITICAL_AVAILABLE_PCT = 5
MEM_WARNING_AVAILABLE_PCT = 15

# Swap usage thresholds
SWAP_CRITICAL_THRESHOLD = 80
SWAP_WARNING_THRESHOLD = 50


# ---------------------------------------------------------------------------
# Finding dataclass-like dict helper
# ---------------------------------------------------------------------------

def _finding(severity: str, category: str, title: str, detail: str = "",
             section_link: str = "") -> Dict[str, str]:
    """Return a single finding dict."""
    return {
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
        "section_link": section_link,
    }


# ---------------------------------------------------------------------------
# Individual check helpers
# ---------------------------------------------------------------------------

def _check_failed_services(system_config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Check for failed systemd services."""
    findings: list = []
    services = system_config.get("services", {})
    failed = services.get("failed_services_entries", [])
    if failed:
        names = [f.get("name", "?") for f in failed]
        count = len(names)
        severity = CRITICAL if count >= 1 else WARNING
        findings.append(_finding(
            severity=severity,
            category="Services",
            title=f"{count} failed service{'s' if count != 1 else ''}",
            detail=", ".join(names[:8]) + (" …" if count > 8 else ""),
            section_link="system-config",
        ))
    return findings


def _check_disk_usage(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """Check disk usage thresholds from system_resources."""
    findings: list = []
    resources = summary.get("system_resources", {})
    disks = resources.get("disk_usage_parsed", [])
    for disk in disks:
        pct = disk.get("use_percent", 0)
        mount = disk.get("mount", "?")
        if pct >= DISK_CRITICAL_THRESHOLD:
            findings.append(_finding(
                severity=CRITICAL,
                category="Disk",
                title=f"Disk {mount} at {pct}%",
                detail=f"{disk.get('used', '?')} / {disk.get('size', '?')}",
                section_link="filesystem",
            ))
        elif pct >= DISK_WARNING_THRESHOLD:
            findings.append(_finding(
                severity=WARNING,
                category="Disk",
                title=f"Disk {mount} at {pct}%",
                detail=f"{disk.get('used', '?')} / {disk.get('size', '?')}",
                section_link="filesystem",
            ))
    return findings


def _check_memory(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """Check memory and swap usage."""
    findings: list = []
    resources = summary.get("system_resources", {})
    mem_parsed = resources.get("memory_parsed", {})
    mem = mem_parsed.get("memory", {})
    if mem:
        avail_pct = mem.get("available_percent", 100)
        if avail_pct <= MEM_CRITICAL_AVAILABLE_PCT:
            findings.append(_finding(
                severity=CRITICAL,
                category="Memory",
                title=f"Available memory critically low ({avail_pct}%)",
                detail=f"{mem.get('available_human', '?')} of {mem.get('total_human', '?')} available",
                section_link="summary",
            ))
        elif avail_pct <= MEM_WARNING_AVAILABLE_PCT:
            findings.append(_finding(
                severity=WARNING,
                category="Memory",
                title=f"Available memory low ({avail_pct}%)",
                detail=f"{mem.get('available_human', '?')} of {mem.get('total_human', '?')} available",
                section_link="summary",
            ))
    swap = mem_parsed.get("swap", {})
    if swap:
        swap_pct = swap.get("used_percent", 0)
        if swap_pct >= SWAP_CRITICAL_THRESHOLD:
            findings.append(_finding(
                severity=WARNING,
                category="Swap",
                title=f"Swap usage high ({swap_pct}%)",
                detail=f"{swap.get('used_human', '?')} / {swap.get('total_human', '?')}",
                section_link="summary",
            ))
        elif swap_pct >= SWAP_WARNING_THRESHOLD:
            findings.append(_finding(
                severity=WARNING,
                category="Swap",
                title=f"Swap usage elevated ({swap_pct}%)",
                detail=f"{swap.get('used_human', '?')} / {swap.get('total_human', '?')}",
                section_link="summary",
            ))
    return findings


# NOTE: Kernel tainted and log-scanning checks have been migrated to the
# rules engine (src/rules/known_issues/).  They are no longer hardcoded here.


def _check_updates(updates: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Check for pending security updates."""
    findings: list = []
    if not updates:
        return findings

    # Different package managers store data differently
    security_count = 0
    total_count = 0

    # APT-based
    apt_updates = updates.get("upgradable_packages", [])
    if apt_updates:
        total_count = len(apt_updates)
        security_count = sum(
            1 for p in apt_updates
            if isinstance(p, dict) and "security" in str(p.get("origin", "")).lower()
        )

    # DNF/YUM-based
    dnf_updates = updates.get("available_updates", [])
    if dnf_updates:
        total_count = max(total_count, len(dnf_updates))

    # Zypper-based
    zypper_updates = updates.get("patches", [])
    if zypper_updates:
        security_count = sum(
            1 for p in zypper_updates
            if isinstance(p, dict) and p.get("category", "").lower() == "security"
        )
        total_count = max(total_count, len(zypper_updates))

    if security_count > 0:
        findings.append(_finding(
            severity=WARNING,
            category="Updates",
            title=f"{security_count} security update{'s' if security_count != 1 else ''} pending",
            detail=f"{total_count} total updates available",
            section_link="updates",
        ))
    elif total_count > 20:
        findings.append(_finding(
            severity=WARNING,
            category="Updates",
            title=f"{total_count} updates pending",
            detail="System may be behind on patches",
            section_link="updates",
        ))
    return findings


def _extract_primary_ips(network: Dict[str, Any]) -> List[str]:
    """
    Extract primary (non-loopback, non-link-local) IP addresses from
    ip addr output.
    """
    ips: list = []
    interfaces = network.get("interfaces", {})
    ip_text = interfaces.get("ip_addr", "")
    if not ip_text:
        return ips

    # Match inet/inet6 lines: "inet 10.0.0.5/24 ..."
    for match in re.finditer(
        r'inet6?\s+([\d.:a-fA-F]+)(?:/\d+)?', ip_text
    ):
        addr = match.group(1)
        # Skip loopback and link-local
        if addr.startswith("127.") or addr == "::1":
            continue
        if addr.startswith("fe80"):
            continue
        ips.append(addr)

    # Deduplicate while preserving order
    seen: set = set()
    unique: list = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            unique.append(ip)
    return unique[:6]  # Limit to 6 most relevant


def _extract_last_boot(summary: Dict[str, Any],
                       system_config: Dict[str, Any]) -> str:
    """Try to extract the last boot timestamp."""
    # From uptime string – sometimes contains "up since YYYY-MM-DD HH:MM:SS"
    uptime = summary.get("uptime", "") or ""
    m = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?)', uptime)
    if m:
        return m.group(1)

    # From journalctl list-boots
    boot_info = system_config.get("boot", {})
    if isinstance(boot_info, dict):
        list_boots = boot_info.get("list_boots", "")
        if list_boots:
            # last line typically has the current boot
            for line in reversed(list_boots.strip().splitlines()):
                m = re.search(
                    r'(\w{3}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
                    line
                )
                if m:
                    return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Main aggregation function
# ---------------------------------------------------------------------------

def compute_health_summary(
    summary: Dict[str, Any],
    system_config: Dict[str, Any],
    network: Dict[str, Any],
    logs: Dict[str, Any],
    updates: Optional[Dict[str, Any]] = None,
    format_type: str = "sosreport",
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Aggregate health data from all analyzer outputs and return a health
    summary suitable for the report template.

    Returns:
        Dictionary with keys:
            status          – "ok" | "warning" | "critical"
            critical_count  – number of critical findings
            warning_count   – number of warning findings
            findings        – list of finding dicts (severity, category, title, detail, section_link)
            kernel          – kernel version string
            distro          – PRETTY_NAME or fallback
            uptime          – raw uptime string
            last_boot       – best-effort boot timestamp
            primary_ips     – list of primary IPs
    """
    Logger.debug("Computing health summary")
    findings: list = []

    # -- Gather findings from structured data checks --
    findings.extend(_check_failed_services(system_config))
    findings.extend(_check_disk_usage(summary))
    findings.extend(_check_memory(summary))
    findings.extend(_check_updates(updates))

    # -- Evaluate JSON-based known-issue rules against raw files --
    if base_path is not None:
        rules_findings = evaluate_rules(base_path, format_type)
        findings.extend(rules_findings)
    else:
        Logger.debug("Rules engine skipped: no base_path provided")

    # -- Compute aggregate status --
    critical_count = sum(1 for f in findings if f["severity"] == CRITICAL)
    warning_count = sum(1 for f in findings if f["severity"] == WARNING)

    if critical_count > 0:
        overall = CRITICAL
    elif warning_count > 0:
        overall = WARNING
    else:
        overall = OK

    # -- Extract key info --
    os_info = summary.get("os_info", {})
    kernel_info = summary.get("kernel_info", {})
    kernel_version = kernel_info.get("version", "Unknown")
    distro = (os_info.get("PRETTY_NAME")
              or os_info.get("NAME", "Unknown"))
    uptime = summary.get("uptime", "Unknown") or "Unknown"
    last_boot = _extract_last_boot(summary, system_config)
    primary_ips = _extract_primary_ips(network)

    # Sort findings: critical first, then warnings
    severity_order = {CRITICAL: 0, WARNING: 1, OK: 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 9))

    health = {
        "status": overall,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "findings": findings,
        "kernel": kernel_version,
        "distro": distro,
        "uptime": uptime,
        "last_boot": last_boot,
        "primary_ips": primary_ips,
    }

    Logger.debug(
        f"Health summary: status={overall}, "
        f"critical={critical_count}, warnings={warning_count}, "
        f"findings={len(findings)}"
    )
    return health
