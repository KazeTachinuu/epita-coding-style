"""Pytest fixtures for coding style checker tests."""

import io
import sys
from typing import NamedTuple

import pytest

from epita_coding_style import Violation, check_file, load_config, main


class CliResult(NamedTuple):
    code: int
    out: str
    err: str


@pytest.fixture(autouse=True)
def _hermetic_cwd(tmp_path, monkeypatch):
    """Run in tmp_path so config auto-detection never sees repo files."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def cli(monkeypatch, capsys):
    """Run the CLI in-process with args (and optional stdin): returns code/out/err."""
    def _run(*args: str, stdin: str = "") -> CliResult:
        monkeypatch.setattr(sys, "argv", ["epita-coding-style", *args])
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main()
        except SystemExit as e:
            code = e.code
        out, err = capsys.readouterr()
        return CliResult(code, out, err)
    return _run


@pytest.fixture
def lint(tmp_path):
    """Lint a code string as tmp_path/test<suffix>: returns its violations."""
    def _lint(code: str, suffix: str = ".c", preset: str | None = None) -> list[Violation]:
        path = tmp_path / f"test{suffix}"
        path.write_bytes(code.encode())
        return check_file(str(path), load_config(preset=preset))
    return _lint


@pytest.fixture
def rules(lint):
    """Lint a code string: returns the names of the rules it violates."""
    def _rules(code: str, suffix: str = ".c", preset: str | None = None) -> set[str]:
        return {v.rule for v in lint(code, suffix, preset)}
    return _rules
