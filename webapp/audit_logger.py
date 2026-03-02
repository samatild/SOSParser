#!/usr/bin/env python3
"""
Audit logging module for SOSParser webapp.
Logs security and usage events when running in PUBLIC_MODE.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


class AuditLogger:
    """Audit logger for tracking security and usage events in public mode."""
    
    def __init__(self, enabled: bool = False):
        """
        Initialize the audit logger.
        
        Args:
            enabled: Whether audit logging is active (should be True in PUBLIC_MODE)
        """
        self.enabled = enabled
        self.logger = self._setup_logger() if enabled else None
    
    def _setup_logger(self) -> logging.Logger:
        """Configure structured audit logger that writes to stdout."""
        logger = logging.getLogger("sosparser.audit")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # JSON formatter for structured logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Custom format for audit events
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S UTC'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _create_audit_entry(
        self,
        event_type: str,
        ip_address: str,
        user_agent: str,
        details: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Create a structured audit log entry.
        
        Args:
            event_type: Type of event (e.g., 'page_access', 'report_generated')
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional event-specific details
        
        Returns:
            Dictionary containing audit entry
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "ip_address": ip_address,
            "user_agent": user_agent[:200] if user_agent else "unknown",  # Truncate long user agents
        }
        
        if details:
            entry["details"] = details
        
        return entry
    
    def log_page_access(
        self,
        path: str,
        method: str,
        ip_address: str,
        user_agent: str,
        status_code: Optional[int] = None
    ) -> None:
        """
        Log page access event.
        
        Args:
            path: Request path
            method: HTTP method
            ip_address: Client IP address
            user_agent: Client user agent
            status_code: HTTP response status code (if available)
        """
        if not self.enabled:
            return
        
        details = {
            "path": path,
            "method": method,
        }
        
        if status_code is not None:
            details["status_code"] = status_code
        
        entry = self._create_audit_entry(
            event_type="page_access",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
    
    def log_report_generation_started(
        self,
        token: str,
        filename: str,
        file_size: int,
        ip_address: str,
        user_agent: str,
        upload_method: str = "direct"
    ) -> None:
        """
        Log when report generation starts.
        
        Args:
            token: Analysis token/session ID
            filename: Name of uploaded file
            file_size: Size of uploaded file in bytes
            ip_address: Client IP address
            user_agent: Client user agent
            upload_method: Upload method ('direct' or 'chunked')
        """
        if not self.enabled:
            return
        
        details = {
            "token": token,
            "filename": filename,
            "file_size_bytes": file_size,
            "upload_method": upload_method
        }
        
        entry = self._create_audit_entry(
            event_type="report_generation_started",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
    
    def log_report_generation_completed(
        self,
        token: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log when report generation completes.
        
        Args:
            token: Analysis token/session ID
            success: Whether generation succeeded
            ip_address: Client IP address
            user_agent: Client user agent
            error_message: Error message if generation failed
        """
        if not self.enabled:
            return
        
        details = {
            "token": token,
            "success": success
        }
        
        if error_message:
            details["error"] = error_message[:500]  # Truncate long errors
        
        entry = self._create_audit_entry(
            event_type="report_generation_completed",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
    
    def log_report_viewed(
        self,
        token: str,
        report_path: str,
        ip_address: str,
        user_agent: str
    ) -> None:
        """
        Log when a report is viewed.
        
        Args:
            token: Analysis token/session ID
            report_path: Relative path to report file
            ip_address: Client IP address
            user_agent: Client user agent
        """
        if not self.enabled:
            return
        
        details = {
            "token": token,
            "report_path": report_path
        }
        
        entry = self._create_audit_entry(
            event_type="report_viewed",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
    
    def log_upload_chunk_initiated(
        self,
        upload_id: str,
        filename: str,
        file_size: int,
        total_chunks: int,
        ip_address: str,
        user_agent: str
    ) -> None:
        """
        Log when chunked upload is initiated.
        
        Args:
            upload_id: Upload session ID
            filename: Name of file being uploaded
            file_size: Total file size in bytes
            total_chunks: Number of chunks
            ip_address: Client IP address
            user_agent: Client user agent
        """
        if not self.enabled:
            return
        
        details = {
            "upload_id": upload_id,
            "filename": filename,
            "file_size_bytes": file_size,
            "total_chunks": total_chunks
        }
        
        entry = self._create_audit_entry(
            event_type="chunked_upload_initiated",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        ip_address: str,
        user_agent: str,
        severity: str = "warning"
    ) -> None:
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            description: Description of the event
            ip_address: Client IP address
            user_agent: Client user agent
            severity: Severity level ('info', 'warning', 'critical')
        """
        if not self.enabled:
            return
        
        details = {
            "security_event": event_type,
            "description": description,
            "severity": severity
        }
        
        entry = self._create_audit_entry(
            event_type="security_event",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.logger.info(json.dumps(entry))
