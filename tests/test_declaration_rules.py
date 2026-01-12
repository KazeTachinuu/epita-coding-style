"""Tests for declaration rules."""

import pytest


# decl.single: one declaration per line
@pytest.mark.parametrize("code,should_fail", [
    ("int x;\n", False),
    ("int x = 1;\n", False),
    ("int x, y;\n", True),
    ("int *x, *y;\n", True),
])
def test_decl_single(check, code, should_fail):
    assert check(code, "decl.single") == should_fail


# decl.vla: no variable-length arrays
@pytest.mark.parametrize("code,should_fail", [
    ("void f(void) { int arr[10]; }\n", False),
    ("#define SIZE 10\nvoid f(void) { int arr[SIZE]; }\n", False),
    ("void f(int n) { int arr[n]; }\n", True),
])
def test_decl_vla(check, code, should_fail):
    assert check(code, "decl.vla") == should_fail
