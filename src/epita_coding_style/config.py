"""Rules, presets, and configuration loading."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Single source of truth: rule -> (description, category, lang).
# lang: "c" = C only (disabled for C++), "cxx" = C++ only (enabled by
# with_cxx), "both" = language-independent. Default enabled unless "cxx".
RULES: dict[str, tuple[str, str, str]] = {
    "file.dos": ("No CRLF line endings (use Unix LF)", "File", "both"),
    "file.terminate": ("File must end with a newline", "File", "both"),
    "file.spurious": ("No blank lines at file start/end", "File", "both"),
    "file.trailing": ("No trailing whitespace", "File", "both"),
    "lines.empty": ("No consecutive empty lines", "File", "both"),
    "braces": ("Allman brace style (braces on own line)", "Style", "both"),
    "fun.length": ("Max lines per function body", "Functions", "both"),
    "fun.arg.count": ("Max arguments per function", "Functions", "both"),
    "fun.proto.void": ("Use (void) for functions with no parameters", "Functions", "c"),
    "export.fun": ("Max exported (non-static) functions per file", "Exports", "c"),
    "export.other": ("Max exported global variables per file", "Exports", "c"),
    "cpp.guard": ("Header files must have include guards", "Preprocessor", "c"),
    "cpp.mark": ("# must be in first column", "Preprocessor", "both"),
    "cpp.if": ("#endif should have a comment", "Preprocessor", "both"),
    "cpp.digraphs": ("No digraphs or trigraphs", "Preprocessor", "both"),
    "comment.multi": ("Multi-line comment lines start with '**'", "Preprocessor", "c"),
    "decl.single": ("One variable declaration per line", "Declarations", "both"),
    "decl.vla": ("No variable-length arrays", "Declarations", "both"),
    "stat.asm": ("No inline assembly", "Declarations", "both"),
    "stat.sep": ("No comma operator outside 'for'", "Declarations", "c"),
    "ctrl.empty": ("Use 'continue' in empty loop bodies", "Control", "both"),
    "keyword.goto": ("No goto statements", "Strict", "c"),
    "cast": ("No explicit casts", "Strict", "c"),
    "format": ("clang-format compliance check", "Formatting", "both"),
    "file.ext": ("C++ files must use .cc/.hh/.hxx extensions (not .cpp/.hpp)", "CXX-File", "cxx"),
    "cpp.pragma.once": ("Use #pragma once instead of include guards", "CXX-Preprocessor", "cxx"),
    "cpp.include.filetype": (
        "Only include .hh/.hxx files (no source files)",
        "CXX-Preprocessor",
        "cxx",
    ),
    "cpp.include.order": (
        "Includes ordered: same-name header, system, local",
        "CXX-Preprocessor",
        "cxx",
    ),
    "cpp.constexpr": ("Compile-time constants should use constexpr", "CXX-Preprocessor", "cxx"),
    "global.casts": ("Must use C++ casts (static_cast etc.), not C-style", "CXX-Global", "cxx"),
    "global.memory.no_malloc": ("No malloc/calloc/realloc/free", "CXX-Global", "cxx"),
    "global.nullptr": ("Use nullptr, not NULL", "CXX-Global", "cxx"),
    "c.extern": ('No extern "C"', "CXX-Global", "cxx"),
    "c.headers": ("No C headers (use <cstdio> not <stdio.h>)", "CXX-Global", "cxx"),
    "c.std_functions": ("Use std:: equivalents", "CXX-Global", "cxx"),
    "naming.class": ("CamelCase class/struct names", "CXX-Naming", "cxx"),
    "naming.namespace": ("Lowercase namespaces, closing comment", "CXX-Naming", "cxx"),
    "decl.ref": ("& next to type, not variable", "CXX-Declarations", "cxx"),
    "decl.ctor.explicit": ("Single-arg constructors should be explicit", "CXX-Declarations", "cxx"),
    "decl.point": ("* next to type, not variable", "CXX-Declarations", "cxx"),
    "ctrl.switch": ("Default case rules for switch", "CXX-Control", "cxx"),
    "ctrl.switch.padding": ("No space before label colon", "CXX-Control", "cxx"),
    "braces.empty": ("{} on same line for empty bodies", "CXX-Writing", "cxx"),
    "braces.single_exp": ("Prefer braces for single-expression blocks", "CXX-Writing", "cxx"),
    "err.throw": ("Don't throw literals", "CXX-Writing", "cxx"),
    "err.throw.catch": ("Catch by reference", "CXX-Writing", "cxx"),
    "err.throw.paren": ("No parentheses after throw", "CXX-Writing", "cxx"),
    "exp.padding": (
        "No space in operator keyword (operator++ not operator ++)",
        "CXX-Writing",
        "cxx",
    ),
    "exp.linebreak": ("Line breaks before binary operators", "CXX-Writing", "cxx"),
    "fun.proto.void.cxx": ("MUST NOT use void in C++ empty params", "CXX-Writing", "cxx"),
    "op.assign": ("Return Class& and *this from assignment operators", "CXX-Writing", "cxx"),
    "op.overload": ("Don't overload operator,, operator||, operator&&", "CXX-Writing", "cxx"),
    "op.overload.binand": ("Don't overload operator&", "CXX-Writing", "cxx"),
    "enum.class": ("Prefer enum class over plain enum", "CXX-Writing", "cxx"),
}

LIMITS: dict[str, str] = {
    "max_lines": "Max lines per function body (C++ default: 50)",
    "max_args": "Max arguments per function",
    "max_funcs": "Max exported functions per file",
    "max_globals": "Max exported globals per file",
    "max_casts": "Max explicit casts across all checked C files",
}

_CXX_RULES = frozenset(n for n, (_, _, lang) in RULES.items() if lang == "cxx")
_C_ONLY_RULES = frozenset(n for n, (_, _, lang) in RULES.items() if lang == "c")


class ConfigError(Exception):
    """Invalid configuration; message is user-facing."""


@dataclass
class Config:
    """Checker configuration."""

    max_lines: int = 30
    max_args: int = 4
    max_funcs: int = 10
    max_globals: int = 1
    max_casts: int = 0

    user_rules: set[str] = field(default_factory=set)
    user_limits: set[str] = field(default_factory=set)

    rules: dict[str, bool] = field(
        default_factory=lambda: {name: lang != "cxx" for name, (_, _, lang) in RULES.items()}
    )

    def is_enabled(self, rule: str) -> bool:
        return self.rules.get(rule, True)

    def with_cxx(self) -> Config:
        """Return a copy with CXX rules enabled and C-only rules disabled."""
        rules = dict(self.rules)
        for rule in _CXX_RULES - self.user_rules:
            rules[rule] = True
        for rule in _C_ONLY_RULES - self.user_rules:
            rules[rule] = False
        max_lines = self.max_lines if "max_lines" in self.user_limits else 50
        return replace(
            self,
            rules=rules,
            max_lines=max_lines,
            user_rules=set(self.user_rules),
            user_limits=set(self.user_limits),
        )


# Presets (override defaults)
PRESETS: dict[str, dict[str, Any]] = {
    "ppex1": {
        "max_casts": 5,
    },
    "42sh": {
        "max_lines": 40,
        "rules": {
            "keyword.goto": False,
            "cast": False,
        },
    },
    "noformat": {
        "max_lines": 40,
        "rules": {
            "keyword.goto": False,
            "cast": False,
            "format": False,
        },
    },
}


def load_config(
    config_path: Path | None = None,
    preset: str | None = None,
    **overrides: Any,
) -> Config:
    """Build a Config: CLI overrides > config file > preset > defaults."""
    cfg = Config()
    file_data, source = _find_config(config_path)
    if preset:
        _apply_dict(cfg, _preset(preset, "preset"), f"preset '{preset}'")
    elif "preset" in file_data:
        _apply_dict(cfg, _preset(file_data["preset"], source), source)
    _apply_dict(cfg, file_data, source)
    _apply_dict(cfg, {k: v for k, v in overrides.items() if v is not None}, "override")
    return cfg


def _find_config(config_path: Path | None) -> tuple[dict[str, Any], str]:
    """The explicit config file, or the first one found walking up from cwd."""
    if config_path:
        if not config_path.exists():
            raise ConfigError(f"config file not found: {config_path}")
        return _load_toml(config_path), str(config_path)
    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        for name in (".epita-style", ".epita-style.toml", "epita-style.toml"):
            if (p := directory / name).is_file():
                return _load_toml(p), str(p)
        if (p := directory / "pyproject.toml").is_file():
            tool = _load_toml(p).get("tool", {})
            if "epita-coding-style" in tool:
                return tool["epita-coding-style"], str(p)
    return {}, ""


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, raising ConfigError if it cannot be read or parsed."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: invalid TOML: {e}") from e
    except OSError as e:
        raise ConfigError(f"{path}: cannot read: {e.strerror or e}") from e


def _preset(name: Any, source: str) -> dict[str, Any]:
    if name not in PRESETS:
        raise ConfigError(f"{source}: unknown preset '{name}' (choose from: {', '.join(PRESETS)})")
    return PRESETS[name]


def _apply_dict(cfg: Config, data: dict[str, Any], source: str) -> None:
    """Apply validated config values; reject unknown keys and bad types."""
    for key, val in data.items():
        if key == "preset":
            _preset(val, source)  # applied first by load_config
        elif key == "rules":
            if not isinstance(val, dict):
                raise ConfigError(f"{source}: [rules] must be a table")
            for rule, enabled in val.items():
                if rule not in RULES:
                    raise ConfigError(f"{source}: unknown rule '{rule}' (see --list-rules)")
                if not isinstance(enabled, bool):
                    raise ConfigError(f"{source}: rule '{rule}' must be true or false")
            cfg.rules.update(val)
            cfg.user_rules.update(val.keys())
        elif key in LIMITS:
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ConfigError(f"{source}: {key} must be a non-negative integer")
            setattr(cfg, key, val)
            cfg.user_limits.add(key)
        else:
            raise ConfigError(f"{source}: unknown key '{key}'")
