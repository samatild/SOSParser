#!/usr/bin/env python3

import os
import re
import secrets
import sys
import uuid
from datetime import datetime
from pathlib import Path

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
)
from werkzeug.utils import secure_filename
import shutil


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

    # Cleanup uploads/ on startup (keep outputs for persistence)
    _cleanup_dir_contents(uploads_dir)

    @app.get("/")
    def index():
        exec_ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return render_template("index.html", execution_timestamp=exec_ts, version=__version__)

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

        # Run the analyzer
        try:
            output_report_path = run_analysis(
                str(tarball_path),
                debug_mode=True,
                save_next_to_tarball=False,
                output_dir_override=str(output_token_dir),
            )
        except Exception as e:
            flash(f"Analysis failed: {e}", "error")
            return redirect(url_for("index"))

        # Redirect to served report
        try:
            rel_path = str(Path(output_report_path).relative_to(output_token_dir))
        except Exception:
            rel_path = "report.html"

        redirect_url = url_for("view_report", token=token, path=rel_path)
        return redirect(redirect_url)

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
        return jsonify({"items": _collect_reports()})

    @app.delete("/api/reports/<token>")
    def delete_report(token: str):
        """Delete a saved report by token."""
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

        # Cleanup uploads after response (keep outputs persistent)
        uploads_token_dir = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(token)

        @after_this_request
        def _cleanup(response):
            try:
                _remove_dir(uploads_token_dir)
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
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(error):
        return "<h1>404 Not Found</h1><p>The requested resource was not found.</p>", 404

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
