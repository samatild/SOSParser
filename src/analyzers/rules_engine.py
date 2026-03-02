#!/usr/bin/env python3
"""
Rules Engine for SOSParser

Loads known-issue rule collections from JSON files and evaluates them
against extracted diagnostic bundles (sosreport or supportconfig).

Each rule targets one or more files inside the bundle and applies a regex.
When the regex matches, a health-summary finding is produced.

No code changes are needed to add new rules — just drop a JSON file
into the ``src/rules/known_issues/`` directory.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import Logger


# ---------------------------------------------------------------------------
# Where rule collections live (relative to this file)
# ---------------------------------------------------------------------------
_RULES_DIR = Path(__file__).resolve().parent.parent / "rules" / "known_issues"

# Map of JSON flag names → Python ``re`` flag constants
_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}

# Maximum file size we're willing to read (200 KB).  Keeps memory bounded
# when scanning very large log files.
_MAX_READ_BYTES = 200_000

# Maximum number of evidence lines to attach to a single finding.
_MAX_EVIDENCE_LINES = 10


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def _load_collections(rules_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load every ``.json`` collection from the rules directory.

    Returns a list of collection dicts (each containing a ``rules`` list).
    """
    directory = rules_dir or _RULES_DIR
    collections: list = []

    if not directory.is_dir():
        Logger.debug(f"Rules directory not found: {directory}")
        return collections

    for json_path in sorted(directory.glob("*.json")):
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if "rules" in data and isinstance(data["rules"], list):
                collections.append(data)
                Logger.debug(
                    f"Loaded rule collection '{data.get('collection', json_path.stem)}' "
                    f"with {len(data['rules'])} rule(s)"
                )
            else:
                Logger.debug(f"Skipping {json_path.name}: no 'rules' array")
        except (json.JSONDecodeError, OSError) as exc:
            Logger.debug(f"Failed to load {json_path.name}: {exc}")

    return collections


def _compile_regex(pattern: str, flags: List[str]) -> Optional[re.Pattern]:
    """Compile a regex pattern with the given flag names."""
    combined = 0
    for name in flags:
        combined |= _FLAG_MAP.get(name.upper(), 0)
    try:
        return re.compile(pattern, combined)
    except re.error as exc:
        Logger.debug(f"Invalid regex '{pattern}': {exc}")
        return None


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

def _read_file_safe(path: Path, max_bytes: int = _MAX_READ_BYTES) -> str:
    """Read a file up to *max_bytes*, returning an empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(max_bytes)
    except OSError:
        return ""


def _scan_file_lines(
    compiled: "re.Pattern",
    file_path: Path,
    rel_path: str,
    max_evidence: int,
) -> List[Dict[str, Any]]:
    """
    Scan a file line-by-line and return evidence entries for matches.

    Each entry: {"file": rel_path, "line_num": int, "line": str}
    """
    evidence: List[Dict[str, Any]] = []
    content = _read_file_safe(file_path)
    if not content:
        return evidence
    for line_num, line in enumerate(content.splitlines(), start=1):
        if compiled.search(line):
            evidence.append({
                "file": rel_path,
                "line_num": line_num,
                "line": line.rstrip(),
            })
            if len(evidence) >= max_evidence:
                break
    return evidence


def _evaluate_rule(
    rule: Dict[str, Any],
    base_path: Path,
    format_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Evaluate a single rule against the extracted bundle.

    Returns a finding dict (with ``evidence`` list) if the rule triggers,
    otherwise ``None``.
    """
    # ---- applicability filter ----
    applies_to = rule.get("applies_to", "both").lower()
    if applies_to != "both" and applies_to != format_type:
        return None

    if not rule.get("enabled", True):
        return None

    # ---- resolve file paths ----
    file_paths_map = rule.get("file_paths", {})
    if isinstance(file_paths_map, dict):
        rel_paths = file_paths_map.get(format_type, [])
    elif isinstance(file_paths_map, list):
        rel_paths = file_paths_map
    else:
        rel_paths = []

    if not rel_paths:
        return None

    # ---- compile regex ----
    pattern = rule.get("regex", "")
    if not pattern:
        return None
    compiled = _compile_regex(pattern, rule.get("regex_flags", []))
    if compiled is None:
        return None

    # ---- scan files line-by-line, collecting evidence ----
    min_matches = rule.get("min_matches", 1)
    all_evidence: List[Dict[str, Any]] = []

    for rel in rel_paths:
        target = base_path / rel
        if not target.is_file():
            continue
        hits = _scan_file_lines(
            compiled, target, rel,
            max_evidence=_MAX_EVIDENCE_LINES - len(all_evidence),
        )
        all_evidence.extend(hits)
        if len(all_evidence) >= _MAX_EVIDENCE_LINES:
            break

    total_matches = len(all_evidence)
    if total_matches < min_matches:
        return None

    # ---- build finding ----
    title = rule.get("title", rule.get("name", "Unknown issue"))
    detail = rule.get("detail", "")

    title = title.replace("{match_count}", str(total_matches))
    detail = detail.replace("{match_count}", str(total_matches))

    return {
        "severity": rule.get("severity", "warning"),
        "category": rule.get("category", "Rules"),
        "title": title,
        "detail": detail,
        "section_link": rule.get("section_link", ""),
        "rule_id": rule.get("id", ""),
        "collection": "",  # filled by caller
        "evidence": all_evidence,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_rules(
    base_path: Path,
    format_type: str,
    rules_dir: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """
    Load all rule collections and evaluate them against the extracted bundle.

    Args:
        base_path:    Root directory of the extracted sosreport / supportconfig.
        format_type:  ``"sosreport"`` or ``"supportconfig"``.
        rules_dir:    Override for the rules directory (useful for tests).

    Returns:
        List of finding dicts ready for the health-summary card.
    """
    Logger.debug(f"Rules engine: evaluating rules for format '{format_type}' at {base_path}")
    collections = _load_collections(rules_dir)
    findings: List[Dict[str, str]] = []

    rule_count = 0
    for collection in collections:
        coll_name = collection.get("collection", "unknown")
        for rule in collection.get("rules", []):
            rule_count += 1
            finding = _evaluate_rule(rule, base_path, format_type)
            if finding is not None:
                finding["collection"] = coll_name
                findings.append(finding)

    Logger.debug(
        f"Rules engine: evaluated {rule_count} rule(s), "
        f"{len(findings)} finding(s) triggered"
    )
    return findings
