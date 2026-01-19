"""Tests for declaration rules."""

import pytest
from textwrap import dedent


@pytest.mark.parametrize("code,should_fail", [
    ("int x;\n", False),
    ("int x = 1;\n", False),
    ("int x, y;\n", True),
    ("int *x, *y;\n", True),
])
def test_decl_single(check, code, should_fail):
    assert check(code, "decl.single") == should_fail


VLA_MACRO_OK = dedent("""\
    #define SIZE 10
    void f(void) { int arr[SIZE]; }
""")


@pytest.mark.parametrize("code,should_fail", [
    ("void f(void) { int arr[10]; }\n", False),
    (VLA_MACRO_OK, False),
    ("void f(int n) { int arr[n]; }\n", True),
])
def test_decl_vla(check, code, should_fail):
    assert check(code, "decl.vla") == should_fail
