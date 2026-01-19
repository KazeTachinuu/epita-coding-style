"""EPITA C Coding Style Checker."""

__version__ = "2.0.1"

from .checker import check_file, Violation, Severity, main

__all__ = ["check_file", "Violation", "Severity", "main", "__version__"]
