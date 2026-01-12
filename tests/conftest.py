"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from check import CodingStyleChecker

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def checker():
    """Default checker instance."""
    return CodingStyleChecker(max_func_lines=40, max_func_args=4, max_exported_funcs=10)


@pytest.fixture
def check(checker, tmp_path):
    """Check code string for a rule violation. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        result = checker.check_file(str(path))
        return any(v.rule == rule for v in result.violations)
    return _check


@pytest.fixture
def check_result(checker, tmp_path):
    """Check code string and return full result."""
    def _check(code: str, suffix: str = ".c"):
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        return checker.check_file(str(path))
    return _check


@pytest.fixture
def check_fixture(checker):
    """Check a fixture file for a rule violation."""
    def _check(filename: str, rule: str) -> bool:
        path = FIXTURES_DIR / filename
        result = checker.check_file(str(path))
        return any(v.rule == rule for v in result.violations)
    return _check
