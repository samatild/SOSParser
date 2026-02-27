#!/usr/bin/env python3

import os
import re
import secrets
import sys
import uuid
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    abort,
    flash,
    make_response,
    after_this_request,
    jsonify,
    Response,
    stream_with_context,
)
from werkzeug.utils import secure_filename
import shutil

# Import audit logger (use relative import for proper package structure)
from webapp.audit_logger import AuditLogger

# Cleanup stale uploads after 1 hour
UPLOAD_SESSION_TTL = 3600

# File-based session storage (works with multiple gunicorn workers)
import json
import fcntl
import subprocess
import io
from queue import Queue, Empty

def _get_session_file(uploads_dir: Path, upload_id: str) -> Path:
    """Get path to session metadata file."""
    return uploads_dir / f"_chunked_{upload_id}" / "session.json"

def _read_session(uploads_dir: Path, upload_id: str) -> dict | None:
    """Read session from file with locking."""
    session_file = _get_session_file(uploads_dir, upload_id)
    if not session_file.exists():
        return None
    try:
        with open(session_file, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            # Convert received_chunks back to set
            data["received_chunks"] = set(data.get("received_chunks", []))
            return data
    except Exception:
        return None

def _write_session(uploads_dir: Path, upload_id: str, session: dict) -> bool:
    """Write session to file with locking."""
    session_file = _get_session_file(uploads_dir, upload_id)
    try:
        session_file.parent.mkdir(parents=True, exist_ok=True)
        # Convert set to list for JSON serialization
        session_copy = session.copy()
        session_copy["received_chunks"] = list(session.get("received_chunks", set()))
        with open(session_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(session_copy, f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception:
        return False

def _delete_session(uploads_dir: Path, upload_id: str) -> dict | None:
    """Delete session and return its data."""
    session = _read_session(uploads_dir, upload_id)
    if session:
        session_file = _get_session_file(uploads_dir, upload_id)
        try:
            session_file.unlink(missing_ok=True)
        except Exception:
            pass
    return session


# Analysis state storage
def _get_analysis_dir(outputs_dir: Path, token: str) -> Path:
    """Get path to analysis state directory."""
    return outputs_dir / token

def _get_analysis_state_file(outputs_dir: Path, token: str) -> Path:
    """Get path to analysis state file."""
    return _get_analysis_dir(outputs_dir, token) / "_analysis_state.json"

def _get_analysis_log_file(outputs_dir: Path, token: str) -> Path:
    """Get path to analysis log file."""
    return _get_analysis_dir(outputs_dir, token) / "_analysis.log"

def _read_analysis_state(outputs_dir: Path, token: str) -> dict | None:
    """Read analysis state from file."""
    state_file = _get_analysis_state_file(outputs_dir, token)
    if not state_file.exists():
        return None
    try:
        with open(state_file, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return data
    except Exception:
        return None

def _write_analysis_state(outputs_dir: Path, token: str, state: dict) -> bool:
    """Write analysis state to file."""
    state_file = _get_analysis_state_file(outputs_dir, token)
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception:
        return False

def _append_log(outputs_dir: Path, token: str, message: str) -> None:
    """Append a log message to the analysis log file."""
    log_file = _get_analysis_log_file(outputs_dir, token)
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(f"{message}\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_src_on_syspath():
    src_path = _project_root() / "src"
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_src_on_syspath()

# Import after sys.path adjusted
try:
    from core.analyzer import run_analysis
except Exception as e:
    print(f"ERROR: Failed to import run_analysis: {e}")
    raise

try:
    from utils.file_operations import peek_sar_files
except Exception as e:
    print(f"ERROR: Failed to import peek_sar_files: {e}")
    raise

try:
    from __version__ import __version__
except Exception as e:
    print(f"WARNING: Failed to import version: {e}")
    __version__ = "unknown"


# Allowed tarball extensions for sosreport
ALLOWED_EXTENSIONS = {"xz", "gz", "bz2", "tar"}


def allowed_tarball(filename: str) -> bool:
    """Check if file is a valid tarball format"""
    if not filename or "." not in filename:
        return False
    # Check for .tar.xz, .txz, .tar.gz, .tar.bz2, .tgz, .tar
    lower = filename.lower()
    return (
        lower.endswith('.tar.xz') or
        lower.endswith('.txz') or  # Supportconfig format
        lower.endswith('.tar.gz') or 
        lower.endswith('.tar.bz2') or
        lower.endswith('.tgz') or
        lower.endswith('.tar')
    )


def _cleanup_dir_contents(target_dir: Path) -> None:
    """Remove all contents of a directory but keep the directory itself"""
    try:
        if not target_dir.exists():
            return
        for child in target_dir.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    try:
                        child.unlink()
                    except FileNotFoundError:
                        pass
            except Exception:
                pass
    except Exception:
        pass


def _remove_dir(target_dir: Path) -> None:
    """Remove entire directory"""
    try:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
    except Exception:
        pass


_SCRIPT_TAG_PATTERN = re.compile(r"<script\b(?![^>]*\snonce=)([^>]*)>", re.IGNORECASE)


def _inject_script_nonce(html: str, nonce: str) -> str:
    """Add CSP nonces to trusted script tags so inline JS continues to run."""
    def _add_nonce(match: re.Match) -> str:
        attrs = match.group(1)
        return f"<script{attrs} nonce=\"{nonce}\">"

    return _SCRIPT_TAG_PATTERN.sub(_add_nonce, html)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    # Basic config
    app.config["SECRET_KEY"] = os.environ.get("WEBAPP_SECRET_KEY", "sosparser-dev-key")
    # Public mode: no report storage, no saved reports browser
    public_mode = os.environ.get("PUBLIC_MODE", "false").lower() in ("true", "1", "yes")
    app.config["PUBLIC_MODE"] = public_mode
    
    # Debug mode: enables memory tracking and verbose logging
    debug_mode = os.environ.get("WEBAPP_DEBUG", "false").lower() in ("true", "1", "yes")
    app.config["DEBUG_MODE"] = debug_mode
    
    # Initialize audit logger (active in public mode only)
    audit_logger = AuditLogger(enabled=public_mode)
    app.config["AUDIT_LOGGER"] = audit_logger
    
    if public_mode:
        print("[INFO] Running in PUBLIC_MODE - audit logging enabled")
    
    base_dir = Path(__file__).parent
    uploads_dir = base_dir / "uploads"
    outputs_dir = base_dir / "outputs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(uploads_dir)
    app.config["OUTPUT_FOLDER"] = str(outputs_dir)
    # Allow larger files for sosreports (up to 2GB default)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("WEBAPP_MAX_CONTENT_MB", "2048")) * 1024 * 1024

    # Report asset passthrough (serve analyzer report assets from src)
    report_templates_dir = _project_root() / "src" / "templates"
    report_styles_dir = report_templates_dir / "styles"
    report_scripts_dir = report_templates_dir / "scripts"
    report_images_dir = report_templates_dir / "images"

    @app.get("/report-assets/styles/<path:filename>")
    def report_styles(filename: str):
        return send_from_directory(str(report_styles_dir), filename, as_attachment=False)

    @app.get("/report-assets/scripts/<path:filename>")
    def report_scripts(filename: str):
        return send_from_directory(str(report_scripts_dir), filename, as_attachment=False)

    @app.get("/report-assets/images/<path:filename>")
    def report_images(filename: str):
        return send_from_directory(str(report_images_dir), filename, as_attachment=False)

    # Cleanup uploads/ on startup
    _cleanup_dir_contents(uploads_dir)
    # In public mode, also cleanup outputs/ on startup (no persistence)
    if public_mode:
        _cleanup_dir_contents(outputs_dir)

    # Helper function to get client IP address
    def _get_client_ip() -> str:
        """Get client IP address, accounting for proxies."""
        # Check X-Forwarded-For header (for proxies/load balancers)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        # Check X-Real-IP header
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        # Fall back to remote_addr
        return request.remote_addr or 'unknown'
    
    # Audit logging hooks
    @app.before_request
    def log_request():
        """Log all requests in public mode."""
        if audit_logger.enabled:
            # Store request start time for duration calculation
            request.start_time = time.time()
            # Skip logging for static assets and health checks
            if request.path.startswith('/report-assets/') or request.path == '/healthz':
                return
            # Log will be completed in after_request with status code
    
    @app.after_request
    def log_response(response):
        """Log response details in public mode."""
        if audit_logger.enabled and hasattr(request, 'start_time'):
            # Skip logging for static assets and health checks
            if request.path.startswith('/report-assets/') or request.path == '/healthz':
                return response
            
            audit_logger.log_page_access(
                path=request.path,
                method=request.method,
                ip_address=_get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status_code=response.status_code
            )
        return response

    @app.get("/")
    def index():
        exec_ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return render_template(
            "index.html",
            execution_timestamp=exec_ts,
            version=__version__,
            public_mode=app.config["PUBLIC_MODE"],
        )

    @app.post("/analyze")
    def analyze():
        """Handle file upload and analysis"""
        tarball_file = request.files.get("sosreport_file")
        
        if not tarball_file or tarball_file.filename == "":
            flash("SOSReport file is required.", "error")
            return redirect(url_for("index"))

        if not allowed_tarball(tarball_file.filename):
            flash("Only .tar.xz, .txz, .tar.gz, .tar.bz2, .tgz, and .tar files are accepted.", "error")
            return redirect(url_for("index"))

        # Create a unique token directory for this analysis
        token = datetime.utcnow().strftime("%Y%m%d%H%M%S") + f"-{uuid.uuid4().hex[:8]}"

        upload_token_dir = Path(app.config["UPLOAD_FOLDER"]) / token
        output_token_dir = Path(app.config["OUTPUT_FOLDER"]) / token
        upload_token_dir.mkdir(parents=True, exist_ok=True)
        output_token_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        tarball_filename = secure_filename(tarball_file.filename)
        tarball_path = upload_token_dir / tarball_filename
        tarball_file.save(str(tarball_path))
        
        # Audit log: report generation started
        if audit_logger.enabled:
            file_size = tarball_path.stat().st_size
            audit_logger.log_report_generation_started(
                token=token,
                filename=tarball_filename,
                file_size=file_size,
                ip_address=_get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown'),
                upload_method='direct'
            )

        # Run the analyzer (always probe all SAR files; chunked upload has the interactive selector)
        try:
            output_report_path = run_analysis(
                str(tarball_path),
                debug_mode=app.config.get("DEBUG_MODE", False),
                save_next_to_tarball=False,
                output_dir_override=str(output_token_dir),
            )
            
            # Audit log: report generation completed successfully
            if audit_logger.enabled:
                audit_logger.log_report_generation_completed(
                    token=token,
                    success=True,
                    ip_address=_get_client_ip(),
                    user_agent=request.headers.get('User-Agent', 'unknown')
                )
        except Exception as e:
            # Audit log: report generation failed
            if audit_logger.enabled:
                audit_logger.log_report_generation_completed(
                    token=token,
                    success=False,
                    ip_address=_get_client_ip(),
                    user_agent=request.headers.get('User-Agent', 'unknown'),
                    error_message=str(e)
                )
            flash(f"Analysis failed: {e}", "error")
            return redirect(url_for("index"))

        # Redirect to served report
        try:
            rel_path = str(Path(output_report_path).relative_to(output_token_dir))
        except Exception:
            rel_path = "report.html"

        redirect_url = url_for("view_report", token=token, path=rel_path)
        return redirect(redirect_url)

    # ========== Chunked Upload API ==========
    
    def _cleanup_stale_uploads():
        """Remove upload sessions older than TTL"""
        now = time.time()
        uploads_dir = Path(app.config["UPLOAD_FOLDER"])
        try:
            for entry in uploads_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("_chunked_"):
                    session_file = entry / "session.json"
                    if session_file.exists():
                        try:
                            with open(session_file, "r") as f:
                                data = json.load(f)
                            if now - data.get("created", 0) > UPLOAD_SESSION_TTL:
                                _remove_dir(entry)
                        except Exception:
                            # If we can't read it, check dir age
                            try:
                                if now - entry.stat().st_mtime > UPLOAD_SESSION_TTL:
                                    _remove_dir(entry)
                            except Exception:
                                pass
        except Exception:
            pass
    
    @app.post("/api/upload/init")
    def upload_init():
        """Initialize a chunked upload session.
        
        Request JSON:
            filename: Original filename
            fileSize: Total file size in bytes
            chunkSize: Size of each chunk (optional, default 5MB)
        
        Response JSON:
            uploadId: Unique upload session ID
            chunkSize: Confirmed chunk size
        """
        _cleanup_stale_uploads()
        
        data = request.get_json() or {}
        filename = data.get("filename", "")
        file_size = data.get("fileSize", 0)
        chunk_size = data.get("chunkSize", 5 * 1024 * 1024)  # Default 5MB chunks
        
        if not filename:
            return jsonify({"error": "Filename is required"}), 400
        
        if not allowed_tarball(filename):
            return jsonify({"error": "Invalid file type. Only .tar.xz, .txz, .tar.gz, .tar.bz2, .tgz, and .tar files are accepted."}), 400
        
        max_size = app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024)
        if file_size > max_size:
            return jsonify({"error": f"File too large. Maximum size is {max_size // (1024*1024)} MB"}), 400
        
        upload_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:12]}"
        
        # Create temp directory for chunks
        uploads_dir = Path(app.config["UPLOAD_FOLDER"])
        temp_dir = uploads_dir / f"_chunked_{upload_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        total_chunks = (file_size + chunk_size - 1) // chunk_size if file_size > 0 else 1
        
        session = {
            "filename": secure_filename(filename),
            "file_size": file_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "received_chunks": set(),
            "temp_dir": str(temp_dir),
            "created": time.time(),
        }
        
        if not _write_session(uploads_dir, upload_id, session):
            _remove_dir(temp_dir)
            return jsonify({"error": "Failed to create upload session"}), 500
        
        # Audit log: chunked upload initiated
        if audit_logger.enabled:
            audit_logger.log_upload_chunk_initiated(
                upload_id=upload_id,
                filename=filename,
                file_size=file_size,
                total_chunks=total_chunks,
                ip_address=_get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown')
            )
        
        return jsonify({
            "uploadId": upload_id,
            "chunkSize": chunk_size,
            "totalChunks": total_chunks,
        })
    
    @app.post("/api/upload/chunk")
    def upload_chunk():
        """Upload a single chunk.
        
        Form data:
            uploadId: Upload session ID
            chunkIndex: Zero-based chunk index
            chunk: The file chunk data
        
        Response JSON:
            received: Number of chunks received so far
            totalChunks: Total expected chunks
            complete: Whether all chunks have been received
        """
        upload_id = request.form.get("uploadId")
        chunk_index = request.form.get("chunkIndex")
        chunk_file = request.files.get("chunk")
        
        if not upload_id or chunk_index is None or not chunk_file:
            return jsonify({"error": "Missing uploadId, chunkIndex, or chunk data"}), 400
        
        try:
            chunk_index = int(chunk_index)
        except ValueError:
            return jsonify({"error": "Invalid chunkIndex"}), 400
        
        uploads_dir = Path(app.config["UPLOAD_FOLDER"])
        session = _read_session(uploads_dir, upload_id)
        if not session:
            return jsonify({"error": "Upload session not found or expired"}), 404
        
        temp_dir = session["temp_dir"]
        total_chunks = session["total_chunks"]
        
        if chunk_index < 0 or chunk_index >= total_chunks:
            return jsonify({"error": f"Invalid chunkIndex. Expected 0-{total_chunks-1}"}), 400
        
        # Save chunk to temp directory
        chunk_path = Path(temp_dir) / f"chunk_{chunk_index:06d}"
        chunk_file.save(str(chunk_path))
        
        # Update session with new chunk
        session["received_chunks"].add(chunk_index)
        received = len(session["received_chunks"])
        complete = received == total_chunks
        
        if not _write_session(uploads_dir, upload_id, session):
            return jsonify({"error": "Failed to update session"}), 500
        
        return jsonify({
            "received": received,
            "totalChunks": total_chunks,
            "complete": complete,
        })
    
    def _run_analysis_with_logging(tarball_path: str, output_dir: str, token: str, outputs_dir: Path,
                                    allowed_sar_files: list | None = None):
        """Run analysis in background thread with logging."""
        import sys
        import io
        
        _append_log(outputs_dir, token, "Starting analysis...")
        _append_log(outputs_dir, token, f"Input file: {Path(tarball_path).name}")
        
        try:
            # Capture stdout/stderr during analysis
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            class LogCapture(io.StringIO):
                def __init__(self, token, outputs_dir, original):
                    super().__init__()
                    self.token = token
                    self.outputs_dir = outputs_dir
                    self.original = original
                    self.buffer_line = ""
                
                def write(self, s):
                    if self.original:
                        self.original.write(s)
                    # Buffer and write complete lines
                    self.buffer_line += s
                    while "\n" in self.buffer_line:
                        line, self.buffer_line = self.buffer_line.split("\n", 1)
                        if line.strip():
                            _append_log(self.outputs_dir, self.token, line.strip())
                    return len(s)
                
                def flush(self):
                    if self.buffer_line.strip():
                        _append_log(self.outputs_dir, self.token, self.buffer_line.strip())
                        self.buffer_line = ""
                    if self.original:
                        self.original.flush()
            
            sys.stdout = LogCapture(token, outputs_dir, old_stdout)
            sys.stderr = LogCapture(token, outputs_dir, old_stderr)
            
            try:
                output_report_path = run_analysis(
                    tarball_path,
                    debug_mode=app.config.get("DEBUG_MODE", False),
                    save_next_to_tarball=False,
                    output_dir_override=output_dir,
                    allowed_sar_files=allowed_sar_files,
                )
                
                # Determine redirect URL
                try:
                    rel_path = str(Path(output_report_path).relative_to(output_dir))
                except Exception:
                    rel_path = "report.html"
                
                _append_log(outputs_dir, token, "Analysis complete!")
                _append_log(outputs_dir, token, f"Report generated: {rel_path}")
                
                _write_analysis_state(outputs_dir, token, {
                    "status": "complete",
                    "report_path": rel_path,
                    "completed_at": time.time(),
                })
                
                # Audit log: report generation completed successfully
                # Note: This runs in background thread, so we can't get request context
                # Main audit logging for completion happens in the analyze() and upload_complete() routes
                
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
        except Exception as e:
            _append_log(outputs_dir, token, f"ERROR: Analysis failed: {e}")
            _write_analysis_state(outputs_dir, token, {
                "status": "error",
                "error": str(e),
                "completed_at": time.time(),
            })
    
    @app.post("/api/upload/complete")
    def upload_complete():
        """Finalize the upload and start analysis in background.

        Request JSON:
            uploadId:   Upload session ID
            analyzeSar: If true (default), peek tarball for SAR files and return
                        a 'sar_selection' response so the user can choose which
                        days to analyze.  If false, skip SAR analysis entirely.

        Response JSON (normal):
            status: "processing"
            token:  Analysis token for tracking progress

        Response JSON (SAR selection):
            status:   "sar_selection"
            token:    Analysis token
            sarFiles: list of {name, date_display, ...} dicts
        """
        data = request.get_json() or {}
        upload_id = data.get("uploadId")
        analyze_sar = data.get("analyzeSar", True)

        if not upload_id:
            return jsonify({"error": "uploadId is required"}), 400

        uploads_dir = Path(app.config["UPLOAD_FOLDER"])
        session = _delete_session(uploads_dir, upload_id)

        if not session:
            return jsonify({"error": "Upload session not found or expired"}), 404

        temp_dir = Path(session["temp_dir"])
        filename = session["filename"]
        total_chunks = session["total_chunks"]
        received = session["received_chunks"]

        if len(received) != total_chunks:
            missing = total_chunks - len(received)
            _remove_dir(temp_dir)
            return jsonify({"error": f"Upload incomplete. Missing {missing} chunks."}), 400

        # Create final upload directory
        token = datetime.utcnow().strftime("%Y%m%d%H%M%S") + f"-{uuid.uuid4().hex[:8]}"
        upload_token_dir = Path(app.config["UPLOAD_FOLDER"]) / token
        output_token_dir = Path(app.config["OUTPUT_FOLDER"]) / token
        upload_token_dir.mkdir(parents=True, exist_ok=True)
        output_token_dir.mkdir(parents=True, exist_ok=True)

        # Initialize analysis state
        outputs_dir = Path(app.config["OUTPUT_FOLDER"])
        _write_analysis_state(outputs_dir, token, {
            "status": "processing",
            "started_at": time.time(),
            "filename": filename,
        })
        _append_log(outputs_dir, token, f"Reassembling file from {total_chunks} chunks...")

        # Reassemble file from chunks using streaming copy
        # Uses shutil.copyfileobj to avoid loading entire chunks into memory
        tarball_path = upload_token_dir / filename
        try:
            import shutil
            with open(tarball_path, "wb") as outfile:
                for i in range(total_chunks):
                    chunk_path = temp_dir / f"chunk_{i:06d}"
                    with open(chunk_path, "rb") as chunk:
                        shutil.copyfileobj(chunk, outfile, length=64 * 1024)  # 64KB buffer
            _append_log(outputs_dir, token, f"File reassembled: {filename}")
        except Exception as e:
            _remove_dir(temp_dir)
            _remove_dir(upload_token_dir)
            _append_log(outputs_dir, token, f"ERROR: Failed to reassemble file: {e}")
            _write_analysis_state(outputs_dir, token, {"status": "error", "error": str(e)})
            return jsonify({"error": f"Failed to reassemble file: {e}"}), 500
        finally:
            # Clean up temp chunks directory
            _remove_dir(temp_dir)

        # Audit log: report generation started (chunked upload)
        if audit_logger.enabled:
            file_size = tarball_path.stat().st_size
            audit_logger.log_report_generation_started(
                token=token,
                filename=filename,
                file_size=file_size,
                ip_address=_get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown'),
                upload_method='chunked'
            )

        # ── SAR-selection flow ───────────────────────────────────────────────
        if analyze_sar:
            sar_peek = peek_sar_files(tarball_path)
            if sar_peek['files']:
                _write_analysis_state(outputs_dir, token, {
                    "status": "sar_selection",
                    "filename": filename,
                    "tarball_path": str(tarball_path),
                    "output_dir": str(output_token_dir),
                    "created": time.time(),
                })
                _append_log(outputs_dir, token,
                            f"Found {len(sar_peek['files'])} SAR file(s) – waiting for selection...")
                return jsonify({
                    "status": "sar_selection",
                    "token": token,
                    "sarFiles": sar_peek['files'],
                })
            # No SAR files found – fall through to normal analysis

        # ── Normal / skip-SAR flow ──────────────────────────────────────────
        # allowed_sar_files=[] means "skip SAR"; None means "analyze all"
        allowed_sar_files = [] if not analyze_sar else None

        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=_run_analysis_with_logging,
            args=(str(tarball_path), str(output_token_dir), token, outputs_dir, allowed_sar_files),
            daemon=True,
        )
        analysis_thread.start()

        return jsonify({
            "status": "processing",
            "token": token,
        })

    @app.post("/api/upload/start-analysis")
    def upload_start_analysis():
        """Start analysis after a SAR-selection step.

        Request JSON:
            token:            Analysis token returned by /api/upload/complete
            selectedSarFiles: List of bare filenames to analyze (e.g.
                              ['sar20251118.xz', 'sar20251119.xz']).
                              An empty list skips SAR entirely.

        Response JSON:
            status: "processing"
            token:  Same token
        """
        data = request.get_json() or {}
        token = data.get("token")
        selected_sar_files = data.get("selectedSarFiles")  # list or None

        if not token:
            return jsonify({"error": "token is required"}), 400

        outputs_dir = Path(app.config["OUTPUT_FOLDER"])
        state = _read_analysis_state(outputs_dir, token)

        if not state:
            return jsonify({"error": "Analysis not found"}), 404

        if state.get("status") != "sar_selection":
            return jsonify({"error": "Analysis is not awaiting SAR selection"}), 400

        tarball_path = state.get("tarball_path")
        output_dir   = state.get("output_dir")
        filename     = state.get("filename", "")

        if not tarball_path or not output_dir:
            return jsonify({"error": "Corrupt state: missing paths"}), 500

        n_selected = len(selected_sar_files) if selected_sar_files is not None else "all"
        _append_log(outputs_dir, token, f"Starting analysis with {n_selected} SAR file(s)...")
        _write_analysis_state(outputs_dir, token, {
            "status": "processing",
            "started_at": time.time(),
            "filename": filename,
        })

        analysis_thread = threading.Thread(
            target=_run_analysis_with_logging,
            args=(tarball_path, output_dir, token, outputs_dir, selected_sar_files),
            daemon=True,
        )
        analysis_thread.start()

        return jsonify({"status": "processing", "token": token})
    
    @app.get("/api/analysis/<token>/status")
    def analysis_status(token: str):
        """Get the current status of an analysis."""
        outputs_dir = Path(app.config["OUTPUT_FOLDER"])
        state = _read_analysis_state(outputs_dir, token)
        
        if not state:
            return jsonify({"error": "Analysis not found"}), 404
        
        response = {"status": state.get("status", "unknown")}
        
        if state.get("status") == "complete":
            rel_path = state.get("report_path", "report.html")
            response["redirectUrl"] = url_for("view_report", token=token, path=rel_path)
        elif state.get("status") == "error":
            response["error"] = state.get("error", "Unknown error")
        
        return jsonify(response)
    
    @app.get("/api/analysis/<token>/logs")
    def analysis_logs(token: str):
        """Stream analysis logs via Server-Sent Events."""
        outputs_dir = Path(app.config["OUTPUT_FOLDER"])
        log_file = _get_analysis_log_file(outputs_dir, token)
        
        def generate():
            last_position = 0
            no_data_count = 0
            
            while True:
                state = _read_analysis_state(outputs_dir, token)
                
                # Read new log lines
                try:
                    if log_file.exists():
                        with open(log_file, "r") as f:
                            f.seek(last_position)
                            new_lines = f.read()
                            last_position = f.tell()
                        
                        if new_lines:
                            no_data_count = 0
                            for line in new_lines.strip().split("\n"):
                                if line:
                                    yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
                except Exception:
                    pass
                
                # Check if analysis is complete
                if state and state.get("status") in ("complete", "error"):
                    if state.get("status") == "complete":
                        rel_path = state.get("report_path", "report.html")
                        redirect_url = url_for("view_report", token=token, path=rel_path)
                        yield f"data: {json.dumps({'type': 'complete', 'redirectUrl': redirect_url})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': state.get('error', 'Unknown error')})}\n\n"
                    break
                
                # Heartbeat to keep connection alive
                no_data_count += 1
                if no_data_count >= 10:  # Every ~5 seconds
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    no_data_count = 0
                
                time.sleep(0.5)
        
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    
    @app.delete("/api/upload/<upload_id>")
    def upload_cancel(upload_id: str):
        """Cancel an in-progress upload and clean up."""
        uploads_dir = Path(app.config["UPLOAD_FOLDER"])
        session = _delete_session(uploads_dir, upload_id)
        
        if session and session.get("temp_dir"):
            _remove_dir(Path(session["temp_dir"]))
        
        return jsonify({"status": "ok"})

    def _collect_reports() -> list[dict]:
        """Enumerate saved reports under OUTPUT_FOLDER."""
        output_root = Path(app.config["OUTPUT_FOLDER"]).resolve()
        if not output_root.exists():
            return []
        items: list[dict] = []
        for entry in output_root.iterdir():
            if not entry.is_dir():
                continue
            token = entry.name
            try:
                # ensure within root
                entry.resolve().relative_to(output_root)
            except Exception:
                continue
            # Try to locate a report file (prefer report.html, search recursively)
            report_path = None
            candidate = entry / "report.html"
            if candidate.exists():
                report_path = candidate
            else:
                html_files = sorted(entry.rglob("*.html"))
                if html_files:
                    report_path = html_files[0]
            if not report_path:
                continue
            try:
                rel = report_path.relative_to(entry)
            except Exception:
                continue
            stat = report_path.stat()
            items.append(
                {
                    "token": token,
                    "path": str(rel),
                    "url": url_for("view_report", token=token, path=str(rel)),
                    "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
                    "size": stat.st_size,
                }
            )
        items.sort(key=lambda x: x["modified"], reverse=True)
        return items

    @app.get("/api/reports")
    def list_reports():
        """List saved reports for browsing."""
        if app.config["PUBLIC_MODE"]:
            # Public mode: report storage disabled
            return jsonify({"items": [], "public_mode": True})
        return jsonify({"items": _collect_reports()})

    @app.delete("/api/reports/<token>")
    def delete_report(token: str):
        """Delete a saved report by token."""
        if app.config["PUBLIC_MODE"]:
            # Public mode: manual deletion disabled
            abort(403)
        output_root = Path(app.config["OUTPUT_FOLDER"]).resolve()
        base = (output_root / secure_filename(token)).resolve()
        try:
            base.relative_to(output_root)
        except Exception:
            abort(404)
        if base.exists():
            try:
                shutil.rmtree(base, ignore_errors=True)
            except Exception:
                abort(500)
        return jsonify({"status": "ok"})

    @app.get("/reports/<token>/<path:filename>")
    def serve_report_file(token: str, filename: str):
        """Serve report files"""
        base = (Path(app.config["OUTPUT_FOLDER"]) / secure_filename(token)).resolve()
        if not base.exists():
            abort(404)
        return send_from_directory(str(base), filename, as_attachment=False)

    @app.get("/view/<token>")
    def view_report(token: str):
        """View report and cleanup after delivery"""
        rel_path = request.args.get("path", "report.html")
        base = (Path(app.config["OUTPUT_FOLDER"]) / secure_filename(token)).resolve()
        if not base.exists():
            abort(404)
        try:
            report_path = (base / rel_path).resolve()
            report_path.relative_to(base)
        except Exception:
            abort(404)
        if not report_path.exists():
            abort(404)
        try:
            html = report_path.read_text(encoding="utf-8")
        except Exception:
            abort(500)

        # Rewrite asset references to shared assets
        html = html.replace("href=\"styles/", "href=\"/report-assets/styles/")
        html = html.replace("src=\"scripts/", "src=\"/report-assets/scripts/")
        html = html.replace("src=\"images/", "src=\"/report-assets/images/")
        html = html.replace("href=\"images/", "href=\"/report-assets/images/")        
        # Audit log: report viewed
        if audit_logger.enabled:
            audit_logger.log_report_viewed(
                token=token,
                report_path=rel_path,
                ip_address=_get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown')
            )
        # Cleanup uploads after response
        # In public mode, also cleanup outputs (no persistence)
        uploads_token_dir = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(token)
        outputs_token_dir = Path(app.config["OUTPUT_FOLDER"]) / secure_filename(token)
        is_public_mode = app.config["PUBLIC_MODE"]

        @after_this_request
        def _cleanup(response):
            try:
                _remove_dir(uploads_token_dir)
            except Exception:
                pass
            if is_public_mode:
                # Public mode: remove outputs after viewing (no storage)
                try:
                    _remove_dir(outputs_token_dir)
                except Exception:
                    pass
            return response

        script_nonce = secrets.token_urlsafe(16)
        html = _inject_script_nonce(html, script_nonce)
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{script_nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' https://endoflife.date; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.get("/api/version/check")
    def check_version():
        """Check for latest version on DockerHub."""
        current_version = __version__
        
        def parse_version(version_string):
            """Parse semantic version into tuple for comparison."""
            try:
                parts = version_string.lstrip('v').split('.')
                return tuple(int(p) for p in parts)
            except (ValueError, AttributeError):
                return (0, 0, 0)
        
        try:
            # DockerHub API endpoint for tags
            url = "https://hub.docker.com/v2/repositories/samuelmatildes/sosparser/tags/?page_size=100"
            req = Request(url)
            req.add_header('User-Agent', 'SOSParser-Version-Checker')
            
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                # Filter out 'latest' and get version tags
                version_tags = []
                for tag in data.get('results', []):
                    tag_name = tag.get('name', '')
                    # Skip 'latest' and tags that don't look like versions
                    if tag_name != 'latest' and (tag_name.startswith('0.') or tag_name.startswith('1.')):
                        version_tags.append(tag_name)
                
                if version_tags:
                    # Sort versions using semantic versioning (tuple comparison)
                    version_tags.sort(key=parse_version, reverse=True)
                    latest_version = version_tags[0]
                    
                    # Compare versions semantically
                    current_tuple = parse_version(current_version)
                    latest_tuple = parse_version(latest_version)
                    update_available = latest_tuple > current_tuple
                    
                    return jsonify({
                        "current": current_version,
                        "latest": latest_version,
                        "update_available": update_available,
                        "status": "ok"
                    })
                else:
                    return jsonify({
                        "current": current_version,
                        "latest": current_version,
                        "update_available": False,
                        "status": "no_tags_found"
                    })
                    
        except (URLError, HTTPError, json.JSONDecodeError, KeyError) as e:
            # Return current version if check fails
            return jsonify({
                "current": current_version,
                "latest": None,
                "update_available": False,
                "status": "error",
                "error": str(e)
            })

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(error):
        return "<h1>404 Not Found</h1><p>The requested resource was not found.</p>", 404

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
