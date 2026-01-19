#!/usr/bin/env python3
"""EPITA C Coding Style Checker - main entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import Config, PRESETS, load_config
from .core import Violation, Severity, parse
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

    return (
        check_file_format(path, content, lines, cfg) +
        check_braces(path, lines, cfg) +
        check_functions(path, tree, content_bytes, lines, cfg) +
        check_exports(path, tree, content_bytes, cfg) +
        check_preprocessor(path, lines, cfg) +
        check_misc(path, tree, content_bytes, lines, cfg) +
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


def main():
    ap = argparse.ArgumentParser(
        description='EPITA C Coding Style Checker',
        epilog='Exit code: 0 if no major violations, 1 otherwise.'
    )
    ap.add_argument('paths', nargs='*', metavar='PATH',
                    help='C files or directories to check')
    ap.add_argument('--preset', choices=list(PRESETS.keys()), metavar='NAME',
                    help=f"use preset config ({', '.join(PRESETS.keys())})")
    ap.add_argument('--config', type=Path, metavar='FILE',
                    help='path to .toml config file')
    ap.add_argument('--max-lines', type=int, metavar='N',
                    help='max lines per function body')
    ap.add_argument('--max-args', type=int, metavar='N',
                    help='max arguments per function')
    ap.add_argument('--max-funcs', type=int, metavar='N',
                    help='max exported functions per file')
    ap.add_argument('-q', '--quiet', action='store_true',
                    help='only show summary')
    ap.add_argument('--no-color', action='store_true',
                    help='disable colored output')
    ap.add_argument('--list-rules', action='store_true',
                    help='list all rules and exit')
    args = ap.parse_args()

    # List rules and exit
    if args.list_rules:
        cfg = Config()
        print("Available rules:")
        for rule in sorted(cfg.rules.keys()):
            print(f"  {rule}")
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
    if args.no_color:
        R = Y = C = W = B = RST = ''

    files = find_files(args.paths)
    if not files:
        print(f"{R}No C files found{RST}", file=sys.stderr)
        return 1

    total_major = total_minor = 0

    for path in files:
        violations = check_file(path, cfg)

        major = sum(1 for v in violations if v.severity == Severity.MAJOR)
        minor = sum(1 for v in violations if v.severity == Severity.MINOR)
        total_major += major
        total_minor += minor

        if not args.quiet and violations:
            print(f"\n{W}{B}{path}{RST}")
            for v in violations:
                color = R if v.severity == Severity.MAJOR else Y
                print(f"  {C}{v.line}{RST}: {color}[{v.severity.value}]{RST} {v.rule}: {v.message}")

    # Summary
    print(f"\n{W}Files: {len(files)}  Major: {R}{total_major}{RST}  Minor: {Y}{total_minor}{RST}")

    return 1 if total_major > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
