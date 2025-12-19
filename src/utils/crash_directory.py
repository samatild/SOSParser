"""
Helpers for collecting crash directory listings and extracting interesting files.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Sequence


DEFAULT_INTERESTING_FILES: Sequence[str] = (
    "kexec-dmesg.log",
    "kexec-dmesg.txt",
    "vmcore-dmesg.txt",
    "vmcore-dmesg.log",
)


class CrashDirectoryCollector:
    """Collects metadata and selected files from crash dump directories."""

    def __init__(
        self,
        root_path: Path,
        *,
        interesting_filenames: Sequence[str] | None = None,
        listing_limit: int = 200,
        file_size_limit: int = 200_000,
    ):
        self.root_path = Path(root_path)
        self.listing_limit = listing_limit
        self.file_size_limit = file_size_limit
        self.interesting_filenames = set(
            interesting_filenames or DEFAULT_INTERESTING_FILES
        )

    def discover_default_directories(self) -> List[Path]:
        """Return common crash directory locations under the root path."""
        directories: List[Path] = []
        candidates = [
            self.root_path / "var_crash",
            self.root_path / "var" / "crash",
        ]
        candidates.extend(self.root_path.glob("var_crash*"))

        seen: set[Path] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            if candidate.exists() and candidate.is_dir():
                directories.append(candidate)
                seen.add(candidate)

        return directories

    def collect(self, directories: Iterable[Path]) -> Dict[str, Any]:
        """Collect listings and interesting files from the provided directories."""
        snapshots = []
        for directory in directories:
            for target in self._expand_target_directories(directory):
                snapshot = self._snapshot_directory(target)
                if snapshot:
                    snapshots.append(snapshot)

        return {"directories": snapshots} if snapshots else {}

    def _expand_target_directories(self, directory: Path) -> Iterable[Path]:
        """Yield directories that actually contain files, diving into subdirs when needed."""
        queue: Deque[Path] = deque([directory])
        seen: set[Path] = set()

        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)

            if not current.exists() or not current.is_dir():
                continue

            children = self._safe_iterdir(current)
            has_files = any(child.is_file() for child in children)

            if has_files:
                yield current

            for child in children:
                if child.is_dir():
                    queue.append(child)

    def _safe_iterdir(self, directory: Path) -> List[Path]:
        try:
            return sorted(directory.iterdir())
        except Exception:
            return []

    def _snapshot_directory(self, directory: Path) -> Dict[str, Any]:
        entries = self._render_directory_listing(directory)
        files = self._read_interesting_files(directory)

        if not entries and not files:
            return {}

        data: Dict[str, Any] = {"path": self._relative_to_root(directory)}
        if entries:
            data["entries"] = entries
        if files:
            data["files"] = files
        return data

    def _render_directory_listing(self, directory: Path) -> List[str]:
        entries: List[str] = []
        try:
            paths = sorted(directory.rglob("*"))
        except Exception:
            return ["Unable to read directory contents"]

        for path in paths:
            relative = path.relative_to(directory)
            if not str(relative):
                continue

            entry_type = "dir" if path.is_dir() else "file"
            size = 0
            if path.is_file():
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0

            entries.append(f"{entry_type:4} {size:>10} {relative}")
            if len(entries) >= self.listing_limit:
                entries.append("... listing truncated ...")
                break

        if not entries:
            entries.append("(empty)")

        return entries

    def _read_interesting_files(self, directory: Path) -> List[Dict[str, str]]:
        collected: List[Dict[str, str]] = []
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.name not in self.interesting_filenames:
                continue

            content = self._read_text_with_limit(path)
            if content is None:
                continue
            relative_path = str(path.relative_to(directory))
            collected.append({"path": relative_path, "content": content})

        return collected

    def _read_text_with_limit(self, path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                data = handle.read(self.file_size_limit + 1)
        except Exception:
            return None

        if len(data) > self.file_size_limit:
            return data[: self.file_size_limit] + "\n... truncated ..."
        return data

    def _relative_to_root(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root_path))
        except ValueError:
            return str(path)
