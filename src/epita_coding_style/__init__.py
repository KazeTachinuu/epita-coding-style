"""EPITA C/C++ Coding Style Checker."""

from importlib.metadata import version

# Defined before the submodule imports: cli and update import it from here.
__version__ = version("epita-coding-style")

from .cli import main
from .config import PRESETS, RULES, Config, ConfigError, load_config
from .lint import check_file
from .model import Lang, Severity, Violation, lang_from_path

__all__ = [
    "PRESETS",
    "RULES",
    "Config",
    "ConfigError",
    "Lang",
    "Severity",
    "Violation",
    "__version__",
    "check_file",
    "lang_from_path",
    "load_config",
    "main",
]
