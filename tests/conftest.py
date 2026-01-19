"""Pytest fixtures for coding style checker tests."""

import pytest
from pathlib import Path

from epita_coding_style import check_file, Violation, Severity

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def check(tmp_path):
    """Check code string for a rule violation. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        violations = check_file(str(path))
        return any(v.rule == rule for v in violations)
    return _check


@pytest.fixture
def check_result(tmp_path):
    """Check code string and return violations list."""
    def _check(code: str, suffix: str = ".c") -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        return check_file(str(path))
    return _check


@pytest.fixture
def check_fixture():
    """Check a fixture file for a rule violation."""
    def _check(filename: str, rule: str) -> bool:
        path = FIXTURES_DIR / filename
        violations = check_file(str(path))
        return any(v.rule == rule for v in violations)
    return _check
