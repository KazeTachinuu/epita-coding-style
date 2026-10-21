"""Find the C and C++ sources to check."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .model import lang_from_path


def _git(directory: str, *args: str, check: bool = False) -> subprocess.CompletedProcess[bytes]:
    # The scanned repo may be untrusted: its .git/config could set core.fsmonitor
    # to a command that git runs even for read-only commands like ls-files.
    return subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", directory, *args],
        capture_output=True,
        check=check,
    )


def _git_files(directory: str) -> list[str] | None:
    """Paths git does not ignore, relative to directory.

    None outside a repo, or when directory itself is ignored (named explicitly).
    """
    try:
        if _git(directory, "check-ignore", "-q", ".").returncode == 0:
            return None
        out = _git(
            directory, "ls-files", "-z", "--cached", "--others", "--exclude-standard", check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    # an empty submodule lists itself as './'
    return [f for f in os.fsdecode(out).split("\0") if os.path.normpath(f) != "."]


def _walk_dir(directory: str) -> list[str]:
    """Source files under directory, skipping hidden and git-ignored paths.

    Same defaults as ripgrep/fd: .gitignore, .git/info/exclude and the global
    excludes file apply inside a git repo; hidden files are skipped everywhere.
    """
    files = _git_files(directory)
    if files is None:
        files = []
        for root, dirs, names in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files += [os.path.relpath(os.path.join(root, n), directory) for n in names]
    found = []
    for f in files:
        if any(p.startswith(".") for p in Path(f).parts):
            continue
        full = os.path.join(directory, f)
        # git lists a nested repo or submodule as a single directory entry
        if os.path.isdir(full) and not os.path.islink(full):
            found += _walk_dir(full)
        # isfile: git also lists tracked files deleted from the worktree
        elif lang_from_path(f) and os.path.isfile(full):
            found.append(full)
    return found


def find_files(paths: list[str]) -> list[str]:
    """Find all C and C++ source files. Raises FileNotFoundError for bad paths."""
    files = []
    for p in paths:
        if os.path.isfile(p):
            if lang_from_path(p):
                files.append(p)
            else:
                print(f"epita-coding-style: skipping '{p}': unsupported extension", file=sys.stderr)
        elif os.path.isdir(p):
            files.extend(_walk_dir(p))
        else:
            raise FileNotFoundError(p)
    unique: dict[str, str] = {}
    for f in files:
        unique.setdefault(os.path.abspath(f), os.path.normpath(f))
    return sorted(unique.values())
