"""Pytest fixtures for coding style checker tests."""

import pytest
from epita_coding_style import check_file, Violation, Severity, Config, load_config


@pytest.fixture
def check(tmp_path):
    """Check code string for a specific rule. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c", preset: str = "42sh") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        cfg = load_config(preset=preset)
        return any(v.rule == rule for v in check_file(str(path), cfg))
    return _check


@pytest.fixture
def check_result(tmp_path):
    """Check code string and return all violations."""
    def _check(code: str, suffix: str = ".c", preset: str = "42sh") -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        cfg = load_config(preset=preset)
        return check_file(str(path), cfg)
    return _check


@pytest.fixture
def check_cxx(tmp_path):
    """Check C++ code string for a specific rule. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".cc") -> bool:
        path = tmp_path / f"test{suffix}"
        path.write_text(code)
        cfg = load_config()
        return any(v.rule == rule for v in check_file(str(path), cfg))
    return _check


@pytest.fixture
def check_cxx_result(tmp_path):
    """Check C++ code string and return all violations for a specific rule."""
    def _check(code: str, rule: str | None = None, suffix: str = ".cc") -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        path.write_text(code)
        cfg = load_config()
        violations = check_file(str(path), cfg)
        if rule is not None:
            return [v for v in violations if v.rule == rule]
        return violations
    return _check
