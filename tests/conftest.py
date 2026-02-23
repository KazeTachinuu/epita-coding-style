"""Pytest fixtures for coding style checker tests."""

import pytest
from epita_coding_style import check_file, Violation, Severity, Config, load_config


@pytest.fixture
def check(tmp_path):
    """Check code string for a specific rule. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c", preset: str | None = "42sh") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        cfg = load_config(preset=preset) if preset else load_config()
        return any(v.rule == rule for v in check_file(str(path), cfg))
    return _check


@pytest.fixture
def check_result(tmp_path):
    """Check code string and return violations, optionally filtered by rule."""
    def _check(code: str, rule: str | None = None, suffix: str = ".c",
               preset: str | None = "42sh") -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        cfg = load_config(preset=preset) if preset else load_config()
        violations = check_file(str(path), cfg)
        if rule is not None:
            return [v for v in violations if v.rule == rule]
        return violations
    return _check


@pytest.fixture
def check_cxx(check):
    """Convenience: check C++ code (suffix=.cc, no preset)."""
    def _check(code: str, rule: str, suffix: str = ".cc") -> bool:
        return check(code, rule, suffix=suffix, preset=None)
    return _check


@pytest.fixture
def check_cxx_result(check_result):
    """Convenience: check C++ code and return violations."""
    def _check(code: str, rule: str | None = None, suffix: str = ".cc") -> list[Violation]:
        return check_result(code, rule=rule, suffix=suffix, preset=None)
    return _check


@pytest.fixture
def format_check(tmp_path):
    """Check code for format violations. Returns (has_violation, violations)."""
    def _check(code: str, suffix: str = ".c"):
        path = tmp_path / f"test{suffix}"
        path.write_text(code)
        cfg = Config()
        violations = check_file(str(path), cfg)
        fmt = [v for v in violations if v.rule == "format"]
        return len(fmt) > 0, fmt
    return _check


@pytest.fixture
def format_passes(format_check):
    """Assert code passes format check."""
    def _assert(code: str, suffix: str, msg: str = ""):
        has_violation, _ = format_check(code, suffix)
        assert not has_violation, msg or f"Expected no format violation for {suffix}"
    return _assert


@pytest.fixture
def format_fails(format_check):
    """Assert code fails format check."""
    def _assert(code: str, suffix: str, msg: str = ""):
        has_violation, _ = format_check(code, suffix)
        assert has_violation, msg or f"Expected format violation for {suffix}"
    return _assert
