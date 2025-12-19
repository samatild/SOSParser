"""
Supportconfig Crash/Kdump Analyzer

Collects crash dump related information for supportconfig bundles.
Currently only crash.txt is parsed because it already contains the
kdump/crashcontrol summary on SLES.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..parser import SupportconfigParser


class CrashConfigAnalyzer:
    """Analyzer for crash dump configuration and artifacts."""

    def __init__(self, root_path, parser: SupportconfigParser):
        """Initialize with the extracted supportconfig path and parser."""
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Return crash/kdump related information."""
        crash_info: Dict[str, Any] = {}

        crash_txt_info = self._parse_crash_related_file("crash.txt")
        if crash_txt_info:
            crash_info["crash_txt"] = crash_txt_info

        return crash_info

    def _parse_crash_related_file(self, filename: str) -> Dict[str, Any]:
        """
        Parse a crash-related supportconfig file (crash.txt, kdump.txt).
        """
        content = self.parser.read_file(filename)
        if not content:
            return {}

        sections = self.parser.extract_sections(content)
        parsed: Dict[str, Any] = {}

        command_entries = self._extract_command_sections(sections)
        if command_entries:
            parsed["commands"] = command_entries

        file_entries = self._extract_file_sections(sections)
        if file_entries:
            parsed["files"] = file_entries

        note_entries = []
        for section in sections:
            if section["type"] != "Note":
                continue
            text = section["content"].strip()
            if not text:
                continue
            lower_text = text.lower()
            if "file not found" in lower_text or "skipping" in lower_text:
                continue
            note_entries.append(text)
        if note_entries:
            parsed["notes"] = note_entries

        other_sections = []
        for section in sections:
            if section["type"] in {"Command", "File", "Note"}:
                continue
            text = section["content"].strip()
            if not text:
                continue
            lower_text = text.lower()
            if "file not found" in lower_text or "skipping" in lower_text:
                continue
            other_sections.append(
                {
                    "header": section["header"],
                    "content": text,
                }
            )
        if other_sections:
            parsed["sections"] = other_sections

        return parsed

    def _extract_command_sections(
        self, sections: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Extract command sections with their commands and output."""
        entries: List[Dict[str, str]] = []

        for section in sections:
            if section["type"] != "Command":
                continue
            command, output = self._split_command_section(section["content"])
            if not command and not output:
                continue
            entries.append(
                {
                    "header": section["header"],
                    "command": command,
                    "output": output,
                }
            )

        return entries

    def _extract_file_sections(
        self, sections: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Extract file sections (path + content)."""
        file_entries: List[Dict[str, str]] = []

        for section in sections:
            if section["type"] != "File":
                continue

            content = section["content"].strip()
            if not content:
                continue

            path_hint, body = self._parse_file_section_content(content)
            if not body:
                continue

            entry_path = path_hint or self._extract_path_from_header(section["header"])
            if not entry_path:
                continue

            file_entries.append(
                {
                    "path": entry_path,
                    "content": body,
                }
            )

        return file_entries

    def _split_command_section(self, content: str) -> tuple[str, str]:
        """Return (command, output) from a Command section body."""
        if not content:
            return ("", "")

        lines = content.split("\n")
        if not lines:
            return ("", "")

        first_line = lines[0].strip()
        command = ""
        body_lines = lines
        if first_line.startswith("#"):
            command = first_line.lstrip("#").strip()
            body_lines = lines[1:]

        output = "\n".join(body_lines).strip()
        return (command, output)

    def _parse_file_section_content(self, content: str) -> tuple[str, str]:
        """Return (path_hint, body) parsed from a configuration file section."""
        lines = content.splitlines()
        if not lines:
            return ("", "")

        path_line = lines[0].lstrip("#").strip()
        body = "\n".join(line for line in lines[1:]).strip()

        return (path_line, body)

    def _extract_path_from_header(self, header: str) -> str:
        """Extract a path from a File section header."""
        if not header:
            return ""
        if ":" in header:
            return header.split(":", 1)[1].strip()
        return header.strip()
