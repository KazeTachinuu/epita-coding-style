"""Pytest fixtures for coding style checker tests."""

import pytest
from epita_coding_style import check_file, Violation, Severity


@pytest.fixture
def check(tmp_path):
    """Check code string for a specific rule. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        return any(v.rule == rule for v in check_file(str(path)))
    return _check


@pytest.fixture
def check_result(tmp_path):
    """Check code string and return all violations."""
    def _check(code: str, suffix: str = ".c") -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        return check_file(str(path))
    return _check
