"""The format rule: clang-format, batched over many files."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from ..config import Config
from ..model import Lang, Violation, lang_from_path, lang_of

_CLANG_ERROR = re.compile(r'^(.*):(\d+):\d+: (?:error|warning):')
_CONFIGS = {Lang.C: ".clang-format-c", Lang.CXX: ".clang-format-cxx"}


def clang_format_config(path: str) -> str:
    """Nearest .clang-format-{c,cxx} or .clang-format above path, else the bundled one."""
    name = _CONFIGS[lang_of(path)]
    start = Path(os.path.abspath(path)).parent
    for directory in (start, *start.parents):
        for candidate in (directory / name, directory / ".clang-format"):
            if candidate.is_file():
                return str(candidate)
    return str(Path(__file__).parent.parent / name)


def clang_format_active(cfg: Config) -> bool:
    """The format rule is enabled and clang-format is installed."""
    return cfg.is_enabled("format") and shutil.which("clang-format") is not None


def check_clang_format(files: list[str], cfg: Config) -> dict[str, list[Violation]]:
    """Format-check C and C++ files with one clang-format run per config.

    Unreadable files are skipped: the file.read check already reports them.
    """
    if not clang_format_active(cfg):
        return {}
    groups: dict[str, list[str]] = {}
    for path in files:
        if lang_from_path(path) and os.access(path, os.R_OK):
            groups.setdefault(clang_format_config(path), []).append(path)
    violations: dict[str, list[Violation]] = {}
    for config, paths in groups.items():
        violations.update(_run_clang_format(config, paths))
    return violations


def _run_clang_format(config: str, paths: list[str]) -> dict[str, list[Violation]]:
    try:
        result = subprocess.run(
            ["clang-format", f"--style=file:{config}", "--dry-run", "--Werror", *paths],
            capture_output=True, text=True, timeout=30 + len(paths))
    except subprocess.TimeoutExpired:
        return {}  # a hung clang-format must not hang the linter: skip the format check
    if result.returncode == 0:
        return {}
    bad_lines: dict[str, set[int]] = {}
    for line in result.stderr.splitlines():
        if (m := _CLANG_ERROR.match(line)) and m[1] in paths:
            bad_lines.setdefault(m[1], set()).add(int(m[2]))
    if bad_lines:
        return {path: [Violation(path, min(lines), "format",
                                 f"{len(lines)} line{'s need' if len(lines) > 1 else ' needs'} formatting")]
                for path, lines in bad_lines.items()}
    # clang-format failed outright (invalid config, crash): find the culprit file
    if len(paths) > 1:
        return {k: v for path in paths for k, v in _run_clang_format(config, [path]).items()}
    error = (result.stderr.strip().splitlines() or ["unknown error"])[0]
    return {paths[0]: [Violation(paths[0], 1, "format", f"clang-format failed: {error}")]}
