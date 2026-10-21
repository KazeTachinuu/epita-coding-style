"""Run the checks on files."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .checks import c, common, cxx
from .checks.clang_format import check_clang_format
from .config import Config
from .model import Lang, Source, Violation, lang_from_path

Check = Callable[[Source, Config], list[Violation]]

C_CHECKS: tuple[Check, ...] = (*common.CHECKS, *c.CHECKS)
# file.ext reports at line 1, ahead of everything else
CXX_CHECKS: tuple[Check, ...] = (cxx.check_file_ext, *common.CHECKS, *cxx.CHECKS)


def check_file(path: str, cfg: Config) -> list[Violation]:
    """Run all checks, including clang-format, on one C or C++ file."""
    return lint_files([path], cfg)[path]


def lint_files(files: list[str], cfg: Config) -> dict[str, list[Violation]]:
    """Run all checks on files; violations per file, sorted by position.

    clang-format runs once per config, and max_casts is a budget shared by all files.
    """
    formatting = check_clang_format(files, cfg)
    results = {path: _lint(path, cfg) + formatting.get(path, []) for path in files}
    _apply_cast_budget(results, cfg.max_casts)
    for violations in results.values():
        violations.sort(key=lambda v: (v.line, v.column or 0))
    return results


def _lint(path: str, cfg: Config) -> list[Violation]:
    """Violations of enabled rules: checks report everything, rule toggles apply here."""
    if lang_from_path(path) is None:
        return []
    try:
        src = Source.read(path)
    except OSError as e:
        return [Violation(path, 1, "file.read", f"Cannot read file: {e.strerror or e}")]
    checks = C_CHECKS
    if src.lang == Lang.CXX:
        cfg, checks = cfg.with_cxx(), CXX_CHECKS
    return [v for check in checks for v in check(src, cfg) if cfg.is_enabled(v.rule)]


def _apply_cast_budget(results: dict[str, list[Violation]], budget: int) -> None:
    """Drop cast violations if all files together stay within budget, else show the total."""
    if not budget:
        return
    total = sum(v.rule == "cast" for vs in results.values() for v in vs)
    for path, vs in results.items():
        if total <= budget:
            results[path] = [v for v in vs if v.rule != "cast"]
        else:
            message = f"Explicit cast ({total} in total, max {budget})"
            results[path] = [replace(v, message=message) if v.rule == "cast" else v for v in vs]
