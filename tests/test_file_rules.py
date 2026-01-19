"""Tests for file-level rules."""

import pytest


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ("int x = 1;   \n", True),
    ("int x = 1;\t\n", True),
])
def test_trailing_whitespace(check, code, should_fail):
    assert check(code, "file.trailing") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ("int x = 1;", True),
])
def test_file_terminate(check, code, should_fail):
    assert check(code, "file.terminate") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\nint y = 2;\n", False),
    ("int x = 1;\r\nint y = 2;\r\n", True),
])
def test_file_dos(check, code, should_fail):
    assert check(code, "file.dos") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ("\nint x = 1;\n", True),
    ("int x = 1;\n\n", True),
])
def test_file_spurious(check, code, should_fail):
    assert check(code, "file.spurious") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int a;\n\nint b;\n", False),
    ("int a;\n\n\nint b;\n", True),
])
def test_lines_empty(check, code, should_fail):
    assert check(code, "lines.empty") == should_fail
