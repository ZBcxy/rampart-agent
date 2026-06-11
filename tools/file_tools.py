"""File System Tools - Read, write, list, search, and manage files."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict

from tools.registry import ToolDefinition, ToolRegistry


def register_file_tools(registry: ToolRegistry):
    """Register all file system tools."""
    registry.register_many([
        ToolDefinition(
            name="file_read",
            description="Read the contents of a file. Returns the file content as text.",
            func=_file_read,
            parameters={
                "path": {"type": "string", "description": "Absolute path to the file to read"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
                "max_lines": {"type": "integer", "description": "Maximum lines to read (default: all)"},
            },
            category="file",
            tags=["read", "io", "text"],
        ),
        ToolDefinition(
            name="file_write",
            description="Write content to a file. Creates the file if it doesn't exist.",
            func=_file_write,
            parameters={
                "path": {"type": "string", "description": "Absolute path to write to"},
                "content": {"type": "string", "description": "Content to write"},
                "mode": {"type": "string", "description": "Write mode: 'w' for overwrite, 'a' for append"},
            },
            category="file",
            requires_confirmation=True,
            tags=["write", "io", "text"],
        ),
        ToolDefinition(
            name="file_list",
            description="List files and directories in a given path.",
            func=_file_list,
            parameters={
                "path": {"type": "string", "description": "Directory path to list"},
                "pattern": {"type": "string", "description": "Glob pattern (e.g., '*.py')"},
                "recursive": {"type": "boolean", "description": "List recursively"},
                "max_depth": {"type": "integer", "description": "Max recursion depth"},
            },
            category="file",
            tags=["list", "io", "discovery"],
        ),
        ToolDefinition(
            name="file_delete",
            description="Delete a file. Use with caution!",
            func=_file_delete,
            parameters={
                "path": {"type": "string", "description": "Absolute path to the file to delete"},
                "force": {"type": "boolean", "description": "Force delete without confirmation"},
            },
            category="file",
            requires_confirmation=True,
            tags=["delete", "io", "dangerous"],
        ),
        ToolDefinition(
            name="file_search",
            description="Search for files matching a pattern recursively.",
            func=_file_search,
            parameters={
                "directory": {"type": "string", "description": "Directory to search in"},
                "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"},
                "name_contains": {"type": "string", "description": "Filter: filename contains"},
                "max_results": {"type": "integer", "description": "Max results to return (default: 100)"},
            },
            category="file",
            tags=["search", "io", "discovery"],
        ),
        ToolDefinition(
            name="file_info",
            description="Get detailed information about a file.",
            func=_file_info,
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
            },
            category="file",
            tags=["metadata", "io"],
        ),
        ToolDefinition(
            name="file_move",
            description="Move or rename a file or directory.",
            func=_file_move,
            parameters={
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "description": "Overwrite if destination exists"},
            },
            category="file",
            requires_confirmation=True,
            tags=["move", "rename", "io"],
        ),
        ToolDefinition(
            name="file_copy",
            description="Copy a file to a new location.",
            func=_file_copy,
            parameters={
                "source": {"type": "string", "description": "Source file path"},
                "destination": {"type": "string", "description": "Destination file path"},
            },
            category="file",
            tags=["copy", "io"],
        ),
        ToolDefinition(
            name="file_mkdir",
            description="Create a new directory (and parents if needed).",
            func=_file_mkdir,
            parameters={
                "path": {"type": "string", "description": "Directory path to create"},
                "parents": {"type": "boolean", "description": "Create parent directories (default: true)"},
            },
            category="file",
            tags=["mkdir", "io"],
        ),
    ])


def _file_read(path: str, encoding: str = "utf-8", max_lines: int = None) -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if p.is_dir():
        return {"error": f"Path is a directory: {path}"}

    try:
        with open(p, "r", encoding=encoding) as f:
            lines = f.readlines()
            total_lines = len(lines)
            if max_lines and max_lines > 0:
                lines = lines[:max_lines]
            content = "".join(lines)
            return {
                "path": str(p.absolute()),
                "content": content,
                "total_lines": total_lines,
                "returned_lines": len(lines),
                "size_bytes": p.stat().st_size,
            }
    except UnicodeDecodeError:
        # Try binary read
        return {
            "path": str(p.absolute()),
            "content": f"[Binary file, {p.stat().st_size} bytes]",
            "total_lines": 0,
            "returned_lines": 0,
            "size_bytes": p.stat().st_size,
        }


def _file_write(path: str, content: str, mode: str = "w") -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    write_mode = "w" if mode in ("w", "write", "overwrite") else "a"
    with open(p, write_mode, encoding="utf-8") as f:
        f.write(content)

    return {
        "path": str(p.absolute()),
        "bytes_written": len(content.encode("utf-8")),
        "mode": write_mode,
    }


def _file_list(path: str, pattern: str = "*", recursive: bool = False, max_depth: int = None) -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    if not p.exists():
        return {"error": f"Path not found: {path}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {path}"}

    if recursive:
        glob_pattern = f"**/{pattern}"
        matched = list(p.glob(glob_pattern))
        if max_depth:
            matched = [m for m in matched if len(m.relative_to(p).parts) <= max_depth]
    else:
        matched = list(p.glob(pattern))

    items = []
    for m in matched[:500]:
        try:
            stat = m.stat()
            items.append({
                "name": m.name,
                "path": str(m.absolute()),
                "type": "directory" if m.is_dir() else "file",
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
        except OSError:
            items.append({
                "name": m.name,
                "path": str(m.absolute()),
                "type": "unknown",
                "size_bytes": 0,
                "modified": 0,
            })

    return {"directory": str(p.absolute()), "count": len(items), "items": items}


def _file_delete(path: str, force: bool = False) -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}

    if not force:
        return {"status": "requires_confirmation", "path": str(p.absolute())}

    p.unlink()
    return {"deleted": str(p.absolute())}


def _file_search(directory: str, pattern: str = "**/*", name_contains: str = "", max_results: int = 100) -> Dict[str, Any]:
    directory = os.path.expanduser(directory)
    p = Path(directory)
    if not p.exists():
        return {"error": f"Directory not found: {directory}"}

    results = []
    for file_path in p.glob(pattern):
        if len(results) >= max_results:
            break
        if name_contains and name_contains.lower() not in file_path.name.lower():
            continue
        if file_path.is_file():
            try:
                results.append({
                    "name": file_path.name,
                    "path": str(file_path.absolute()),
                    "size_bytes": file_path.stat().st_size,
                })
            except OSError:
                continue

    return {"directory": str(p.absolute()), "pattern": pattern, "count": len(results), "files": results}


def _file_info(path: str) -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    if not p.exists():
        return {"error": f"Path not found: {path}"}

    stat = p.stat()
    return {
        "name": p.name,
        "path": str(p.absolute()),
        "type": "directory" if p.is_dir() else "file",
        "size_bytes": stat.st_size,
        "created": stat.st_ctime,
        "modified": stat.st_mtime,
        "accessed": stat.st_atime,
        "extension": p.suffix,
        "parent": str(p.parent),
    }


def _file_move(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    source = os.path.expanduser(source)
    destination = os.path.expanduser(destination)
    src = Path(source)
    dst = Path(destination)

    if not src.exists():
        return {"error": f"Source not found: {source}"}
    if dst.exists() and not overwrite:
        return {"error": f"Destination exists: {destination} (use overwrite=true)"}

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"source": str(src.absolute()), "destination": str(dst.absolute()), "moved": True}


def _file_copy(source: str, destination: str) -> Dict[str, Any]:
    source = os.path.expanduser(source)
    destination = os.path.expanduser(destination)
    src = Path(source)
    dst = Path(destination)

    if not src.exists():
        return {"error": f"Source not found: {source}"}

    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.is_file():
        shutil.copy2(str(src), str(dst))
    else:
        shutil.copytree(str(src), str(dst))

    return {"source": str(src.absolute()), "destination": str(dst.absolute()), "copied": True}


def _file_mkdir(path: str, parents: bool = True) -> Dict[str, Any]:
    path = os.path.expanduser(path)
    p = Path(path)
    p.mkdir(parents=parents, exist_ok=True)
    return {"path": str(p.absolute()), "created": True}
