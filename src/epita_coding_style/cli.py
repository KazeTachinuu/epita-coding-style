"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path
from typing import NamedTuple

from . import __version__
from .checks.clang_format import clang_format_active, clang_format_config
from .config import LIMITS, PRESETS, RULES, Config, ConfigError, load_config
from .files import find_files
from .lint import lint_files
from .model import Severity, Violation
from .update import print_update_msg, start_update_check

_EPILOG = """\
Configuration:
  Auto-detected files (in order): .epita-style, .epita-style.toml,
  epita-style.toml, or [tool.epita-coding-style] in pyproject.toml

  Config file format (TOML):
    max_lines = 40
    [rules]
    "keyword.goto" = false

  Priority: CLI flags > config file > preset > defaults

Presets:
  ppex1      max_casts=5
  42sh       max_lines=40, disables: goto, cast
  noformat   max_lines=40, disables: goto, cast, format

Environment:
  NO_COLOR / FORCE_COLOR         override color autodetection
  EPITA_STYLE_NO_UPDATE_CHECK    disable the daily PyPI version check
                                 (only runs in a terminal, never in CI)

Exit codes:
  0  No major violations
  1  Major violations found
  2  Usage, config, or file error
"""


class Colors(NamedTuple):
    bold: str = ""
    dim: str = ""
    red: str = ""
    yellow: str = ""
    white: str = ""
    cyan: str = ""
    reset: str = ""


_ANSI = Colors("\033[1m", "\033[2m", "\033[91m", "\033[93m", "\033[97m", "\033[36m", "\033[0m")


def _count(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="epita-coding-style",
        description="Fast C/C++ linter for EPITA coding style compliance.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="files or directories to check (recursively finds "
        ".c/.h/.cc/.hh/.hxx, honoring .gitignore); "
        "'-' reads paths from stdin",
    )

    g = ap.add_argument_group("Config")
    g.add_argument(
        "--preset",
        choices=list(PRESETS),
        metavar="NAME",
        help=f"use a preset: {', '.join(PRESETS)}",
    )
    g.add_argument("--config", type=Path, metavar="FILE", help="path to TOML config file")

    g = ap.add_argument_group("Limits")
    defaults = Config()
    for name, desc in LIMITS.items():
        g.add_argument(
            "--" + name.replace("_", "-"),
            type=_count,
            metavar="N",
            help=f"{desc} [default: {getattr(defaults, name)}]",
        )

    g = ap.add_argument_group("Output")
    g.add_argument("-q", "--quiet", action="store_true", help="only show summary")
    g.add_argument("--no-color", action="store_true", help="disable colored output")

    g = ap.add_argument_group("Info")
    g.add_argument("--list-rules", action="store_true", help="list all rules with descriptions")
    g.add_argument(
        "--show-config", action="store_true", help="show effective configuration and exit"
    )
    g.add_argument("-v", "--version", action="version", version=f"epita-coding-style {__version__}")
    return ap


def _colors(*, no_color: bool) -> Colors:
    """--no-color > NO_COLOR > FORCE_COLOR > stdout is a terminal."""
    if no_color or os.environ.get("NO_COLOR"):
        return Colors()
    if os.environ.get("FORCE_COLOR") or sys.stdout.isatty():
        return _ANSI
    return Colors()


def _rules_by_category() -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    for rule, (_, cat, _) in RULES.items():
        categories.setdefault(cat, []).append(rule)
    return categories


def _print_rules(c: Colors) -> None:
    for i, (cat, rules) in enumerate(_rules_by_category().items()):
        if i:
            print()
        print(f"{c.bold}{cat}:{c.reset}")
        for rule in rules:
            print(f"  {rule:<24} {c.dim}{RULES[rule][0]}{c.reset}")


def _print_config(cfg: Config, c: Colors) -> None:
    """Print cfg as loadable TOML: explicit settings, defaults commented out."""
    defaults = Config()

    def line(code: str, comment: str, *, is_set: bool) -> None:
        code = code if is_set else f"# {code}"
        print(f"{c.cyan if is_set else c.dim}{code:<38}{c.reset}{c.dim}# {comment}{c.reset}")

    print(f"{c.dim}# Copy to .epita-style.toml; uncomment a line to change it{c.reset}")
    for name, desc in LIMITS.items():
        is_set = name in cfg.user_limits
        line(f"{name} = {getattr(cfg if is_set else defaults, name)}", desc, is_set=is_set)

    print("\n[rules]")
    for cat, rules in _rules_by_category().items():
        print(f"{c.dim}# {cat}{c.reset}")
        for rule in rules:
            is_set = rule in cfg.user_rules
            enabled = cfg.rules[rule] if is_set else True
            line(f'"{rule}" = {str(enabled).lower()}', RULES[rule][0], is_set=is_set)


def _render(v: Violation, c: Colors) -> str:
    """gcc-style diagnostic, with the source line and a caret when known."""
    major = v.severity == Severity.MAJOR
    color = c.red if major else c.yellow
    out = (
        f"{color}{v.file}:{v.line}:{(v.column or 0) + 1}: "
        f"{'error' if major else 'warning'}: {v.message} [epita-{v.rule}]{c.reset}"
    )
    if v.line_content and v.line_content.strip():
        out += f"\n{v.line_content}"
        if v.column is not None:
            out += f"\n{' ' * v.column}{color}^{c.reset}"
    return out


def _print_fix_hint(results: dict[str, list[Violation]], c: Colors) -> None:
    """Print the clang-format commands that fix the files needing formatting."""
    by_config: dict[str, list[str]] = {}
    for path, violations in results.items():
        if any(
            v.rule == "format" and not v.message.startswith("clang-format failed")
            for v in violations
        ):
            by_config.setdefault(clang_format_config(path), []).append(path)
    if by_config:
        print(f"\n{c.yellow}Fix formatting:{c.reset}")
        for config, paths in by_config.items():
            print("  " + shlex.join(["clang-format", f"--style=file:{config}", "-i", *paths]))


def main() -> int:
    ap = _parser()
    args = ap.parse_args()
    start_update_check()
    c = _colors(no_color=args.no_color)

    if args.list_rules:
        _print_rules(c)
        print_update_msg()
        return 0

    try:
        cfg = load_config(
            config_path=args.config,
            preset=args.preset,
            **{name: getattr(args, name) for name in LIMITS},
        )
    except ConfigError as e:
        print(f"epita-coding-style: error: {e}", file=sys.stderr)
        return 2

    if args.show_config:
        _print_config(cfg, c)
        print_update_msg()
        return 0

    if not args.paths:
        ap.error("PATH is required")
    paths = [p for p in args.paths if p != "-"]
    if "-" in args.paths:
        paths += [line.strip() for line in sys.stdin if line.strip()]

    try:
        files = find_files(paths)
    except FileNotFoundError as e:
        print(f"epita-coding-style: error: {e.args[0]}: no such file or directory", file=sys.stderr)
        return 2
    if not files:
        print(f"{c.red}epita-coding-style: error: no C/C++ files found{c.reset}", file=sys.stderr)
        print_update_msg()
        return 2

    if cfg.is_enabled("format") and not clang_format_active(cfg):
        print(
            "epita-coding-style: warning: clang-format not found, format check skipped",
            file=sys.stderr,
        )
    results = lint_files(files, cfg)

    major = minor = 0
    for violations in results.values():
        for v in violations:
            if v.severity == Severity.MAJOR:
                major += 1
            else:
                minor += 1
            if not args.quiet:
                print(_render(v, c))

    print(
        f"\n{c.white}Files: {len(files)}  Major: {c.red}{major}{c.reset}  "
        f"Minor: {c.yellow}{minor}{c.reset}"
    )
    if not args.quiet:
        _print_fix_hint(results, c)

    print_update_msg()
    return 1 if major else 0
