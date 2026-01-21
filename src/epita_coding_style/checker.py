#!/usr/bin/env python3
"""EPITA C Coding Style Checker - main entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import Config, PRESETS, RULES_META, load_config
from .core import Violation, Severity, parse, NodeCache
from .checks import (
    check_file_format,
    check_braces,
    check_functions,
    check_exports,
    check_preprocessor,
    check_misc,
    check_clang_format,
)


def check_file(path: str, cfg: Config) -> list[Violation]:
    """Run all checks on a file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            content = f.read()
    except Exception as e:
        return [Violation(path, 0, "file.read", str(e))]

    lines = content.split('\n')
    content_bytes = content.encode()
    tree = parse(content_bytes)
    nodes = NodeCache(tree)

    return (
        check_file_format(path, content, lines, cfg) +
        check_braces(path, lines, cfg) +
        check_functions(path, nodes, content_bytes, lines, cfg) +
        check_exports(path, nodes, content_bytes, cfg) +
        check_preprocessor(path, lines, cfg) +
        check_misc(path, nodes, content_bytes, lines, cfg) +
        check_clang_format(path, cfg)
    )


def find_files(paths: list[str]) -> list[str]:
    """Find all .c and .h files."""
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(('.c', '.h')):
            files.append(p)
        elif os.path.isdir(p):
            for root, _, names in os.walk(p):
                files.extend(os.path.join(root, n) for n in names if n.endswith(('.c', '.h')))
    return sorted(files)


def _print_rules(use_color: bool = True):
    """Print all rules grouped by category with descriptions."""
    cfg = Config()
    categories: dict[str, list[tuple[str, str, bool]]] = {}

    BOLD = '\033[1m' if use_color else ''
    DIM = '\033[2m' if use_color else ''
    RST = '\033[0m' if use_color else ''

    for rule in sorted(cfg.rules.keys()):
        desc, cat = RULES_META.get(rule, (rule, "Other"))
        enabled = cfg.rules.get(rule, True)
        categories.setdefault(cat, []).append((rule, desc, enabled))

    cat_order = ["File", "Style", "Functions", "Exports", "Preprocessor",
                 "Declarations", "Control", "Strict", "Formatting", "Other"]
    first = True
    for cat in cat_order:
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

    # Colors
    DIM = '\033[2m' if use_color else ''
    GREEN = '\033[32m' if use_color else ''
    RED = '\033[31m' if use_color else ''
    CYAN = '\033[36m' if use_color else ''
    RST = '\033[0m' if use_color else ''

    # Build all lines first to calculate alignment
    limit_lines = [
        ("max_lines", cfg.max_lines, defaults.max_lines, "Max lines per function body"),
        ("max_args", cfg.max_args, defaults.max_args, "Max arguments per function"),
        ("max_funcs", cfg.max_funcs, defaults.max_funcs, "Max exported functions per file"),
        ("max_globals", cfg.max_globals, defaults.max_globals, "Max exported globals per file"),
    ]

    # Rules by category
    categories: dict[str, list[tuple[str, str, bool]]] = {}
    for rule in sorted(cfg.rules.keys()):
        desc, cat = RULES_META.get(rule, (rule, "Other"))
        enabled = cfg.rules.get(rule, True)
        categories.setdefault(cat, []).append((rule, desc, enabled))

    # Calculate max widths
    limit_width = max(len(f"{name} = {val}") for name, val, _, _ in limit_lines)
    rule_width = max(len(f'"{rule}" = {str(en).lower()}') for rules in categories.values() for rule, _, en in rules)
    col = max(limit_width, rule_width) + 2

    print(f"{DIM}# Effective configuration (copy to .epita-style.toml){RST}")
    print()

    # Limits
    print(f"{DIM}# Limits{RST}")
    for name, val, default, desc in limit_lines:
        code = f"{name} = {val}"
        color = CYAN if val != default else ''
        print(f"{color}{code:<{col}}{RST}{DIM}# {desc} (default: {default}){RST}")

    print()
    print(f"{DIM}# Rules: true = enabled, false = disabled{RST}")
    print("[rules]")

    for cat in ["File", "Style", "Functions", "Exports", "Preprocessor",
                "Declarations", "Control", "Strict", "Formatting", "Other"]:
        if cat not in categories:
            continue
        print(f"{DIM}# {cat}{RST}")
        for rule, desc, enabled in categories[cat]:
            val_str = "true" if enabled else "false"
            code = f'"{rule}" = {val_str}'
            color = GREEN if enabled else RED
            print(f'{color}{code:<{col}}{RST}{DIM}# {desc}{RST}')


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
        description='Fast C linter for EPITA coding style compliance.',
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional
    ap.add_argument('paths', nargs='*', metavar='PATH',
                    help='files or directories to check (recursively finds .c/.h)')

    # Config options
    cfg_group = ap.add_argument_group('Config')
    cfg_group.add_argument('--preset', choices=list(PRESETS.keys()), metavar='NAME',
                           help='use a preset: 42sh, noformat')
    cfg_group.add_argument('--config', type=Path, metavar='FILE',
                           help='path to TOML config file')

    # Limits
    lim_group = ap.add_argument_group('Limits')
    lim_group.add_argument('--max-lines', type=int, metavar='N',
                           help='max lines per function body [default: 30]')
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
    info_group.add_argument('-v', '--version', action='version',
                            version=f'%(prog)s {__version__}')

    args = ap.parse_args()

    # Determine if we should use colors:
    # --no-color flag > NO_COLOR env > FORCE_COLOR env > isatty()
    if args.no_color or os.environ.get('NO_COLOR'):
        use_color = False
    elif os.environ.get('FORCE_COLOR'):
        use_color = True
    else:
        use_color = sys.stdout.isatty()

    # Info commands (no paths required)
    if args.list_rules:
        _print_rules(use_color=use_color)
        return 0

    if args.show_config:
        cfg = load_config(
            config_path=args.config,
            preset=args.preset,
            max_lines=args.max_lines,
            max_args=args.max_args,
            max_funcs=args.max_funcs,
        )
        _print_config(cfg, use_color=use_color)
        return 0

    # Require paths for checking
    if not args.paths:
        ap.error("PATH is required")

    # Load config
    cfg = load_config(
        config_path=args.config,
        preset=args.preset,
        max_lines=args.max_lines,
        max_args=args.max_args,
        max_funcs=args.max_funcs,
    )

    # Colors
    R, Y, C, W, B, RST = ('\033[91m', '\033[93m', '\033[96m', '\033[97m', '\033[1m', '\033[0m')
    if not use_color:
        R = Y = C = W = B = RST = ''

    files = find_files(args.paths)
    if not files:
        print(f"{R}No C files found{RST}", file=sys.stderr)
        return 1

    total_major = total_minor = 0
    files_needing_format = []

    for path in files:
        violations = check_file(path, cfg)

        major = sum(1 for v in violations if v.severity == Severity.MAJOR)
        minor = sum(1 for v in violations if v.severity == Severity.MINOR)
        total_major += major
        total_minor += minor

        # Track files needing clang-format
        if any(v.rule == "format" for v in violations):
            files_needing_format.append(path)

        if not args.quiet and violations:
            for v in violations:
                color = R if v.severity == Severity.MAJOR else Y
                col_str = f":{v.column + 1}" if v.column is not None else ":1"
                severity_word = "error" if v.severity == Severity.MAJOR else "warning"
                print(f"{color}{path}:{v.line}{col_str}: {severity_word}: {v.message} [epita-{v.rule}]{RST}")
                if v.line_content is not None:
                    print(f"{v.line_content}")
                    if v.column is not None:
                        print(f"{' ' * v.column}{color}^{RST}")

    # Summary
    print(f"\n{W}Files: {len(files)}  Major: {R}{total_major}{RST}  Minor: {Y}{total_minor}{RST}")

    # Show clang-format command if there are files to format
    if files_needing_format:
        print(f"\n{Y}Fix formatting:{RST} clang-format -i {' '.join(files_needing_format)}")

    return 1 if total_major > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
