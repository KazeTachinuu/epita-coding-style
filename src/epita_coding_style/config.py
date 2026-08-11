"""Configuration system for EPITA C/C++ Coding Style Checker."""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in, fallback for 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


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
    "cpp.include.filetype": ("Only include .hh/.hxx files (no source files)", "CXX-Preprocessor", "cxx"),
    "cpp.include.order": ("Includes ordered: same-name header, system, local", "CXX-Preprocessor", "cxx"),
    "cpp.constexpr": ("Compile-time constants should use constexpr", "CXX-Preprocessor", "cxx"),
    "global.casts": ("Must use C++ casts (static_cast etc.), not C-style", "CXX-Global", "cxx"),
    "global.memory.no_malloc": ("No malloc/calloc/realloc/free", "CXX-Global", "cxx"),
    "global.nullptr": ("Use nullptr, not NULL", "CXX-Global", "cxx"),
    "c.extern": ("No extern \"C\"", "CXX-Global", "cxx"),
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
    "exp.padding": ("No space in operator keyword (operator++ not operator ++)", "CXX-Writing", "cxx"),
    "exp.linebreak": ("Line breaks before binary operators", "CXX-Writing", "cxx"),
    "fun.proto.void.cxx": ("MUST NOT use void in C++ empty params", "CXX-Writing", "cxx"),
    "op.assign": ("Return Class& and *this from assignment operators", "CXX-Writing", "cxx"),
    "op.overload": ("Don't overload operator,, operator||, operator&&", "CXX-Writing", "cxx"),
    "op.overload.binand": ("Don't overload operator&", "CXX-Writing", "cxx"),
    "enum.class": ("Prefer enum class over plain enum", "CXX-Writing", "cxx"),
}

RULES_META: dict[str, tuple[str, str]] = {
    name: (desc, cat) for name, (desc, cat, _) in RULES.items()
}
_CXX_RULES = frozenset(n for n, (_, _, lang) in RULES.items() if lang == "cxx")
_C_ONLY_RULES = frozenset(n for n, (_, _, lang) in RULES.items() if lang == "c")


@dataclass
class Config:
    """Checker configuration."""

    max_lines: int = 30
    max_args: int = 4
    max_funcs: int = 10
    max_globals: int = 1

    _user_rules: set[str] = field(default_factory=set)

    rules: dict[str, bool] = field(default_factory=lambda: {
        name: lang != "cxx" for name, (_, _, lang) in RULES.items()
    })

    def is_enabled(self, rule: str) -> bool:
        """Check if a rule is enabled."""
        return self.rules.get(rule, True)

    def with_cxx(self) -> "Config":
        """Return a copy with CXX rules enabled and C-only rules disabled."""
        rules = dict(self.rules)
        for rule in _CXX_RULES - self._user_rules:
            rules[rule] = True
        for rule in _C_ONLY_RULES - self._user_rules:
            rules[rule] = False
        max_lines = 50 if self.max_lines == Config.max_lines else self.max_lines
        return replace(self, rules=rules, max_lines=max_lines,
                       _user_rules=set(self._user_rules))


# Presets (override defaults)
PRESETS: dict[str, dict[str, Any]] = {
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
    """
    Load configuration with priority: CLI overrides > config file > preset > defaults.

    Args:
        config_path: Path to .toml config file
        preset: Preset name ("epita", "42sh")
        **overrides: CLI overrides (max_lines, max_args, etc.)
    """
    cfg = Config()

    # 1. Apply CLI preset first (lowest priority for presets)
    if preset and preset in PRESETS:
        _apply_dict(cfg, PRESETS[preset])

    # 2. Load config file
    file_data: dict[str, Any] | None = None
    if config_path and config_path.exists():
        file_data = _load_toml(config_path)
    else:
        # Auto-detect config files
        for name in (".epita-style", ".epita-style.toml", "epita-style.toml"):
            if Path(name).exists():
                file_data = _load_toml(Path(name))
                break
        else:
            # Check pyproject.toml
            if Path("pyproject.toml").exists():
                data = _load_toml(Path("pyproject.toml"))
                if "tool" in data and "epita-coding-style" in data["tool"]:
                    file_data = data["tool"]["epita-coding-style"]

    # 2b. Apply preset from config file (if no CLI preset), then apply config values
    if file_data:
        file_preset = file_data.get("preset")
        if file_preset and file_preset in PRESETS and not preset:
            _apply_dict(cfg, PRESETS[file_preset])
        _apply_dict(cfg, file_data)

    # 3. Apply CLI overrides
    for key, val in overrides.items():
        if val is not None and hasattr(cfg, key):
            setattr(cfg, key, val)

    return cfg


def _load_toml(path: Path) -> dict[str, Any]:
    """Load TOML file."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def _apply_dict(cfg: Config, data: dict[str, Any]) -> None:
    """Apply dictionary values to config."""
    for key, val in data.items():
        if key == "rules" and isinstance(val, dict):
            cfg.rules.update(val)
            cfg._user_rules.update(val.keys())
        elif hasattr(cfg, key):
            setattr(cfg, key, val)
