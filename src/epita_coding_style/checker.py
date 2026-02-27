#!/usr/bin/env python3
"""EPITA C/C++ Coding Style Checker - main entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import urllib.request
from pathlib import Path

from . import __version__
from .config import Config, PRESETS, RULES_META, load_config
from .core import Violation, Severity, parse, parse_cpp, NodeCache, Lang, lang_from_path, ALL_EXTS, CXX_BAD_EXTS
from .checks import (
    check_file_format, check_braces, check_functions, check_exports,
    check_preprocessor, check_misc, check_vla, check_ctrl_empty, check_clang_format,
)
from .checks_cxx import (
    check_cxx_preprocessor, check_cxx_globals, check_cxx_naming,
    check_cxx_declarations, check_cxx_control, check_cxx_writing,
)


def check_file(path: str, cfg: Config) -> list[Violation]:
    """Run all checks on a file, dispatching to C or C++ checks as appropriate."""
    lang = lang_from_path(path)
    if lang is None:
        return []

    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            content = f.read()
    except Exception as e:
        return [Violation(path, 0, "file.read", str(e))]

    lines = content.split('\n')
    content_bytes = content.encode()

    if lang == Lang.CXX:
        return _check_cxx_file(path, cfg, content, lines, content_bytes)
    return _check_c_file(path, cfg, content, lines, content_bytes)


def _check_c_file(path: str, cfg: Config, content: str, lines: list[str],
                  content_bytes: bytes) -> list[Violation]:
    """Run C-specific checks."""
    tree = parse(content_bytes)
    nodes = NodeCache(tree)

    return (
        check_file_format(path, content, lines, cfg) +
        check_braces(path, lines, cfg) +
        check_functions(path, nodes, content_bytes, lines, cfg) +
        check_exports(path, nodes, content_bytes, cfg) +
        check_preprocessor(path, lines, cfg) +
        check_misc(path, nodes, content_bytes, lines, cfg) +
        check_vla(path, nodes, content_bytes, lines, cfg) +
        check_ctrl_empty(path, lines, cfg, nodes=nodes) +
        check_clang_format(path, cfg)
    )


def _check_cxx_file(path: str, cfg: Config, content: str, lines: list[str],
                    content_bytes: bytes) -> list[Violation]:
    """Run C++ specific checks. Automatically enables CXX rules."""
    cxx_cfg = cfg.with_cxx()

    # file.ext: wrong C++ extension
    ext_violations = []
    if cxx_cfg.is_enabled("file.ext") and path.endswith(CXX_BAD_EXTS):
        ext = Path(path).suffix
        ext_map = {'.cpp': '.cc', '.hpp': '.hh'}
        expected = ext_map.get(ext, '.cc')
        ext_violations = [Violation(path, 1, "file.ext",
                                    f"Use '{expected}' extension instead of '{ext}'")]

    tree = parse_cpp(content_bytes)
    nodes = NodeCache(tree)

    return (
        ext_violations +
        check_file_format(path, content, lines, cxx_cfg) +
        check_cxx_preprocessor(path, lines, content_bytes, nodes, cxx_cfg) +
        check_cxx_globals(path, lines, content_bytes, nodes, cxx_cfg) +
        check_cxx_naming(path, lines, content_bytes, nodes, cxx_cfg) +
        check_cxx_declarations(path, lines, content_bytes, nodes, cxx_cfg) +
        check_cxx_control(path, lines, content_bytes, nodes, cxx_cfg) +
        check_cxx_writing(path, lines, content_bytes, nodes, cxx_cfg) +
        check_clang_format(path, cxx_cfg)
    )


def find_files(paths: list[str]) -> list[str]:
    """Find all C and C++ source files."""
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(ALL_EXTS):
            files.append(p)
        elif os.path.isdir(p):
            for root, _, names in os.walk(p):
                files.extend(os.path.join(root, n) for n in names if n.endswith(ALL_EXTS))
    return sorted(files)


CATEGORY_ORDER = ["File", "Style", "Functions", "Exports", "Preprocessor",
                  "Declarations", "Control", "Strict", "Formatting",
                  "CXX-File", "CXX-Preprocessor", "CXX-Global", "CXX-Naming",
                  "CXX-Declarations", "CXX-Control", "CXX-Writing", "Other"]


def _group_rules(cfg: Config) -> dict[str, list[tuple[str, str, bool]]]:
    categories: dict[str, list[tuple[str, str, bool]]] = {}
    for rule in sorted(cfg.rules.keys()):
        desc, cat = RULES_META.get(rule, (rule, "Other"))
        enabled = cfg.rules.get(rule, True)
        categories.setdefault(cat, []).append((rule, desc, enabled))
    return categories


def _print_rules(use_color: bool = True):
    """Print all rules grouped by category with descriptions."""
    BOLD = '\033[1m' if use_color else ''
    DIM = '\033[2m' if use_color else ''
    RST = '\033[0m' if use_color else ''

    categories = _group_rules(Config())
    first = True
    for cat in CATEGORY_ORDER:
        if cat not in categories:
            continue
        if not first:
            print()
        first = False
        print(f"{BOLD}{cat}:{RST}")
        for rule, desc, _ in categories[cat]:
            print(f"  {rule:<20} {DIM}{desc}{RST}")


def _print_config(cfg: Config, use_color: bool = True):
    """Print current effective configuration as valid TOML with comments."""
    defaults = Config()

    DIM = '\033[2m' if use_color else ''
    GREEN = '\033[32m' if use_color else ''
    RED = '\033[31m' if use_color else ''
    CYAN = '\033[36m' if use_color else ''
    RST = '\033[0m' if use_color else ''

    limit_lines = [
        ("max_lines", cfg.max_lines, defaults.max_lines, "Max lines per function body"),
        ("max_args", cfg.max_args, defaults.max_args, "Max arguments per function"),
        ("max_funcs", cfg.max_funcs, defaults.max_funcs, "Max exported functions per file"),
        ("max_globals", cfg.max_globals, defaults.max_globals, "Max exported globals per file"),
    ]

    categories = _group_rules(cfg)

    limit_width = max(len(f"{name} = {val}") for name, val, _, _ in limit_lines)
    rule_width = max(len(f'"{rule}" = {str(en).lower()}') for rules in categories.values() for rule, _, en in rules)
    col = max(limit_width, rule_width) + 2

    print(f"{DIM}# Effective configuration (copy to .epita-style.toml){RST}")
    print()

    print(f"{DIM}# Limits{RST}")
    for name, val, default, desc in limit_lines:
        code = f"{name} = {val}"
        color = CYAN if val != default else ''
        print(f"{color}{code:<{col}}{RST}{DIM}# {desc} (default: {default}){RST}")

    print()
    print(f"{DIM}# Rules: true = enabled, false = disabled{RST}")
    print("[rules]")

    for cat in CATEGORY_ORDER:
        if cat not in categories:
            continue
        print(f"{DIM}# {cat}{RST}")
        for rule, desc, enabled in categories[cat]:
            val_str = "true" if enabled else "false"
            code = f'"{rule}" = {val_str}'
            color = GREEN if enabled else RED
            print(f'{color}{code:<{col}}{RST}{DIM}# {desc}{RST}')


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string like '3.1.1' into a tuple of ints for comparison."""
    try:
        return tuple(int(x) for x in v.strip().split('.'))
    except (ValueError, AttributeError):
        return (0,)


def _check_for_update() -> str | None:
    """Check PyPI for a newer version. Returns a message string or None."""
    try:
        url = "https://pypi.org/pypi/epita-coding-style/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            data = json.loads(resp.read())
        latest = data["info"]["version"]
        if _parse_version(latest) > _parse_version(__version__):
            return (
                f"A new version is available: {__version__} -> {latest}\n"
                f"Update with: pipx upgrade epita-coding-style"
            )
    except Exception:
        pass
    return None


_update_result: str | None = None
_update_done = threading.Event()


def _start_update_check() -> None:
    """Fire-and-forget version check in a daemon thread."""
    def _worker():
        global _update_result
        _update_result = _check_for_update()
        _update_done.set()

    threading.Thread(target=_worker, daemon=True).start()


def _print_update_msg() -> None:
    """Print update message if the background check finished in time."""
    if not _update_done.wait(timeout=1):
        return
    if _update_result:
        C = "\033[36m" if sys.stderr.isatty() else ""
        RST = "\033[0m" if sys.stderr.isatty() else ""
        print(f"{C}{_update_result}{RST}", file=sys.stderr)


def main():
    # Build epilog with config file and preset info
    epilog = """\
Configuration:
  Auto-detected files (in order): .epita-style, .epita-style.toml,
  epita-style.toml, or [tool.epita-coding-style] in pyproject.toml

  Config file format (TOML):
    max_lines = 40
    [rules]
    "keyword.goto" = false

  Priority: CLI flags > config file > preset > defaults

Presets:
  42sh       max_lines=40, disables: goto, cast
  noformat   max_lines=40, disables: goto, cast, format

Exit codes:
  0  No major violations
  1  Major violations found or error
"""

    ap = argparse.ArgumentParser(
        prog='epita-coding-style',
        description='Fast C/C++ linter for EPITA coding style compliance.',
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional
    ap.add_argument('paths', nargs='*', metavar='PATH',
                    help='files or directories to check (recursively finds .c/.h/.cc/.hh/.hxx)')

    # Config options
    cfg_group = ap.add_argument_group('Config')
    cfg_group.add_argument('--preset', choices=list(PRESETS.keys()), metavar='NAME',
                           help='use a preset: 42sh, noformat')
    cfg_group.add_argument('--config', type=Path, metavar='FILE',
                           help='path to TOML config file')

    # Limits
    lim_group = ap.add_argument_group('Limits')
    lim_group.add_argument('--max-lines', type=int, metavar='N',
                           help='max lines per function body [default: 30, C++ auto: 50]')
    lim_group.add_argument('--max-args', type=int, metavar='N',
                           help='max arguments per function [default: 4]')
    lim_group.add_argument('--max-funcs', type=int, metavar='N',
                           help='max exported functions per file [default: 10]')

    # Output
    out_group = ap.add_argument_group('Output')
    out_group.add_argument('-q', '--quiet', action='store_true',
                           help='only show summary')
    out_group.add_argument('--no-color', action='store_true',
                           help='disable colored output')

    # Info
    info_group = ap.add_argument_group('Info')
    info_group.add_argument('--list-rules', action='store_true',
                            help='list all rules with descriptions')
    info_group.add_argument('--show-config', action='store_true',
                            help='show effective configuration and exit')
    info_group.add_argument('-v', '--version', action='store_true',
                            help='show program\'s version number and exit')

    args = ap.parse_args()
    _start_update_check()

    if args.version:
        print(f'epita-coding-style {__version__}')
        _print_update_msg()
        return 0

    # Determine if we should use colors:
    # --no-color flag > NO_COLOR env > FORCE_COLOR env > isatty()
    if args.no_color or os.environ.get('NO_COLOR'):
        use_color = False
    elif os.environ.get('FORCE_COLOR'):
        use_color = True
    else:
        use_color = sys.stdout.isatty()

    if args.list_rules:
        _print_rules(use_color=use_color)
        _print_update_msg()
        return 0

    cfg = load_config(
        config_path=args.config,
        preset=args.preset,
        max_lines=args.max_lines,
        max_args=args.max_args,
        max_funcs=args.max_funcs,
    )

    if args.show_config:
        _print_config(cfg, use_color=use_color)
        _print_update_msg()
        return 0

    if not args.paths:
        ap.error("PATH is required")

    R, Y, W, RST = ('\033[91m', '\033[93m', '\033[97m', '\033[0m') if use_color else ('', '', '', '')

    files = find_files(args.paths)
    if not files:
        print(f"{R}No C/C++ files found{RST}", file=sys.stderr)
        _print_update_msg()
        return 1

    total_major = total_minor = 0
    files_needing_format = []

    for path in files:
        violations = check_file(path, cfg)
        if not violations:
            continue

        has_format = False
        for v in violations:
            if v.severity == Severity.MAJOR:
                total_major += 1
            else:
                total_minor += 1
            if v.rule == "format":
                has_format = True

            if not args.quiet:
                is_major = v.severity == Severity.MAJOR
                color = R if is_major else Y
                col_str = f":{v.column + 1}" if v.column is not None else ":1"
                print(f"{color}{path}:{v.line}{col_str}: {'error' if is_major else 'warning'}: {v.message} [epita-{v.rule}]{RST}")
                if v.line_content is not None:
                    print(f"{v.line_content}")
                    if v.column is not None:
                        print(f"{' ' * v.column}{color}^{RST}")

        if has_format:
            files_needing_format.append(path)

    # Summary
    print(f"\n{W}Files: {len(files)}  Major: {R}{total_major}{RST}  Minor: {Y}{total_minor}{RST}")

    # Show clang-format command if there are files to format
    if files_needing_format:
        print(f"\n{Y}Fix formatting:{RST} clang-format -i {' '.join(files_needing_format)}")

    _print_update_msg()

    return 1 if total_major > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
