"""Configuration system for EPITA C Coding Style Checker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in, fallback for 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# Rule metadata: (short_description, category)
RULES_META: dict[str, tuple[str, str]] = {
    # File format
    "file.dos": ("No CRLF line endings (use Unix LF)", "File"),
    "file.terminate": ("File must end with a newline", "File"),
    "file.spurious": ("No blank lines at file start/end", "File"),
    "file.trailing": ("No trailing whitespace", "File"),
    "lines.empty": ("No consecutive empty lines", "File"),
    # Braces
    "braces": ("Allman brace style (braces on own line)", "Style"),
    # Functions
    "fun.length": ("Max lines per function body", "Functions"),
    "fun.arg.count": ("Max arguments per function", "Functions"),
    "fun.proto.void": ("Use (void) for functions with no parameters", "Functions"),
    # Exports
    "export.fun": ("Max exported (non-static) functions per file", "Exports"),
    "export.other": ("Max exported global variables per file", "Exports"),
    # Preprocessor
    "cpp.guard": ("Header files must have include guards", "Preprocessor"),
    "cpp.mark": ("# must be in first column", "Preprocessor"),
    "cpp.if": ("#endif should have a comment", "Preprocessor"),
    "cpp.digraphs": ("No digraphs or trigraphs", "Preprocessor"),
    # Declarations & control
    "decl.single": ("One variable declaration per line", "Declarations"),
    "decl.vla": ("No variable-length arrays", "Declarations"),
    "stat.asm": ("No inline assembly", "Declarations"),
    "ctrl.empty": ("Use 'continue' in empty loop bodies", "Control"),
    # Strict
    "keyword.goto": ("No goto statements", "Strict"),
    "cast": ("No explicit casts", "Strict"),
    # Formatting
    "format": ("clang-format compliance check", "Formatting"),
}


@dataclass
class Config:
    """Checker configuration."""

    # Numeric limits
    max_lines: int = 30
    max_args: int = 4
    max_funcs: int = 10
    max_globals: int = 1

    # Rule toggles (all enabled by default for strict EPITA compliance)
    rules: dict[str, bool] = field(default_factory=lambda: {
        # File format
        "file.dos": True,
        "file.terminate": True,
        "file.spurious": True,
        "file.trailing": True,
        "lines.empty": True,
        # Braces
        "braces": True,
        # Functions
        "fun.length": True,
        "fun.arg.count": True,
        "fun.proto.void": True,
        # Exports
        "export.fun": True,
        "export.other": True,
        # Preprocessor
        "cpp.guard": True,
        "cpp.mark": True,
        "cpp.if": True,
        "cpp.digraphs": True,
        # Declarations & control
        "decl.single": True,
        "decl.vla": True,
        "stat.asm": True,
        "ctrl.empty": True,
        # Strict rules (often disabled for specific projects)
        "keyword.goto": True,
        "cast": True,
        # Formatting (uses clang-format)
        "format": True,
    })

    def is_enabled(self, rule: str) -> bool:
        """Check if a rule is enabled."""
        return self.rules.get(rule, True)


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
        elif hasattr(cfg, key):
            setattr(cfg, key, val)
