"""EPITA C Coding Style Checker."""

from importlib.metadata import version

__version__ = version("epita-coding-style")

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
