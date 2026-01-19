"""Configuration system for EPITA C Coding Style Checker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in, fallback for 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


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

    # 1. Apply preset
    if preset and preset in PRESETS:
        _apply_dict(cfg, PRESETS[preset])

    # 2. Load config file
    if config_path and config_path.exists():
        _apply_dict(cfg, _load_toml(config_path))
    else:
        # Auto-detect config files
        for name in (".epita-style.toml", "epita-style.toml"):
            if Path(name).exists():
                _apply_dict(cfg, _load_toml(Path(name)))
                break
        else:
            # Check pyproject.toml
            if Path("pyproject.toml").exists():
                data = _load_toml(Path("pyproject.toml"))
                if "tool" in data and "epita-coding-style" in data["tool"]:
                    _apply_dict(cfg, data["tool"]["epita-coding-style"])

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
