"""Tests for file-level rules."""

import pytest


@pytest.mark.parametrize(
    "code,should_fail",
    [
        ("int x = 1;\n", False),
        ("int x = 1;   \n", True),
        ("int x = 1;\t\n", True),
    ],
    ids=["clean", "trailing-spaces", "trailing-tab"],
)
def test_trailing_whitespace(rules, code, should_fail):
    assert ("file.trailing" in rules(code)) == should_fail


@pytest.mark.parametrize(
    "code,should_fail",
    [
        ("int x = 1;\n", False),
        ("int x = 1;", True),
    ],
    ids=["newline", "no-newline"],
)
def test_file_terminate(rules, code, should_fail):
    assert ("file.terminate" in rules(code)) == should_fail


@pytest.mark.parametrize(
    "code,should_fail",
    [
        ("int x = 1;\nint y = 2;\n", False),
        ("int x = 1;\r\nint y = 2;\r\n", True),
    ],
    ids=["unix-lf", "dos-crlf"],
)
def test_file_dos(rules, code, should_fail):
    assert ("file.dos" in rules(code)) == should_fail


@pytest.mark.parametrize(
    "code,should_fail",
    [
        ("int x = 1;\n", False),
        ("\nint x = 1;\n", True),
        ("int x = 1;\n\n", True),
    ],
    ids=["clean", "leading-blank", "trailing-blank"],
)
def test_file_spurious(rules, code, should_fail):
    assert ("file.spurious" in rules(code)) == should_fail


@pytest.mark.parametrize(
    "code,should_fail",
    [
        ("int a;\n\nint b;\n", False),
        ("int a;\n\n\nint b;\n", True),
    ],
    ids=["single-blank", "double-blank"],
)
def test_lines_empty(rules, code, should_fail):
    assert ("lines.empty" in rules(code)) == should_fail


@pytest.mark.parametrize(
    "code,rule,should_fail",
    [
        ("int a;\nint b;\r\n", "file.dos", True),
        ("", "file.terminate", False),
        ("int x;\n\n\n", "file.spurious", True),
        ("  \nint x;\n", "file.spurious", True),
        ("int a;\n \n\t\nint b;\n", "lines.empty", True),
    ],
    ids=[
        "dos-mixed",
        "terminate-empty-file",
        "spurious-multi-trailing",
        "spurious-ws-first-line",
        "empty-whitespace-only",
    ],
)
def test_file_rule_edges(rules, code, rule, should_fail):
    assert (rule in rules(code)) == should_fail


def test_lines_empty_no_phantom_line(lint):
    assert all(v.line <= 3 for v in lint("int a;\n\n\n") if v.rule == "lines.empty")
