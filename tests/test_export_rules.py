"""Tests for export rules."""

import pytest
from check import Severity


def _make_exported_funcs(n, allman=False, multiline_params=False):
    """Generate n exported functions (K&R, Allman, or multi-line params)."""
    if multiline_params:
        return "\n".join(
            f"int func{i}(int a,\n           int b)\n{{\n    return {i};\n}}"
            for i in range(n)
        ) + "\n"
    if allman:
        return "\n".join(f"int func{i}(void)\n{{\n    return {i};\n}}" for i in range(n)) + "\n"
    return "\n".join(f"int func{i}(void) {{ return {i}; }}" for i in range(n)) + "\n"


def _make_static_funcs(n):
    """Generate n static functions."""
    return "\n".join(f"static int func{i}(void) {{ return {i}; }}" for i in range(n)) + "\n"


# export.fun: max 10 exported functions per .c file
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10), False),
    (_make_exported_funcs(11), True),
    (_make_static_funcs(15), False),  # all static, no limit
])
def test_export_fun(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


# export.fun: Allman style (brace on own line)
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10, allman=True), False),
    (_make_exported_funcs(11, allman=True), True),
])
def test_export_fun_allman(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


# export.fun: Multi-line parameters
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10, multiline_params=True), False),
    (_make_exported_funcs(11, multiline_params=True), True),
])
def test_export_fun_multiline_params(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


def test_export_fun_header_not_checked(check):
    """export.fun rule should not apply to .h files."""
    code = _make_exported_funcs(11)
    assert not check(code, "export.fun", suffix=".h")


def test_export_fun_is_major(check_result):
    """export.fun violations should be MAJOR severity."""
    code = _make_exported_funcs(11)
    result = check_result(code)
    violations = [v for v in result.violations if v.rule == "export.fun"]
    assert len(violations) > 0
    assert all(v.severity == Severity.MAJOR for v in violations)


# export.other: max 1 non-function exported symbol per .c file
@pytest.mark.parametrize("code,should_fail", [
    ("int global_var;\n", False),
    ("int global_var1;\nint global_var2;\n", True),
])
def test_export_other(check, code, should_fail):
    assert check(code, "export.other") == should_fail
