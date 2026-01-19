"""Pytest fixtures for coding style checker tests."""

import pytest
from epita_coding_style import check_file, Violation, Severity, Config


@pytest.fixture
def check(tmp_path):
    """Check code string for a specific rule. Returns True if violated."""
    def _check(code: str, rule: str, suffix: str = ".c", preset: str = "42sh") -> bool:
        path = tmp_path / f"test{suffix}"
        if '\r' in code:
            path.write_bytes(code.encode())
        else:
            path.write_text(code)
        # Use 42sh preset by default (40 lines, no goto/cast checks)
        from epita_coding_style import load_config
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
        from epita_coding_style import load_config
        cfg = load_config(preset=preset)
        return check_file(str(path), cfg)
    return _check
