"""Bounded, read-only access to the repository selected in session state."""

import os
from collections.abc import Iterator
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

MAX_BYTES = 1024 * 1024
SKIP_DIRS = {".git", "target", ".venv", "node_modules", "__pycache__"}


def _ignored(parts: tuple[str, ...]) -> bool:
    return any(part.startswith(".") or part in SKIP_DIRS for part in parts)


def _resolve(root: Path, value: str) -> Path:
    requested = root / value
    resolved = requested.resolve()
    if not requested.is_relative_to(root) or not resolved.is_relative_to(root):
        raise ValueError("Refused: path is outside the project root.")
    if _ignored(requested.relative_to(root).parts[:-1]) or _ignored(
        resolved.relative_to(root).parts[:-1]
    ):
        raise ValueError("Skipped: excluded folder.")
    return resolved


def _root(tool_context: ToolContext) -> Path:
    value = tool_context.state.get("project_path")
    if not isinstance(value, str) or not value:
        raise ValueError("Refused: project_path is not set.")
    root = Path(value).resolve()
    if not root.is_dir():
        raise ValueError("Refused: project_path is not a directory.")
    return root


def _read(root: Path, path: Path) -> str:
    resolved = _resolve(root, str(path))
    if not resolved.is_file():
        raise ValueError("Skipped: not a regular file.")
    if resolved.stat().st_size > MAX_BYTES:
        raise ValueError("Skipped: file exceeds 1 MiB.")
    with resolved.open("rb") as handle:
        content = handle.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Skipped: file exceeds 1 MiB.")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Skipped: file is not UTF-8 text.") from None


def _matches(path: Path, pattern: str) -> bool:
    """Match root-relative glob segments; ** also matches zero directories."""
    parts, patterns = path.parts, Path(pattern).parts

    @lru_cache(maxsize=None)
    def match(index: int, part: int) -> bool:
        if part == len(patterns):
            return index == len(parts)
        if patterns[part] == "**":
            return match(index, part + 1) or (
                index < len(parts) and match(index + 1, part)
            )
        return (
            index < len(parts)
            and fnmatchcase(parts[index], patterns[part])
            and match(index + 1, part + 1)
        )

    return match(0, 0)


def _files(root: Path, pattern: str) -> Iterator[tuple[str, str]]:
    _resolve(root, pattern)
    relative_pattern = str((root / pattern).relative_to(root))
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = sorted(
            folder for folder in folders
            if not _ignored((folder,))
            and not (Path(directory) / folder).is_symlink()
        )
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if not _matches(relative, relative_pattern):
                continue
            try:
                content = _read(root, path)
            except (OSError, ValueError, RuntimeError):
                continue
            yield relative.as_posix(), content


def _error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return " ".join(str(exc).split())
    return "Unavailable: the requested path could not be read."


def list_files(pattern: str, tool_context: ToolContext) -> str:
    """List sorted UTF-8 files matching a root-relative glob, with a 200-file cap.

    Args:
        pattern: Glob relative to the repository root; use ** for recursion.
        tool_context: Injected context containing project_path in session state.
    """
    try:
        paths = sorted(path for path, _ in _files(_root(tool_context), pattern))
        return "\n".join([
            *paths[:200], f"{len(paths)} files; {max(0, len(paths) - 200)} omitted"
        ])
    except (OSError, ValueError, RuntimeError) as exc:
        return _error(exc)


def search_text(
    query: str, tool_context: ToolContext, glob: str = "**/*"
) -> str:
    """Search UTF-8 files for a case-insensitive substring; show up to 50 lines.

    Args:
        query: Literal substring to find, ignoring case.
        tool_context: Injected context containing project_path in session state.
        glob: Root-relative file glob, recursive by default.
    """
    try:
        matches: list[str] = []
        total = 0
        for path, content in _files(_root(tool_context), glob):
            for number, line in enumerate(content.splitlines(), start=1):
                if query.casefold() in line.casefold():
                    total += 1
                    if len(matches) < 50:
                        matches.append(f"{path}:{number}: {line}")
        return "\n".join([*matches, f"{total} matches"])
    except (OSError, ValueError, RuntimeError) as exc:
        return _error(exc)


def read_file(
    path: str,
    tool_context: ToolContext,
    start_line: int = 1,
    end_line: int = 200,
) -> str:
    """Read a UTF-8 file with one-based line numbers; return at most 200 lines.

    Args:
        path: File path relative to the repository root.
        tool_context: Injected context containing project_path in session state.
        start_line: First line to return, inclusive, starting at one.
        end_line: Last line to return, inclusive; capped at start_line plus 199.
    """
    try:
        root = _root(tool_context)
        resolved = _resolve(root, path)
        if start_line < 1 or end_line < start_line:
            return "Refused: use a positive, ordered line range."
        lines = _read(root, resolved).splitlines()
        end = min(end_line, start_line + 199)
        result = [
            f"{number}: {line}"
            for number, line in enumerate(lines[start_line - 1:end], start_line)
        ]
        return "\n".join([*result, f"{len(lines)} lines total"])
    except (OSError, ValueError, RuntimeError) as exc:
        return _error(exc)
