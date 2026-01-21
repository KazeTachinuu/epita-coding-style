"""EPITA C Coding Style Checker."""

__version__ = "2.2.0"

from .core import Violation, Severity
from .config import Config, load_config, PRESETS
from .checker import check_file, main

__all__ = [
    "check_file",
    "Violation",
    "Severity",
    "main",
    "Config",
    "load_config",
    "PRESETS",
    "__version__",
]
